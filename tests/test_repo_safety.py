from pathlib import Path


def test_token_setter_uses_placeholder():
    text = Path(
        "scripts/set_token.sh"
    ).read_text(
        encoding="utf-8"
    )

    assert "DISCORD_TOKEN=__TOKEN__" in text


def test_style_guide_uses_generic_paths():
    text = Path(
        "docs/STYLE_GUIDE.md"
    ).read_text(
        encoding="utf-8"
    )

    assert "<project-root>" in text
    assert "personal home folder" in text


def test_env_is_ignored():
    lines = {
        line.strip()
        for line in Path(
            ".gitignore"
        )
        .read_text(
            encoding="utf-8"
        )
        .splitlines()
    }

    assert ".env" in lines


def test_ink_source_is_not_treated_as_env():
    text = Path(
        "ui/src/index.mjs"
    ).read_text(
        encoding="utf-8"
    )

    assert "secret = false" in text
