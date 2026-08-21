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

    with pytest.raises(ValueError, match="cannot be changed"):
        local_config.save_value("DISCORD_APPLICATION_ID", "123")


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


def test_legacy_schedule_is_used_for_posts(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("SYNC_INTERVAL_SECONDS=300\n", encoding="utf-8")
    monkeypatch.setattr(local_config, "ENV_FILE", env_file)

    assert local_config.configured()["post_interval_minutes"] == 5


def test_retention_preferences_are_bounded_and_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "ENV_FILE", tmp_path / ".env")

    local_config.save_value("STATE_MAX_POSTS", "500")
    local_config.save_value("STATE_MAX_EVENTS", "250")
    local_config.save_value("STATE_BACKUP_COUNT", "3")

    status = local_config.configured()
    assert status["state_max_posts"] == 500
    assert status["state_max_events"] == 250
    assert status["state_backup_count"] == 3

    with pytest.raises(ValueError, match="outside the supported range"):
        local_config.save_value("STATE_BACKUP_COUNT", "0")


def test_bot_enabled_state_is_private_and_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "ENV_FILE", tmp_path / ".env")

    assert local_config.configured()["bot_enabled"] is True

    local_config.save_value("BOT_ENABLED", "0")
    assert local_config.configured()["bot_enabled"] is False

    with pytest.raises(ValueError, match="enabled or disabled"):
        local_config.save_value("BOT_ENABLED", "2")


def test_post_and_update_schedules_are_separate(tmp_path, monkeypatch):
    monkeypatch.setattr(local_config, "ENV_FILE", tmp_path / ".env")

    local_config.save_value("POST_INTERVAL_SECONDS", "120")
    local_config.save_value("POST_UPDATE_INTERVAL_SECONDS", "900")

    status = local_config.configured()
    assert status["post_interval_minutes"] == 2
    assert status["post_update_interval_minutes"] == 15
