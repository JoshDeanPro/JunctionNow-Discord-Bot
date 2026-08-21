from unittest.mock import AsyncMock

import pytest

from app.control import ControlWorker


@pytest.mark.asyncio
async def test_ban_disables_delivery_before_leaving():
    state = {
        "guilds": {
            "123": {
                "enabled": True,
                "channel_id": "456",
            }
        }
    }

    class Store:
        async def mutate(self, change):
            return change(state)

    guild = type("Guild", (), {"leave": AsyncMock()})()
    bot = type(
        "Bot",
        (),
        {
            "store": Store(),
            "get_guild": lambda self, guild_id: guild,
        },
    )()

    await ControlWorker(bot).ban_server({"guild_id": 123})

    assert state["guilds"]["123"]["enabled"] is False
    assert "123" in state["banned_guilds"]
    guild.leave.assert_awaited_once()


@pytest.mark.asyncio
async def test_manual_post_update_runs_full_sync():
    sync_engine = type("SyncEngine", (), {"sync_once": AsyncMock(return_value={"status": "ok"})})()
    bot = type("Bot", (), {"sync_engine": sync_engine})()

    await ControlWorker(bot).execute("sync_now", {})

    sync_engine.sync_once.assert_awaited_once()
