from __future__ import annotations

import secrets

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
)

from app.config import get_settings


def create_api(
    bot,
) -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=(
            "JunctionNow Discord Bot"
        ),
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    def authorize(
        supplied: str | None,
    ) -> None:
        configured = (
            settings.internal_api_secret
        )

        if not configured:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Internal API secret "
                    "is not configured"
                ),
            )

        if not secrets.compare_digest(
            configured,
            supplied or "",
        ):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized",
            )

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "discord_ready": (
                bot.is_ready()
            ),
            "guilds": len(
                bot.guilds
            ),
        }

    @app.get("/ready")
    async def ready():
        if not bot.is_ready():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Discord bot is not ready"
                ),
            )

        return {
            "status": "ready"
        }

    @app.post(
        "/internal/sync"
    )
    async def sync(
        x_junctionnow_secret: (
            str | None
        ) = Header(
            default=None
        ),
    ):
        authorize(
            x_junctionnow_secret
        )

        return await (
            bot.sync_engine
            .sync_once()
        )

    @app.get(
        "/internal/status"
    )
    async def status(
        x_junctionnow_secret: (
            str | None
        ) = Header(
            default=None
        ),
    ):
        authorize(
            x_junctionnow_secret
        )

        state = await (
            bot.store.snapshot()
        )

        return {
            "guilds": len(
                state.get(
                    "guilds",
                    {},
                )
            ),
            "posts": len(
                state.get(
                    "posts",
                    {},
                )
            ),
            "delivery_guilds": len(
                state.get(
                    "deliveries",
                    {},
                )
            ),
            "analytics": (
                state.get(
                    "analytics",
                    {},
                ).get(
                    "counters",
                    {},
                )
            ),
            "last_sync_started_at": (
                bot.sync_engine
                .last_sync_started_at
            ),
            "last_sync_finished_at": (
                bot.sync_engine
                .last_sync_finished_at
            ),
            "last_sync_error": (
                bot.sync_engine
                .last_sync_error
            ),
        }

    return app
