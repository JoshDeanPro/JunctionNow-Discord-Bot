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


def test_dashboard_loads_before_rendering_analytics():
    text = dashboard_source()

    assert "bridge('overview')" in text
    assert "label: 'Reach'" in text
    assert "label: 'Interactions'" in text
    assert "label: 'Storage'" in text
    assert "label: 'Runs'" in text


def test_dashboard_uses_shared_menu_input():
    text = dashboard_source()

    assert text.count(
        "useInput("
    ) == 0


def test_operator_dates_are_friendly():
    text = Path("ui/src/index.mjs").read_text(encoding="utf-8")

    assert "function friendlyDate" in text
    assert "dateStyle: 'medium'" in text
    assert "label: 'Update All Now'" in text


def test_menu_wraps_and_only_escape_exits():
    text = Path("ui/src/index.mjs").read_text(encoding="utf-8")
    start = text.index("function Menu")
    end = text.index("function MultiSelect", start)
    menu = text[start:end]

    assert "move(value, -1)" in menu
    assert "move(value, 1)" in menu
    assert "% items.length" in menu
    assert "if (item.spacer)" in menu
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
    assert "title: 'Manage Bot'" in text
    assert "title: 'Storage'" in text
    assert "title: 'Settings'" in text
    assert "'enter save   esc cancel'" in text
    assert "space select   enter submit   esc back" in text
    assert "label: 'Overview'" in text
    assert "title: 'Posts Settings'" in text
    assert "state: data.photo_destination_configured ? undefined : 'Needs destination'" in text
    assert "{id: 'photos', label: 'Photos'}" not in text
    assert "Withdraw Broadcast" in text
    assert "title: 'Storage Features'" in text
    assert "title: 'Storage Destinations'" in text
    assert "title: 'Storage Preferences'" in text
    assert "title: 'Storage Maintenance'" in text
    assert "label: 'Clear All'" in text
    assert "Default · JSON" in text
    assert "item.status === 'inactive'" in text


def test_first_run_and_bot_enable_return_paths_are_clear():
    text = Path("ui/src/index.mjs").read_text(encoding="utf-8")

    assert "data && !data.config.token_configured" in text
    assert "key: screen.setting" in text
    assert "label: 'Application ID'" not in text
    assert "esc skip for now" in text
    assert "home();" in text
    assert "title: 'Setup Complete'" in text
    assert "'daemon-start'" in text
    assert "`Bot ${action}d.`" not in text
    assert "function runtimeState" in text
    assert "return {label: 'Inactive', color: 'red'}" in text
    assert "state: botState.label" in text
    assert "{id: 'start', label: 'Start bot'}" not in text
    assert "{id: 'stop', label: 'Stop bot'}" not in text


def test_cli_uses_distinct_page_modes_and_single_line_menu_rows():
    text = Path("ui/src/index.mjs").read_text(encoding="utf-8")
    start = text.index("function Menu")
    end = text.index("function MultiSelect", start)
    menu = text[start:end]

    assert "function Page" in text
    assert "function ReadOnlyList" in text
    assert "item.label.padEnd" in menu
    assert "item.description" in menu
    assert "selectedItem.description" not in menu
    assert "statusColor" not in text
    assert "feature-settings" not in text
    assert "id: 'posts-settings'" in text
    assert "function postTitle" in text
    assert "label: 'Start/Stop'" in text
    assert "label: 'Post Updates'" in text
    assert "const choices = [2, 5, 15, 30" in text
    assert "label: 'Settings'" in text
    assert "label: 'Manually Enter Channel ID'" in text
    assert "'Awaiting server setup'" in text
    assert "state: server.channel_id || 'None selected'" in text
