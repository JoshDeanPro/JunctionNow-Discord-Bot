from pathlib import Path

import pytest

from app import tui_bridge


def test_invite_uses_only_required_permissions(monkeypatch):
    monkeypatch.setattr(
        tui_bridge,
        "configured",
        lambda: {"application_id": "123456789"},
    )

    invite = tui_bridge.invite_link()

    assert "applications.commands" in invite["url"]
    assert "bot" in invite["url"]
    assert "Administrator" not in invite["permissions"]
    assert "Manage Server" not in invite["permissions"]


def test_manager_uninstall_removes_command_and_project(tmp_path, monkeypatch):
    project = tmp_path / "JunctionNow-Discord-Bot"
    command = project / "bin" / "jnbot"
    command.parent.mkdir(parents=True)
    command.write_text("#!/bin/sh\n", encoding="utf-8")
    (project / ".git").mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "junctionnow-discord-bot"\n', encoding="utf-8"
    )
    installed = tmp_path / "bin" / "jnbot"
    installed.parent.mkdir()
    installed.symlink_to(command)

    monkeypatch.setattr(tui_bridge, "ROOT", project)
    monkeypatch.setattr(tui_bridge, "INSTALL_ROOT", project)
    monkeypatch.setattr(tui_bridge, "INSTALLED_COMMAND", installed)
    monkeypatch.setattr(tui_bridge, "daemon_pid", lambda: None)
    monkeypatch.setattr(tui_bridge, "daemon_stop", lambda: {"running": False})

    assert tui_bridge.uninstall_manager() == {"installed": False, "removed": True}
    assert not installed.exists()
    assert not project.exists()


def test_manager_uninstall_preserves_unrelated_command(tmp_path, monkeypatch):
    project = tmp_path / "JunctionNow-Discord-Bot"
    (project / ".git").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "junctionnow-discord-bot"\n', encoding="utf-8"
    )
    installed = tmp_path / "jnbot"
    installed.write_text("unrelated", encoding="utf-8")
    monkeypatch.setattr(tui_bridge, "ROOT", project)
    monkeypatch.setattr(tui_bridge, "INSTALL_ROOT", project)
    monkeypatch.setattr(tui_bridge, "INSTALLED_COMMAND", installed)

    with pytest.raises(RuntimeError, match="not managed"):
        tui_bridge.uninstall_manager()

    assert installed.read_text(encoding="utf-8") == "unrelated"


def test_manager_self_install_does_not_overwrite_existing_command():
    text = Path("scripts/install.sh").read_text(encoding="utf-8")

    assert 'APP_ROOT="${JNBOT_INSTALL_ROOT:-$HOME/.local/share/junctionnow}"' in text
    assert 'ln -s "$APP_ROOT/bin/jnbot" "$COMMAND_PATH"' in text
    assert "managed by another application" in text
    assert "python3.12 -m venv" in text
    assert 'pip install --quiet -e "$APP_ROOT"' in text
    assert 'npm --prefix "$APP_ROOT/ui" ci --omit=dev --silent' in text
    assert '"$APP_ROOT[dev]"' not in text


def test_starting_an_active_bot_does_not_spawn_another_process(tmp_path, monkeypatch):
    saved = []
    monkeypatch.setattr(tui_bridge, "LIFECYCLE_LOCK", tmp_path / "daemon.lock")
    monkeypatch.setattr(tui_bridge, "daemon_pid", lambda: 12345)
    monkeypatch.setattr(tui_bridge, "save_value", lambda name, value: saved.append((name, value)))

    class UnexpectedProcess:
        def __init__(self, *args, **kwargs):
            raise AssertionError("A second bot process was started")

    monkeypatch.setattr(tui_bridge.subprocess, "Popen", UnexpectedProcess)

    assert tui_bridge.daemon_start() == {"running": True, "pid": 12345}
    assert saved == [("BOT_ENABLED", "1")]
