from __future__ import annotations

import secrets

from fastapi import FastAPI, Header, HTTPException

from app.config import get_settings


def create_api(bot) -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="JunctionNow Discord Bot",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    def authorize(
        supplied: str | None,
    ) -> None:
        configured = settings.internal_api_secret

        if not configured:
            raise HTTPException(
                status_code=503,
                detail="Internal API secret is not configured",
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
            "discord_ready": bot.is_ready(),
            "guilds": len(bot.guilds),
        }

    @app.get("/ready")
    async def ready():
        if not bot.is_ready():
            raise HTTPException(
                status_code=503,
                detail="Discord bot is not ready",
            )

        return {
            "status": "ready",
            "discord_ready": True,
        }

    @app.post("/internal/sync")
    async def sync(
        x_junctionnow_secret: str | None = Header(
            default=None
        ),
    ):
        authorize(x_junctionnow_secret)
        return await bot.sync_engine.sync_once()

    @app.get("/internal/status")
    async def internal_status(
        x_junctionnow_secret: str | None = Header(
            default=None
        ),
    ):
        authorize(x_junctionnow_secret)

        engine = bot.sync_engine

        return {
            "guilds": len(bot.guilds),
            "last_sync_started_at": engine.last_sync_started_at,
            "last_sync_finished_at": engine.last_sync_finished_at,
            "last_sync_error": engine.last_sync_error,
            "last_post_count": engine.last_post_count,
        }

    return app
