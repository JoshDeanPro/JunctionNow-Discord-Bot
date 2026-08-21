from __future__ import annotations

from functools import lru_cache

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

    app_env: str = "development"
    log_level: str = "INFO"

    junctionnow_feed_url: str = "https://junctionnow.com/feed/"
    junctionnow_request_timeout: float = 20.0
    max_feed_items: int = 10

    sync_interval_seconds: int = 60
    sync_on_startup: bool = True

    state_file: str = "./data/state.json"
    state_max_posts: int = 1000
    state_max_events: int = 500
    state_backup_count: int = 5

    api_enabled: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = 8787
    internal_api_secret: str = ""

    log_file: str = "./logs/junctionnow-bot.log"

    @field_validator(
        "discord_application_id",
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
