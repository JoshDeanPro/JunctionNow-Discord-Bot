from __future__ import annotations

import logging
from pathlib import Path

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()

    path = Path(settings.log_file)
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    logging.basicConfig(
        level=getattr(
            logging,
            settings.log_level.upper(),
            logging.INFO,
        ),
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s: %(message)s"
        ),
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                path,
                encoding="utf-8",
            ),
        ],
    )

    logging.getLogger("httpx").setLevel(
        logging.WARNING
    )

    logging.getLogger("httpcore").setLevel(
        logging.WARNING
    )

    logging.getLogger("aiohttp").setLevel(
        logging.WARNING
    )

    logging.getLogger(
        "discord.gateway"
    ).setLevel(logging.WARNING)
