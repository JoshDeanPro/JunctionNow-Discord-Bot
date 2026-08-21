from __future__ import annotations

import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def configured() -> dict:
    values = read_values()
    return {
        "token_configured": bool(values.get("DISCORD_TOKEN")),
        "application_id": values.get("DISCORD_APPLICATION_ID", ""),
        "photo_destination_configured": bool(values.get("MANAGEMENT_GUILD_ID")),
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
    }

    if name not in allowed:
        raise ValueError("That setting cannot be changed here.")

    value = value.strip()

    if not value or "\n" in value or "\r" in value:
        raise ValueError("The value cannot be empty.")

    if name != "DISCORD_TOKEN" and not value.isdigit():
        raise ValueError("This value must contain only numbers.")

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
