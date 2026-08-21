from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import discord

from app.control import enqueue
from app.local_config import clear_photo_destination, configured, save_value
from app.storage import JsonStateStore
from app.storage_destinations import (
    add_destination,
    public_destinations,
    remove_destination,
    sync_destination,
)
from app.updates import install_update, update_status

ROOT = Path(__file__).resolve().parents[1]
PID_FILE = ROOT / "data" / "junctionnow.pid"
INSTALLED_COMMAND = (
    Path.home() / ".junctionnow" / "bin" / "jnbot.cmd"
    if os.name == "nt"
    else Path.home() / ".local" / "bin" / "jnbot"
)


def payload() -> dict:
    try:
        return json.loads(
            sys.stdin.read() or "{}"
        )
    except json.JSONDecodeError:
        return {}


def output(data: dict) -> None:
    print(
        json.dumps(
            {
                "ok": True,
                **data,
            },
            ensure_ascii=False,
        )
    )


def fail(message: str) -> None:
    print(
        json.dumps(
            {
                "ok": False,
                "error": message,
            }
        )
    )

    raise SystemExit(1)


def daemon_pid() -> int | None:
    if not PID_FILE.exists():
        return None

    try:
        pid = int(
            PID_FILE.read_text().strip()
        )

        os.kill(pid, 0)
        return pid

    except PermissionError:
        return pid
    except (ValueError, ProcessLookupError):
        return None


def daemon_status() -> dict:
    pid = daemon_pid()
    enabled = configured()["bot_enabled"]
    running = bool(pid)

    return {
        "running": running,
        "enabled": enabled,
        "status": "active" if running else "inactive" if enabled else "disabled",
        "pid": pid,
    }


