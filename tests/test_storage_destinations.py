import json

import pytest

from app import storage_destinations


def test_public_destinations_hide_credentials(tmp_path, monkeypatch):
    private_file = tmp_path / "private" / "storage.json"
    monkeypatch.setattr(storage_destinations, "PRIVATE_FILE", private_file)
    storage_destinations.save_destinations(
        [
            {
                "id": "one",
                "name": "Archive",
                "kind": "postgresql",
                "host": "database.internal",
                "port": 5432,
                "database": "junctionnow",
                "username": "bot",
                "password": "private-value",
                "features": ["posts"],
                "status": "active",
            }
        ]
    )

    public = storage_destinations.public_destinations()

    assert public == [
        {
            "id": "one",
            "name": "Archive",
            "kind": "postgresql",
            "features": ["posts"],
            "status": "active",
            "last_synced_at": None,
            "last_error": None,
        }
    ]
    assert private_file.stat().st_mode & 0o777 == 0o600
    assert "private-value" not in json.dumps(public)


def test_feature_payloads_only_include_selected_data():
    state = {
        "guilds": {"1": {"name": "Newsroom"}},
        "posts": {"post": {"title": "Story"}},
        "deliveries": {"post": {"1": {"message_id": "2"}}},
    }

    assert storage_destinations.feature_payloads(state, ["posts"]) == {
        "posts": state["posts"]
    }


@pytest.mark.asyncio
async def test_destination_is_saved_only_after_successful_write(tmp_path, monkeypatch):
    monkeypatch.setattr(
        storage_destinations,
        "PRIVATE_FILE",
        tmp_path / "private" / "storage.json",
    )
    writes = []

    async def write(destination, payloads):
        writes.append((destination, payloads))

    monkeypatch.setattr(storage_destinations, "write_destination", write)
    result = await storage_destinations.add_destination(
        {
            "kind": "mysql",
            "name": "Local Mirror",
            "host": "127.0.0.1",
            "port": 3306,
            "database": "junctionnow",
            "username": "bot",
            "password": "private-value",
            "features": ["posts", "activity"],
        },
        {"posts": {}, "analytics": {"events": []}},
    )

    saved = storage_destinations.load_destinations()
    assert result["name"] == "Local Mirror"
    assert saved[0]["password"] == "private-value"
    assert saved[0]["status"] == "active"
    assert writes[0][1] == {"posts": {}, "activity": {"events": []}}


@pytest.mark.asyncio
async def test_failed_destination_is_not_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(
        storage_destinations,
        "PRIVATE_FILE",
        tmp_path / "private" / "storage.json",
    )

    async def fail(*args):
        raise ConnectionError

    monkeypatch.setattr(storage_destinations, "write_destination", fail)

    with pytest.raises(ConnectionError):
        await storage_destinations.add_destination(
            {
                "kind": "postgresql",
                "name": "Broken",
                "host": "127.0.0.1",
                "database": "junctionnow",
                "username": "bot",
                "password": "private-value",
                "features": ["posts"],
            },
            {},
        )

    assert storage_destinations.load_destinations() == []
