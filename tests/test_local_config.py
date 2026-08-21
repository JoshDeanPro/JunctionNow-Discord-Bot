import stat

import pytest

from app import local_config


def test_private_settings_are_atomic_and_preserved(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LOG_LEVEL=WARNING\n", encoding="utf-8")
    monkeypatch.setattr(local_config, "ENV_FILE", env_file)

    local_config.save_value("DISCORD_TOKEN", "private-token")

    assert local_config.configured()["token_configured"] is True
    assert "LOG_LEVEL=WARNING" in env_file.read_text(encoding="utf-8")
    assert "DISCORD_TOKEN=private-token" in env_file.read_text(encoding="utf-8")
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600


def test_private_settings_reject_unknown_names(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "ENV_FILE", tmp_path / ".env")

    with pytest.raises(ValueError, match="cannot be changed"):
        local_config.save_value("UNSAFE_SETTING", "value")


def test_photo_destination_requires_channel_or_webhook(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "ENV_FILE", tmp_path / ".env")

    local_config.save_value("MANAGEMENT_GUILD_ID", "123")
    assert local_config.configured()["photo_destination_configured"] is False

    local_config.save_value("MANAGEMENT_CHANNEL_ID", "456")
    assert local_config.configured()["photo_destination_configured"] is True

    local_config.clear_photo_destination()
    assert local_config.configured()["photo_destination_configured"] is False


def test_photo_webhook_is_private_and_validated(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "ENV_FILE", tmp_path / ".env")

    with pytest.raises(ValueError, match="valid Discord webhook"):
        local_config.save_value("PHOTO_WEBHOOK_URL", "https://example.com/hook")

    local_config.save_value(
        "PHOTO_WEBHOOK_URL",
        "https://discord.com/api/webhooks/123/private-value",
    )

    status = local_config.configured()
    assert status["photo_webhook_configured"] is True
    assert "webhook_url" not in status


def test_schedule_is_bounded_and_reports_local_timezone(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "ENV_FILE", tmp_path / ".env")

    with pytest.raises(ValueError, match="30 minutes"):
        local_config.save_value("SYNC_INTERVAL_SECONDS", "60")

    local_config.save_value("SYNC_INTERVAL_SECONDS", "3600")
    status = local_config.configured()

    assert status["sync_interval_minutes"] == 60
    assert status["timezone"]
