from pathlib import Path


def test_token_setter_uses_placeholder():
    text = Path(
        "scripts/set_token.sh"
    ).read_text(encoding="utf-8")

    assert "DISCORD_TOKEN=__TOKEN__" in text


def test_style_guide_uses_generic_paths():
    text = Path(
        "docs/STYLE_GUIDE.md"
    ).read_text(encoding="utf-8")

    assert "<project-root>" in text
    assert "personal home folder" in text


def test_env_is_ignored():
    ignore = Path(
        ".gitignore"
    ).read_text(encoding="utf-8")

    lines = {
        line.strip()
        for line in ignore.splitlines()
    }

    assert ".env" in lines
