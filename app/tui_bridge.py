from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from app.config import get_settings
from app.control import enqueue
from app.storage import JsonStateStore

ROOT = Path(__file__).resolve().parents[1]
PID_FILE = ROOT / "data" / "junctionnow.pid"


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

    except (
        ValueError,
        ProcessLookupError,
        PermissionError,
    ):
        return None


def daemon_status() -> dict:
    pid = daemon_pid()

    return {
        "running": bool(pid),
        "pid": pid,
    }


def daemon_start() -> dict:
    current = daemon_pid()

    if current:
        return {
            "running": True,
            "pid": current,
        }

    log_path = (
        ROOT
        / get_settings().log_file
    ).resolve()

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    handle = log_path.open(
        "a",
        encoding="utf-8",
    )

    subprocess.Popen(
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
        stdout=handle,
        stderr=handle,
        start_new_session=True,
    )

    return {
        "running": True,
    }


def daemon_stop() -> dict:
    pid = daemon_pid()

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
            "items": items[:100]
        }

    if command == "photos":
        events = (
            state.get(
                "analytics",
                {},
            ).get(
                "events",
                []
            )
        )

        items = [
            item
            for item in events
            if item.get("type")
            == "photo_submission"
        ]

        items.reverse()

        return {
            "items": items[:100]
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
