from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    discord_token: str = ""
    discord_application_id: int | None = None
    discord_dev_guild_id: int | None = None

    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:///./data/junctionnow.db"

    source_mode: Literal["auto", "json", "rss"] = "auto"
    junctionnow_feed_url: str = ""
    junctionnow_request_timeout: float = 20.0
    max_posts_per_sync: int = 100

    sync_interval_seconds: int = 60
    sync_on_startup: bool = True

    api_enabled: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = 8787
    internal_api_secret: str = ""

    bot_brand_name: str = "JunctionNow"
    bot_footer_text: str = "JunctionNow"

    log_file: str = "./logs/junctionnow-bot.log"

    @field_validator(
        "discord_application_id",
        "discord_dev_guild_id",
        mode="before",
    )
    @classmethod
    def blank_int_to_none(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
