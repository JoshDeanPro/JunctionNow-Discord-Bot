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

    assert 'name="setup"' in text
    assert 'name="edit"' in text
    assert 'name="config"' not in text
    assert 'name="status"' not in text

    assert text.count(
        "@app_commands.command"
    ) == 2


def test_setup_mentions_are_one_time_and_multi_role():
    components = Path("app/bot/components.py").read_text(encoding="utf-8")
    delivery = Path("app/sync/delivery.py").read_text(encoding="utf-8")

    assert "max_values=10" in components
    assert "mentioned on the next post only" in components
    assert 'config.get("mention_pending")' in delivery
