from pathlib import Path


def test_credentials_are_managed_by_jnbot_only():
    assert not Path("scripts/set_token.sh").exists()
    assert not Path("scripts/set_app_id.sh").exists()

    text = Path("ui/src/index.mjs").read_text(encoding="utf-8")
    assert "Discord token" in text
    assert "secret: true" in text


def test_readme_uses_generic_paths():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "/Users/" not in text
    assert "personal" in text


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
