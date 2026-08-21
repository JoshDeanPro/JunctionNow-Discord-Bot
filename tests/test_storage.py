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
