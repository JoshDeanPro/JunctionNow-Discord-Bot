from __future__ import annotations

import asyncio
import logging

import uvicorn

from app.api.server import create_api
from app.bot.client import JunctionNowBot
from app.config import get_settings
from app.db.session import close_database, init_database
from app.logging_config import configure_logging

logger = logging.getLogger(__name__)


async def run_api(
    bot: JunctionNowBot,
) -> None:
    settings = get_settings()

    server = uvicorn.Server(
        uvicorn.Config(
            create_api(bot),
            host=settings.api_host,
            port=settings.api_port,
            log_level=settings.log_level.lower(),
            access_log=False,
        )
    )

    await server.serve()


async def main() -> None:
    configure_logging()

    settings = get_settings()

    if not settings.discord_token:
        raise RuntimeError(
            "DISCORD_TOKEN is not configured. "
            "Configure .env before starting the bot."
        )

    await init_database()

    bot = JunctionNowBot()
    running: list[asyncio.Task] = []

    try:
        running.append(
            asyncio.create_task(
                bot.start(settings.discord_token),
                name="discord",
            )
        )

        if settings.api_enabled:
            running.append(
                asyncio.create_task(
                    run_api(bot),
                    name="internal-api",
                )
            )

        done, pending = await asyncio.wait(
            running,
            return_when=asyncio.FIRST_EXCEPTION,
        )

        for task in done:
            error = task.exception()

            if error is not None:
                raise error

        for task in pending:
            task.cancel()

    finally:
        if not bot.is_closed():
            await bot.close()

        for task in running:
            if not task.done():
                task.cancel()

        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
