from pathlib import Path


def test_token_setter_uses_placeholder():
    text = Path(
        "scripts/set_token.sh"
    ).read_text(encoding="utf-8")

    assert "DISCORD_TOKEN=__TOKEN__" in text


def test_style_guide_has_no_real_home_path():
    text = Path(
        "docs/STYLE_GUIDE.md"
    ).read_text(encoding="utf-8")

    assert "/Users/joshua/" not in text
    assert "/home/joshua/" not in text


def test_env_is_ignored():
    ignore = Path(
        ".gitignore"
    ).read_text(encoding="utf-8")

    assert ".env" in ignore
