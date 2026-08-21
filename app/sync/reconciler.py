from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.config import get_settings
from app.db.models import SourcePost, Subscription
from app.db.session import SessionLocal
from app.sync.delivery import DeliveryService
from app.sync.feed import JunctionNowFeedClient
from app.sync.render import content_hash
from app.sync.types import FeedPost

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SyncEngine:
    def __init__(self, bot) -> None:
        self.bot = bot
        self.settings = get_settings()
        self.feed = JunctionNowFeedClient()
        self.delivery = DeliveryService(bot)
        self.lock = asyncio.Lock()

        self.last_sync_started_at: datetime | None = None
        self.last_sync_finished_at: datetime | None = None
        self.last_sync_error: str | None = None
        self.last_post_count = 0

    async def sync_once(self) -> dict[str, int | str]:
        if self.lock.locked():
            return {"status": "already_running", "posts": 0}

        async with self.lock:
            self.last_sync_started_at = utcnow()
            self.last_sync_error = None

            try:
                posts = await self.feed.fetch()
                posts = posts[: self.settings.max_posts_per_sync]

                self.last_post_count = len(posts)

                async with SessionLocal() as session:
                    subscriptions = (
                        await session.execute(
                            select(Subscription).where(
                                Subscription.enabled.is_(True)
                            )
                        )
                    ).scalars().all()

                    for post in posts:
                        db_post = await self.upsert_post(
                            session,
                            post,
                        )

                        for subscription in subscriptions:
                            await self.delivery.deliver_with_retry(
                                session,
                                subscription,
                                db_post,
                                post,
                            )

                        await session.commit()

                self.last_sync_finished_at = utcnow()

                logger.info(
                    "Sync complete: %s posts, %s subscriptions",
                    len(posts),
                    len(subscriptions),
                )

                return {
                    "status": "ok",
                    "posts": len(posts),
                    "subscriptions": len(subscriptions),
                }

            except Exception as exc:
                self.last_sync_error = str(exc)
                self.last_sync_finished_at = utcnow()
                logger.exception("JunctionNow synchronization failed")
                raise

    async def upsert_post(
        self,
        session,
        post: FeedPost,
    ) -> SourcePost:
        db_post = await session.get(
            SourcePost,
            post.post_id,
        )

        new_hash = content_hash(post)

        if db_post is None:
            db_post = SourcePost(
                post_id=post.post_id,
                revision=max(post.revision, 1),
                content_hash=new_hash,
                status=post.status,
                title=post.title,
                body=post.body,
                url=post.url,
                image_url=post.image_url,
                published_at=post.published_at,
                source_updated_at=post.updated_at,
                last_seen_at=utcnow(),
            )

            session.add(db_post)
            await session.flush()
            return db_post

        changed = db_post.content_hash != new_hash

        if changed:
            db_post.revision = max(
                db_post.revision + 1,
                post.revision,
            )
        elif post.revision > db_post.revision:
            db_post.revision = post.revision

        db_post.content_hash = new_hash
        db_post.status = post.status
        db_post.title = post.title
        db_post.body = post.body
        db_post.url = post.url
        db_post.image_url = post.image_url
        db_post.published_at = post.published_at
        db_post.source_updated_at = post.updated_at
        db_post.last_seen_at = utcnow()

        await session.flush()

        return db_post
