from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _load_env() -> None:
    path = Path(".env")

    if not path.exists():
        return

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        os.environ.setdefault(key, value)


def _integer(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    return int(value) if value else default


def _float(name: str, default: float) -> float:
    value = os.environ.get(name, "").strip()
    return float(value) if value else default


def _boolean(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()

    if not value:
        return default

    return value in {"1", "true", "yes", "on"}


def _optional_integer(name: str) -> int | None:
    value = os.environ.get(name, "").strip()
    return int(value) if value else None


@dataclass(frozen=True, slots=True)
class Settings:
    discord_token: str
    discord_application_id: int | None

    app_env: str
    log_level: str

    junctionnow_feed_url: str
    junctionnow_request_timeout: float
    max_feed_items: int

    sync_interval_seconds: int
    sync_on_startup: bool

    state_file: str
    state_max_posts: int
    state_max_events: int
    state_backup_count: int

    log_file: str


@lru_cache
def get_settings() -> Settings:
    _load_env()

    return Settings(
        discord_token=os.environ.get("DISCORD_TOKEN", "").strip(),
        discord_application_id=_optional_integer("DISCORD_APPLICATION_ID"),
        app_env=os.environ.get("APP_ENV", "development").strip(),
        log_level=os.environ.get("LOG_LEVEL", "INFO").strip(),
        junctionnow_feed_url=os.environ.get(
            "JUNCTIONNOW_FEED_URL",
            "https://junctionnow.com/feed/",
        ).strip(),
        junctionnow_request_timeout=_float(
            "JUNCTIONNOW_REQUEST_TIMEOUT",
            20.0,
        ),
        max_feed_items=_integer("MAX_FEED_ITEMS", 10),
        sync_interval_seconds=_integer("SYNC_INTERVAL_SECONDS", 300),
        sync_on_startup=_boolean("SYNC_ON_STARTUP", True),
        state_file=os.environ.get(
            "STATE_FILE",
            "./data/state.json",
        ).strip(),
        state_max_posts=_integer("STATE_MAX_POSTS", 1000),
        state_max_events=_integer("STATE_MAX_EVENTS", 500),
        state_backup_count=_integer("STATE_BACKUP_COUNT", 5),
        log_file=os.environ.get(
            "LOG_FILE",
            "./logs/junctionnow-bot.log",
        ).strip(),
    )
