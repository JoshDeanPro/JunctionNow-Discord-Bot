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
