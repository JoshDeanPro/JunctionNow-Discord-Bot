from pathlib import Path


def test_commands_require_manage_server():
    text = Path(
        "app/bot/commands.py"
    ).read_text(encoding="utf-8")

    assert text.count(
        "default_permissions(\n        manage_guild=True"
    ) == 2

    assert text.count(
        "has_permissions(\n        manage_guild=True"
    ) == 2


def test_public_commands_stay_small():
    text = Path(
        "app/bot/commands.py"
    ).read_text(encoding="utf-8")

    assert 'name="config"' in text
    assert 'name="status"' in text

    assert text.count(
        "@app_commands.command"
    ) == 2
