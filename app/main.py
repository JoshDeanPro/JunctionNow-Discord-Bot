from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.bot.client import JunctionNowBot
from app.config import get_settings
from app.logging_config import configure_logging
from app.storage import JsonStateStore

ROOT = Path(__file__).resolve().parents[1]
PID_FILE = ROOT / "data" / "junctionnow.pid"


async def main() -> None:
    configure_logging()

    settings = get_settings()

    if not settings.discord_token:
        raise RuntimeError(
            "DISCORD_TOKEN is not configured."
        )

    PID_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    PID_FILE.write_text(
        str(os.getpid()),
        encoding="utf-8",
    )

    store = JsonStateStore()
    await store.initialize()

    bot = JunctionNowBot(store)

    try:
        await bot.start(
            settings.discord_token
        )
    finally:
        if not bot.is_closed():
            await bot.close()

        try:
            if (
                PID_FILE.exists()
                and PID_FILE.read_text().strip()
                == str(os.getpid())
            ):
                PID_FILE.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
