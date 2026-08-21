from pathlib import Path
from unittest.mock import AsyncMock

import discord
import pytest

from app.control import ControlWorker
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


@pytest.mark.asyncio
async def test_multi_photo_request_is_one_bounded_operator_action(monkeypatch):
    request = AsyncMock()
    monkeypatch.setattr("app.control.set_photo_request", request)
    bot = object()

    await ControlWorker(bot).photo_requests(
        {
            "post_ids": ["one", "two", "one"],
            "enabled": True,
        }
    )

    assert request.await_count == 2
    request.assert_any_await(bot, "one", True)
    request.assert_any_await(bot, "two", True)
