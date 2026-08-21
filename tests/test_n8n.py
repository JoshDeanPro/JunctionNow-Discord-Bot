import json
from pathlib import Path


def workflow(name: str) -> dict:
    return json.loads((Path("n8n") / name).read_text(encoding="utf-8"))


def test_n8n_workflows_are_importable_and_private():
    setup = workflow("01-initialize.json")
    posts = workflow("02-posts.json")
    exported = json.dumps([setup, posts])

    assert setup["active"] is False
    assert posts["active"] is False
    assert "credentials" not in exported
    assert "DISCORD_TOKEN" not in exported
    assert "api/webhooks/" not in exported


def test_n8n_setup_seeds_current_posts_without_delivery():
    setup = workflow("01-initialize.json")
    node_types = {node["type"] for node in setup["nodes"]}

    assert "n8n-nodes-base.rssFeedRead" in node_types
    assert "n8n-nodes-base.dataTable" in node_types
    assert "n8n-nodes-base.httpRequest" not in node_types


def test_n8n_posts_track_and_update_discord_messages_safely():
    posts = workflow("02-posts.json")
    by_name = {node["name"]: node for node in posts["nodes"]}
    serialized = json.dumps(posts)

    assert by_name["Every 30 Minutes"]["parameters"]["rule"]["interval"][0] == {
        "field": "minutes",
        "minutesInterval": 30,
    }
    assert "Update Posts Now" in by_name
    assert by_name["Edit Discord Message"]["parameters"]["method"] == "PATCH"
    assert by_name["Create Discord Message"]["parameters"]["method"] == "POST"
    assert by_name["Recreate Discord Message"]["parameters"]["method"] == "POST"
    assert "message_id" in serialized
    assert "parse: []" in serialized
    assert "@everyone" not in serialized
    assert "@here" not in serialized
