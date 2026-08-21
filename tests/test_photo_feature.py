from pathlib import Path

import discord

from app.photos import (
    PhotoPostView,
)


def test_photo_components_exist():
    assert hasattr(
        discord.ui,
        "FileUpload",
    )

    assert hasattr(
        discord.ui,
        "Checkbox",
    )


def test_photo_view_is_persistent():
    class Bot:
        pass

    view = PhotoPostView(
        Bot()
    )

    assert view.timeout is None


def test_management_has_photo_and_server_tools():
    text = Path(
        "app/management.py"
    ).read_text(encoding="utf-8")

    assert 'label="Request Photos"' in text
    assert 'label="Servers"' in text
    assert 'label="Access Link"' in text


def test_low_noise_http_logging():
    text = Path(
        "app/logging_config.py"
    ).read_text(encoding="utf-8")

    assert 'logging.getLogger("httpx")' in text
    assert "logging.WARNING" in text
