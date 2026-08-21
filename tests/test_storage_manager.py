import json
import stat

import pytest

from app import tui_bridge


class FakeStore:
    def __init__(self, state):
        self.state = state

    async def initialize(self):
        return None

    async def snapshot(self):
        return self.state

    async def mutate(self, change):
        return change(self.state)


@pytest.mark.asyncio
async def test_safe_clean_preserves_delivery_tracking(monkeypatch):
    state = {
        "posts": {"post": {"title": "Current"}},
        "deliveries": {"guild": {"post": {"message_id": "123"}}},
        "analytics": {"events": []},
        "control": {"queue": [{"status": "done"}, {"status": "failed"}]},
        "broadcasts": {
            "old": {"withdrawn": True},
            "live": {"withdrawn": False},
        },
    }
    store = FakeStore(state)
    monkeypatch.setattr(tui_bridge, "JsonStateStore", lambda: store)

    result = await tui_bridge.async_main("storage-clean", {})

    assert result["removed"] == {"actions": 1, "broadcasts": 1}
    assert state["posts"]["post"]["title"] == "Current"
    assert state["deliveries"]["guild"]["post"]["message_id"] == "123"
    assert state["control"]["queue"] == [{"status": "failed"}]
    assert set(state["broadcasts"]) == {"live"}


@pytest.mark.asyncio
async def test_dump_writes_private_local_snapshot(tmp_path, monkeypatch):
    state = {
        "posts": {},
        "deliveries": {},
        "analytics": {"events": []},
    }
    monkeypatch.setattr(tui_bridge, "ROOT", tmp_path)
    monkeypatch.setattr(tui_bridge, "JsonStateStore", lambda: FakeStore(state))

    result = await tui_bridge.async_main("storage-dump", {})
    target = tmp_path / result["location"]

    assert json.loads(target.read_text(encoding="utf-8")) == state
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
