from unittest.mock import AsyncMock

import pytest

from app.sync.reconciler import SyncEngine
from app.sync.types import FeedPost


@pytest.mark.asyncio
async def test_lightweight_post_check_skips_existing_article_updates():
    state = {"system": {}, "guilds": {}, "banned_guilds": {}}

    class Store:
        get_post = AsyncMock(return_value={"post_id": "existing"})
        upsert_post = AsyncMock()
        record_event = AsyncMock()

        async def mutate(self, change):
            return change(state)

        async def snapshot(self):
            return state

    bot = type(
        "Bot",
        (),
        {
            "control_worker": type(
                "Control",
                (),
                {"send_scheduled_broadcasts": AsyncMock()},
            )(),
        },
    )()
    store = Store()
    engine = SyncEngine(bot, store)
    engine.feed.fetch = AsyncMock(
        return_value=[
            FeedPost(
                post_id="existing",
                title="Existing",
                body="RSS body",
                url="https://junctionnow.com/existing/",
                image_url=None,
                published_at=None,
                rss_hash="rss",
                page_hash=None,
            )
        ]
    )

    result = await engine.sync_once(inspect_articles=False)

    assert result == {"status": "ok", "posts": 1}
    engine.feed.fetch.assert_awaited_once_with(inspect_articles=False)
    store.upsert_post.assert_not_awaited()
