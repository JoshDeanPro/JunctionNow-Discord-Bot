from pathlib import Path

import pytest

from app.storage import (
    SCHEMA_VERSION,
    JsonStateStore,
)


@pytest.mark.asyncio
async def test_json_state_initializes(
    tmp_path: Path,
    monkeypatch,
):
    path = (
        tmp_path
        / "state.json"
    )

    store = JsonStateStore()

    store.path = path
    store.backup_dir = (
        tmp_path
        / "backups"
    )

    await store.initialize()

    state = await store.snapshot()

    assert state[
        "schema_version"
    ] == SCHEMA_VERSION

    assert path.exists()


@pytest.mark.asyncio
async def test_event_is_persisted(
    tmp_path: Path,
):
    store = JsonStateStore()

    store.path = (
        tmp_path
        / "state.json"
    )

    store.backup_dir = (
        tmp_path
        / "backups"
    )

    await store.initialize()

    await store.record_event(
        "test_event",
        guild_id=123,
    )

    state = await store.snapshot()

    assert (
        state["analytics"]
        ["counters"]
        ["test_event"]
        == 1
    )


@pytest.mark.asyncio
async def test_feed_refresh_preserves_operator_post_state(
    tmp_path: Path,
):
    store = JsonStateStore()
    store.path = tmp_path / "state.json"
    store.backup_dir = tmp_path / "backups"
    await store.initialize()

    original = {
        "post_id": "article-1",
        "title": "Original",
        "source_hash": "old",
    }
    await store.upsert_post(original)

    def set_operator_state(state):
        post = state["posts"]["article-1"]
        post["withdrawn"] = True
        post["withdrawn_at"] = "2026-01-01T00:00:00+00:00"
        post["photo_requested"] = True
        post["photo_request_changed_at"] = "2026-01-02T00:00:00+00:00"

    await store.mutate(set_operator_state)
    result = await store.upsert_post(
        {
            **original,
            "title": "Changed",
            "source_hash": "new",
        }
    )

    assert result["changed"] is True
    assert result["record"]["title"] == "Changed"
    assert result["record"]["withdrawn"] is True
    assert result["record"]["photo_requested"] is True


@pytest.mark.asyncio
async def test_mentions_are_pending_for_one_delivery(tmp_path: Path):
    store = JsonStateStore()
    store.path = tmp_path / "state.json"
    store.backup_dir = tmp_path / "backups"
    await store.initialize()

    await store.configure_roles(123, [10, 20], 99)
    configured = await store.get_guild(123)

    assert configured["mention_role_ids"] == ["10", "20"]
    assert configured["mention_pending"] is True

    await store.consume_mentions(123)

    assert (await store.get_guild(123))["mention_pending"] is False


@pytest.mark.asyncio
async def test_guild_tracks_sendable_channels_from_gateway_cache(tmp_path: Path):
    store = JsonStateStore()
    store.path = tmp_path / "state.json"
    store.backup_dir = tmp_path / "backups"
    await store.initialize()

    permissions = type("Permissions", (), {"view_channel": True, "send_messages": True})()
    channel = type(
        "Channel",
        (),
        {"id": 456, "name": "news", "permissions_for": lambda self, member: permissions},
    )()
    guild = type(
        "Guild",
        (),
        {
            "id": 123,
            "name": "Test Server",
            "member_count": 10,
            "me": object(),
            "text_channels": [channel],
        },
    )()

    await store.track_guild(guild)

    assert (await store.get_guild(123))["available_channels"] == [
        {"id": "456", "name": "news"}
    ]
