from __future__ import annotations

import asyncio

from app.bot.client import JunctionNowBot
from app.config import get_settings
from app.logging_config import configure_logging
from app.storage import JsonStateStore


async def main() -> None:
    configure_logging()

    settings = get_settings()

    if not settings.discord_token:
        raise RuntimeError(
            "DISCORD_TOKEN is not configured in .env"
        )

    if (
        settings.management_guild_id
        or settings.management_channel_id
        or settings.management_operator_ids
    ):
        if not (
            settings.management_guild_id
            and settings.management_channel_id
            and len(settings.management_operator_ids) == 2
        ):
            raise RuntimeError(
                "Management configuration is incomplete"
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


if __name__ == "__main__":
    asyncio.run(main())
