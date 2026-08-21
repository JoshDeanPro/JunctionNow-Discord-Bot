from __future__ import annotations

import asyncio

import uvicorn

from app.api.server import create_api
from app.bot.client import JunctionNowBot
from app.config import get_settings
from app.logging_config import configure_logging
from app.storage import JsonStateStore


async def run_api(
    bot: JunctionNowBot,
) -> None:
    settings = get_settings()

    server = uvicorn.Server(
        uvicorn.Config(
            create_api(bot),
            host=settings.api_host,
            port=settings.api_port,
            log_level=(
                settings.log_level.lower()
            ),
            access_log=False,
        )
    )

    await server.serve()


async def main() -> None:
    configure_logging()

    settings = get_settings()

    if not settings.discord_token:
        raise RuntimeError(
            "DISCORD_TOKEN is not configured"
        )

    store = JsonStateStore()
    await store.initialize()

    bot = JunctionNowBot(
        store
    )

    tasks = [
        asyncio.create_task(
            bot.start(
                settings.discord_token
            ),
            name="discord",
        )
    ]

    if settings.api_enabled:
        tasks.append(
            asyncio.create_task(
                run_api(bot),
                name="api",
            )
        )

    try:
        done, pending = await asyncio.wait(
            tasks,
            return_when=(
                asyncio.FIRST_EXCEPTION
            ),
        )

        for task in done:
            error = task.exception()

            if error:
                raise error

        for task in pending:
            task.cancel()

    finally:
        if not bot.is_closed():
            await bot.close()

        for task in tasks:
            if not task.done():
                task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
