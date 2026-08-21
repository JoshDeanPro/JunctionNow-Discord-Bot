import pytest

from app.control import ControlWorker


@pytest.mark.asyncio
async def test_broadcast_withdrawal_is_persistent():
    state = {
        "broadcasts": {
            "notice": {
                "id": "notice",
                "message": "Example",
                "deliveries": [],
                "withdrawn": False,
            }
        }
    }

    class Store:
        async def snapshot(self):
            return state

        async def mutate(self, change):
            return change(state)

    bot = type(
        "Bot",
        (),
        {
            "store": Store(),
            "get_guild": lambda self, guild_id: None,
        },
    )()

    await ControlWorker(bot).withdraw_broadcast({"broadcast_id": "notice"})

    assert state["broadcasts"]["notice"]["withdrawn"] is True
    assert state["broadcasts"]["notice"]["withdrawn_at"]


@pytest.mark.asyncio
async def test_withdrawn_broadcast_is_idempotent():
    state = {
        "broadcasts": {
            "notice": {
                "id": "notice",
                "deliveries": [],
                "withdrawn": True,
            }
        }
    }

    class Store:
        async def snapshot(self):
            return state

        async def mutate(self, change):
            raise AssertionError("An already withdrawn broadcast must not change.")

    bot = type("Bot", (), {"store": Store()})()

    await ControlWorker(bot).withdraw_broadcast({"broadcast_id": "notice"})
