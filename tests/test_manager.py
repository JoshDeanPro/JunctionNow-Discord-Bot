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


def test_manager_uninstall_only_removes_its_own_link(tmp_path, monkeypatch):
    project = tmp_path / "project"
    command = project / "bin" / "jnbot"
    command.parent.mkdir(parents=True)
    command.write_text("#!/bin/sh\n", encoding="utf-8")
    installed = tmp_path / "bin" / "jnbot"
    installed.parent.mkdir()
    installed.symlink_to(command)

    monkeypatch.setattr(tui_bridge, "ROOT", project)
    monkeypatch.setattr(tui_bridge, "INSTALLED_COMMAND", installed)

    assert tui_bridge.uninstall_manager() == {"installed": False}
    assert not installed.exists()
    assert command.exists()


def test_manager_uninstall_preserves_unrelated_command(tmp_path, monkeypatch):
    installed = tmp_path / "jnbot"
    installed.write_text("unrelated", encoding="utf-8")
    monkeypatch.setattr(tui_bridge, "INSTALLED_COMMAND", installed)

    with pytest.raises(RuntimeError, match="not managed"):
        tui_bridge.uninstall_manager()

    assert installed.read_text(encoding="utf-8") == "unrelated"


def test_manager_self_install_does_not_overwrite_existing_command():
    text = Path("bin/jnbot").read_text(encoding="utf-8")

    assert '[ ! -e "$INSTALLED" ] && [ ! -L "$INSTALLED" ]' in text
    assert 'ln -s "$ROOT/bin/jnbot" "$INSTALLED"' in text
