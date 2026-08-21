from pathlib import Path

import discord

from app.photos import PhotoPostView


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


def test_operator_tools_moved_to_ink():
    assert not Path(
        "app/management.py"
    ).exists()

    assert Path(
        "app/control.py"
    ).exists()

    assert Path(
        "app/tui_bridge.py"
    ).exists()

    assert Path(
        "ui/src/index.mjs"
    ).exists()

    text = Path(
        "ui/src/index.mjs"
    ).read_text(
        encoding="utf-8"
    )

    assert "Request photos" in text
    assert "Servers" in text
    assert "Broadcast" in text
    assert "Ban server" in text


def test_low_noise_http_logging():
    text = Path(
        "app/logging_config.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        'logging.getLogger("httpx")'
        in text
    )

    assert "logging.WARNING" in text
