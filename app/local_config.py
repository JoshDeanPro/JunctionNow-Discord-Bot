from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def configured() -> dict:
    values = read_values()
    guild_id = values.get("MANAGEMENT_GUILD_ID", "")
    channel_id = values.get("MANAGEMENT_CHANNEL_ID", "")
    webhook = values.get("PHOTO_WEBHOOK_URL", "")

    return {
        "token_configured": bool(values.get("DISCORD_TOKEN")),
        "application_id": values.get("DISCORD_APPLICATION_ID", ""),
        "photo_guild_id": guild_id,
        "photo_channel_id": channel_id,
        "photo_webhook_configured": bool(webhook),
        "photo_destination_configured": bool(webhook or (guild_id and channel_id)),
        "sync_interval_minutes": int(values.get("SYNC_INTERVAL_SECONDS", "1800")) // 60,
        "timezone": datetime.now().astimezone().tzname() or "Local time",
    }


def read_values() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}

    values = {}

    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")

    return values


def save_value(name: str, value: str) -> None:
    allowed = {
        "DISCORD_TOKEN",
        "DISCORD_APPLICATION_ID",
        "MANAGEMENT_GUILD_ID",
        "MANAGEMENT_CHANNEL_ID",
        "PHOTO_WEBHOOK_URL",
        "SYNC_INTERVAL_SECONDS",
    }

    if name not in allowed:
        raise ValueError("That setting cannot be changed here.")

    value = value.strip()

    if not value or "\n" in value or "\r" in value:
        raise ValueError("The value cannot be empty.")

    numeric = {
        "DISCORD_APPLICATION_ID",
        "MANAGEMENT_GUILD_ID",
        "MANAGEMENT_CHANNEL_ID",
        "SYNC_INTERVAL_SECONDS",
    }

    if name in numeric and not value.isdigit():
        raise ValueError("This value must contain only numbers.")

    if name == "SYNC_INTERVAL_SECONDS" and not 1800 <= int(value) <= 86400:
        raise ValueError("Choose an interval from 30 minutes to 24 hours.")

    if name == "PHOTO_WEBHOOK_URL" and not value.startswith(
        ("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")
    ):
        raise ValueError("Enter a valid Discord webhook URL.")

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    prefix = f"{name}="
    replacement = f"{prefix}{value}"
    replaced = False

    for index, line in enumerate(lines):
        if line.strip().startswith(prefix):
            lines[index] = replacement
            replaced = True
            break

    if not replaced:
        lines.append(replacement)

    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".env-", dir=ENV_FILE.parent)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary, 0o600)
        os.replace(temporary, ENV_FILE)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def clear_photo_destination() -> None:
    for name in ("MANAGEMENT_GUILD_ID", "MANAGEMENT_CHANNEL_ID", "PHOTO_WEBHOOK_URL"):
        save_optional_value(name, "")


def save_optional_value(name: str, value: str) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    names = {name}
    kept = [line for line in lines if line.split("=", 1)[0].strip() not in names]

    if value:
        kept.append(f"{name}={value}")

    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".env-", dir=ENV_FILE.parent)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(kept) + ("\n" if kept else ""))
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary, 0o600)
        os.replace(temporary, ENV_FILE)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
