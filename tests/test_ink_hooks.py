from pathlib import Path


def dashboard_source() -> str:
    text = Path(
        "ui/src/index.mjs"
    ).read_text(
        encoding="utf-8"
    )

    start = text.index(
        "function Dashboard"
    )

    end = text.index(
        "function Servers",
        start,
    )

    return text[start:end]


def test_dashboard_input_hook_is_unconditional():
    text = dashboard_source()

    hook = text.index(
        "useInput("
    )

    error_return = text.index(
        "if (error)"
    )

    loading_return = text.index(
        "if (!data)"
    )

    assert hook < error_return
    assert hook < loading_return


def test_dashboard_has_one_input_hook():
    text = dashboard_source()

    assert text.count(
        "useInput("
    ) == 1
