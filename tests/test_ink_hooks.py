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


def test_operator_dates_are_friendly():
    text = Path("ui/src/index.mjs").read_text(encoding="utf-8")

    assert "function friendlyDate" in text
    assert "dateStyle: 'medium'" in text
    assert "Update all posts now" in text


def test_menu_wraps_and_only_escape_exits():
    text = Path("ui/src/index.mjs").read_text(encoding="utf-8")
    start = text.index("function Menu")
    end = text.index("function MultiSelect", start)
    menu = text[start:end]

    assert menu.count("% items.length") == 2
    assert "if (key.escape)" in menu
    assert "if (key.leftArrow && back)" in menu
    assert menu.count("exit();") == 1


def test_photo_controls_have_one_clear_hierarchy():
    text = Path("ui/src/index.mjs").read_text(encoding="utf-8")

    assert "Use a server and channel together, or use a webhook." in text
    assert "enter save   esc cancel" in text
    assert "title: 'Add-ons'" in text
    assert "'Request Photos'" in text
    assert "title: 'Features'" in text
    assert "title: 'Bot'" in text
    assert "title: 'Storage'" in text
    assert "title: 'Settings'" in text
    assert "'enter save   esc cancel'" in text
    assert "space select   enter submit   esc back" in text
    assert "label: 'Overview'" in text
    assert "Detected timezone:" in text
    assert "Request Photos · configure destination first" in text
    assert "{id: 'photos', label: 'Photos'}" not in text
    assert "Withdraw Broadcast" in text