def daemon_start() -> dict:
    current = daemon_pid()

    if current:
        save_value("BOT_ENABLED", "1")
        return {
            "running": True,
            "pid": current,
        }

    process = subprocess.Popen(
        [
            str(
                ROOT
                / ".venv"
                / "bin"
                / "python"
            ),
            "-m",
            "app.main",
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    time.sleep(1)

    if process.poll() is not None:
        raise RuntimeError("The bot stopped during startup. Check the bot log.")

    save_value("BOT_ENABLED", "1")

    return {
        "running": True,
        "pid": process.pid,
    }


def daemon_stop() -> dict:
    pid = daemon_pid()
    save_value("BOT_ENABLED", "0")

    if not pid:
        return {
            "running": False,
        }

    os.kill(
        pid,
        signal.SIGTERM,
    )

    return {
        "running": False,
    }


def invite_link() -> dict:
    application_id = configured().get("application_id")

    if not application_id:
        raise ValueError("Save the Discord Application ID in Bot Settings first.")

    permissions = discord.Permissions.none()
    permissions.update(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
    )

    return {
        "url": str(
            discord.utils.oauth_url(
                int(application_id),
                permissions=permissions,
                scopes=("bot", "applications.commands"),
            )
        ),
        "permissions": [
            "View Channels",
            "Send Messages",
            "Embed Links",
            "Attach Files",
            "Read Message History",
        ],
    }


def uninstall_manager() -> dict:
    manifest = ROOT / "pyproject.toml"

    if ROOT.name != "JunctionNow-Discord-Bot" or not (ROOT / ".git").is_dir():
        raise RuntimeError("The JunctionNow installation location could not be verified.")

    with manifest.open("rb") as handle:
        project_name = tomllib.load(handle).get("project", {}).get("name")

    if project_name != "junctionnow-discord-bot":
        raise RuntimeError("The JunctionNow installation could not be verified.")

    expected = (ROOT / "bin" / "jnbot").resolve()
    windows_launcher = (
        f'@echo off\nnode "{ROOT / "ui" / "src" / "index.mjs"}" %*'
    )

    if INSTALLED_COMMAND.exists() or INSTALLED_COMMAND.is_symlink():
        managed = (
            INSTALLED_COMMAND.is_symlink()
            and INSTALLED_COMMAND.resolve() == expected
        ) or (
            os.name == "nt"
            and INSTALLED_COMMAND.is_file()
            and INSTALLED_COMMAND.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
            == windows_launcher
        )

        if not managed:
            raise RuntimeError("The installed jnbot command is not managed by this project.")

    service = Path("/etc/systemd/system/junctionnow-discord.service")

    if service.exists() and os.geteuid() != 0:
        raise RuntimeError("Run jnbot as root to remove the installed system service.")

    pid = daemon_pid()
    daemon_stop()

    if pid:
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            os.kill(pid, signal.SIGKILL)

    if service.exists():
        subprocess.run(
            ["systemctl", "disable", "--now", "junctionnow-discord.service"],
            check=True,
            capture_output=True,
            text=True,
        )
        service.unlink()
        subprocess.run(
            ["systemctl", "daemon-reload"],
            check=True,
            capture_output=True,
            text=True,
        )

    if INSTALLED_COMMAND.exists() or INSTALLED_COMMAND.is_symlink():
        INSTALLED_COMMAND.unlink()

    shutil.rmtree(ROOT)
    return {"installed": False, "removed": True}


async def async_main(
    command: str,
    data: dict,
) -> dict:
    store = JsonStateStore()
    await store.initialize()

    state = await store.snapshot()

    if command == "overview":
        guilds = state.get(
            "guilds",
            {},
        )

        deliveries = state.get(
            "deliveries",
            {},
        )

        config = configured()
        system = state.get("system", {})
        counters = state.get("analytics", {}).get("counters", {})

        def next_run(value, minutes):
            if not value:
                return None

            try:
                return (datetime.fromisoformat(value) + timedelta(minutes=minutes)).isoformat()
            except ValueError:
                return None

        return {
            "daemon": daemon_status(),
            "feed_enabled": state.get(
                "system",
                {},
            ).get(
                "feed_enabled",
                True,
            ),
            "servers": len(guilds),
            "configured": sum(
                1
                for item in guilds.values()
                if item.get("channel_id")
            ),
            "posts": len(
                state.get(
                    "posts",
                    {},
                )
            ),
            "deliveries": sum(
                len(items)
                for items in deliveries.values()
            ),
            "photo_requests": sum(
                1
                for post in state.get(
                    "posts",
                    {},
                ).values()
                if post.get(
                    "photo_requested"
                )
            ),
            "banned": len(
                state.get(
                    "banned_guilds",
                    {},
                )
            ),
            "members": sum(
                int(item.get("member_count") or 0)
                for item in guilds.values()
                if not item.get("removed_at")
            ),
            "activity_events": len(state.get("analytics", {}).get("events", [])),
            "interactions": int(counters.get("photo_button_click", 0)),
            "photo_submissions": int(counters.get("photo_submission", 0)),
            "delivery_failures": int(counters.get("delivery_error", 0)),
            "sync_failures": int(counters.get("sync_error", 0)),
            "storage_bytes": store.path.stat().st_size if store.path.exists() else 0,
            "last_post_check_at": system.get("last_post_check_at"),
            "last_post_update_check_at": system.get("last_post_update_check_at"),
            "next_post_check_at": next_run(
                system.get("last_post_check_at"), config["post_interval_minutes"]
            ),
            "next_post_update_check_at": next_run(
                system.get("last_post_update_check_at"),
                config["post_update_interval_minutes"],
            ),
            "post_interval_minutes": config["post_interval_minutes"],
            "post_update_interval_minutes": config["post_update_interval_minutes"],
        }

    if command == "servers":
        bans = state.get(
            "banned_guilds",
            {},
        )

        items = []

        for guild_id, record in (
            state.get(
                "guilds",
                {},
            ).items()
        ):
            items.append(
                {
                    "id": guild_id,
                    "name": record.get(
                        "guild_name",
                        "Unknown server",
                    ),
                    "enabled": bool(
                        record.get(
                            "enabled"
                        )
                    ),
                    "channel_id": record.get(
                        "channel_id"
                    ),
                    "channels": record.get("available_channels", []),
                    "removed": bool(
                        record.get(
                            "removed_at"
                        )
                    ),
                    "banned": guild_id in bans,
                }
            )

        items.sort(
            key=lambda item: item[
                "name"
            ].lower()
        )

        return {
            "items": items
        }

    if command == "posts":
        items = list(
            state.get(
                "posts",
                {},
            ).values()
        )

        items.sort(
            key=lambda item: item.get(
                "published_at",
                "",
            ),
            reverse=True,
        )

        return {
            "items": items[:100],
            "feed_enabled": state.get("system", {}).get("feed_enabled", True),
        }

    if command == "posts-settings":
        config = configured()
        return {
            "enabled": state.get("system", {}).get("feed_enabled", True),
            "post_interval_minutes": config["post_interval_minutes"],
            "post_update_interval_minutes": config["post_update_interval_minutes"],
            "timezone": config["timezone"],
        }

    if command == "activity":
        items = (
            state.get(
                "analytics",
                {},
            ).get(
                "events",
                []
            )[-100:]
        )

        items.reverse()

        return {
            "items": items
        }

    if command == "storage-status":
        config = configured()
        posts = state.get("posts", {})
        deliveries = state.get("deliveries", {})
        events = state.get("analytics", {}).get("events", [])

        return {
            "backends": {
                "json": {"status": "active", "label": "Active"},
                "mysql": {"status": "not_enabled", "label": "Not Enabled"},
                "postgresql": {"status": "not_enabled", "label": "Not Enabled"},
            },
            "features": {
                "posts": len(posts),
                "deliveries": sum(len(items) for items in deliveries.values()),
                "photo_requests": sum(
                    1 for post in posts.values() if post.get("photo_requested")
                ),
                "photo_submissions": sum(
                    1 for event in events if event.get("type") == "photo_submission"
                ),
                "broadcasts": len(state.get("broadcasts", {})),
                "activity": len(events),
            },
            "limits": {
                "posts": config["state_max_posts"],
                "activity": config["state_max_events"],
                "backups": config["state_backup_count"],
            },
            "state_location": "data/state.json",
            "archive_location": "data/backups",
        }

    if command == "storage-destinations":
        return {"items": public_destinations()}

    if command == "storage-destination-add":
        return await add_destination(data, state)

    if command == "storage-destination-sync":
        return await sync_destination(str(data.get("id", "")), state)

    if command == "storage-destination-remove":
        remove_destination(str(data.get("id", "")))
        return {"removed": True}

    if command == "storage-clean":
        removed = {"actions": 0, "broadcasts": 0}

        def clean(current):
            queue = current.setdefault("control", {}).setdefault("queue", [])
            kept = [item for item in queue if item.get("status") != "done"]
            removed["actions"] = len(queue) - len(kept)
            queue[:] = kept

            broadcasts = current.setdefault("broadcasts", {})
            withdrawn = [
                broadcast_id
                for broadcast_id, item in broadcasts.items()
                if item.get("withdrawn")
            ]
            for broadcast_id in withdrawn:
                broadcasts.pop(broadcast_id, None)
            removed["broadcasts"] = len(withdrawn)

        await store.mutate(clean)
        return {"removed": removed}

    if command == "storage-dump":
        export_dir = ROOT / "data" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        target = export_dir / f"state-{stamp}.json"
        encoded = json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        descriptor, temporary = tempfile.mkstemp(prefix=".export-", dir=export_dir)

        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

        return {"location": f"data/exports/{target.name}"}

    if command == "broadcasts":
        items = list(state.get("broadcasts", {}).values())
        items.sort(key=lambda item: item.get("sent_at", ""), reverse=True)
        return {"items": items[:100]}

    if command == "queue":
        action = str(
            data.get(
                "action",
                "",
            )
        )

        if not action:
            raise ValueError(
                "Action is required."
            )

        action_id = await enqueue(
            store,
            action,
            data.get(
                "payload",
                {},
            ),
        )

        return {
            "action_id": action_id
        }

    if command == "schedule-set":
        minutes = int(data.get("minutes", 0))
        schedule = str(data.get("schedule", "posts"))
        seconds = minutes * 60
        setting = {
            "posts": "POST_INTERVAL_SECONDS",
            "updates": "POST_UPDATE_INTERVAL_SECONDS",
        }.get(schedule)

        if not setting:
            raise ValueError("Unknown post schedule.")

        save_value(setting, str(seconds))
        action_id = await enqueue(
            store,
            "sync_interval",
            {"seconds": seconds, "schedule": schedule},
        )
        return {"action_id": action_id, "minutes": minutes, "schedule": schedule}

    if command == "retention-set":
        values = {
            "max_posts": int(data["max_posts"]),
            "max_events": int(data["max_events"]),
            "backup_count": int(data["backup_count"]),
        }
        save_value("STATE_MAX_POSTS", str(values["max_posts"]))
        save_value("STATE_MAX_EVENTS", str(values["max_events"]))
        save_value("STATE_BACKUP_COUNT", str(values["backup_count"]))
        action_id = await enqueue(store, "retention", values)
        return {"action_id": action_id, **values}

    raise ValueError(
        f"Unknown command: {command}"
    )


def main() -> None:
    if len(sys.argv) < 2:
        fail("Command is required.")

    command = sys.argv[1]
    data = payload()

    try:
        if command == "daemon-status":
            output(
                daemon_status()
            )
            return

        if command == "invite-link":
            output(invite_link())
            return

        if command == "manager-uninstall":
            output(uninstall_manager())
            return

        if command == "config-status":
            output(configured())
            return

        if command == "config-set":
            name = str(data.get("name", ""))
            save_value(name, str(data.get("value", "")))
            output({"saved": name})
            return

        if command == "config-clear-photo":
            clear_photo_destination()
            output({"saved": "photo_destination"})
            return

        if command == "daemon-start":
            output(
                daemon_start()
            )
            return

        if command == "daemon-stop":
            output(
                daemon_stop()
            )
            return

        if command == "update-status":
            output(update_status(fetch=True))
            return

        if command == "update-install":
            output(install_update())
            return

        result = asyncio.run(
            async_main(
                command,
                data,
            )
        )

        output(result)

    except Exception as exc:
        fail(str(exc))


if __name__ == "__main__":
    main()
