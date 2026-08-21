from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime

import discord

from app.storage import JsonStateStore
from app.sync.delivery import (
    DeliveryError,
    DeliveryService,
)
from app.sync.feed import (
    JunctionNowFeedClient,
)
from app.sync.types import FeedPost

logger = logging.getLogger(__name__)


def source_hash(
    rss_hash: str,
    page_hash: str,
) -> str:
    return hashlib.sha256(
        (
            rss_hash
            + "|"
            + page_hash
        ).encode("utf-8")
    ).hexdigest()


def parse_iso(
    value: str | None,
) -> datetime | None:
    if not value:
        return None

    try:
        parsed = (
            datetime.fromisoformat(
                value
            )
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=UTC
        )

    return parsed.astimezone(
        UTC
    )


class SyncEngine:
    def __init__(
        self,
        bot,
        store: JsonStateStore,
    ) -> None:
        self.bot = bot
        self.store = store
        self.feed = (
            JunctionNowFeedClient()
        )

        self.delivery = (
            DeliveryService(bot)
        )

        self.lock = asyncio.Lock()

        self.last_sync_started_at = None
        self.last_sync_finished_at = None
        self.last_sync_error = None
        self.last_post_count = 0
        self.last_article_check_at = None

    def should_send_new(
        self,
        post: FeedPost,
        stored_post: dict,
        guild_config: dict,
    ) -> bool:
        configured = parse_iso(
            guild_config.get(
                "configured_at"
            )
        )

        if configured is None:
            return False

        if post.published_at:
            published = (
                post.published_at
                .replace(
                    tzinfo=UTC
                )
                if post.published_at
                .tzinfo is None
                else post.published_at
                .astimezone(UTC)
            )

            return (
                published > configured
            )

        first_seen = parse_iso(
            stored_post.get(
                "first_seen_at"
            )
        )

        if first_seen is None:
            return False

        return (
            first_seen > configured
        )

    async def sync_once(
        self,
        *,
        inspect_articles: bool = True,
    ) -> dict:
        if self.lock.locked():
            return {
                "status": (
                    "already_running"
                ),
                "posts": 0,
            }

        async with self.lock:
            self.last_sync_started_at = (
                datetime.now(
                    UTC
                ).isoformat()
            )

            self.last_sync_error = None

            try:
                posts = await self.feed.fetch(inspect_articles=inspect_articles)

                checked_at = datetime.now(UTC)

                def record_checks(state):
                    system = state.setdefault("system", {})
                    system["last_post_check_at"] = checked_at.isoformat()

                    if inspect_articles:
                        system["last_post_update_check_at"] = checked_at.isoformat()

                await self.store.mutate(record_checks)

                if inspect_articles:
                    self.last_article_check_at = checked_at

                self.last_post_count = len(
                    posts
                )

                for post in reversed(
                    posts
                ):
                    previous = (
                        await self.store.get_post(
                            post.post_id
                        )
                    )

                    if previous is not None and not inspect_articles:
                        continue

                    previous_page_hash = (
                        (
                            previous
                            or {}
                        ).get(
                            "page_hash",
                            "",
                        )
                        or ""
                    )

                    effective_page_hash = (
                        post.page_hash
                        if post.page_hash
                        is not None
                        else previous_page_hash
                    )

                    current_source_hash = (
                        source_hash(
                            post.rss_hash,
                            effective_page_hash,
                        )
                    )

                    stored = {
                        "post_id": (
                            post.post_id
                        ),
                        "title": post.title,
                        "body": post.body,
                        "url": post.url,
                        "image_url": (
                            post.image_url
                        ),
                        "published_at": (
                            post.published_at
                            .replace(
                                tzinfo=UTC
                            )
                            .isoformat()
                            if post.published_at
                            else None
                        ),
                        "rss_hash": (
                            post.rss_hash
                        ),
                        "page_hash": (
                            effective_page_hash
                        ),
                        "source_hash": (
                            current_source_hash
                        ),
                    }

                    upsert = (
                        await self.store.upsert_post(
                            stored
                        )
                    )

                    stored_record = (
                        upsert["record"]
                    )

                    if stored_record.get(
                        "withdrawn",
                        False,
                    ):
                        continue

                    state = (
                        await self.store.snapshot()
                    )

                    guilds = state.get(
                        "guilds",
                        {},
                    )

                    banned_guilds = state.get(
                        "banned_guilds",
                        {},
                    )

                    for (
                        guild_id,
                        config,
                    ) in guilds.items():
                        if guild_id in banned_guilds:
                            continue

                        if not (
                            config.get(
                                "enabled"
                            )
                            and config.get(
                                "channel_id"
                            )
                        ):
                            continue

                        guild = self.bot.get_guild(
                            int(guild_id)
                        )

                        if guild is None:
                            continue

                        delivery = (
                            await self.store
                            .get_delivery(
                                guild_id,
                                post.post_id,
                            )
                        )

                        try:
                            if delivery is None:
                                if not (
                                    self.should_send_new(
                                        post,
                                        stored_record,
                                        config,
                                    )
                                ):
                                    continue

                                result = (
                                    await self.delivery
                                    .send_new(
                                        guild,
                                        config,
                                        post,
                                        current_source_hash,
                                        photo_requested=bool(
                                            stored_record.get(
                                                "photo_requested",
                                                False,
                                            )
                                        ),
                                    )
                                )

                                await self.store.save_delivery(
                                    guild_id,
                                    post.post_id,
                                    result,
                                    event_type=(
                                        "message_sent"
                                    ),
                                )

                                continue

                            delivery_hash = (
                                delivery.get(
                                    "source_hash"
                                )
                            )

                            missing_message = (
                                not delivery.get(
                                    "message_id"
                                )
                            )

                            changed = (
                                delivery_hash
                                != current_source_hash
                            )

                            if not (
                                missing_message
                                or changed
                            ):
                                continue

                            result, event_type = (
                                await self.delivery
                                .update_existing(
                                    guild,
                                    config,
                                    delivery,
                                    post,
                                    current_source_hash,
                                    photo_requested=bool(
                                        stored_record.get(
                                            "photo_requested",
                                            False,
                                        )
                                    ),
                                )
                            )

                            await self.store.save_delivery(
                                guild_id,
                                post.post_id,
                                result,
                                event_type=event_type,
                            )

                        except (
                            DeliveryError,
                            discord.HTTPException,
                        ) as exc:
                            logger.warning(
                                "Delivery failed "
                                "guild=%s post=%s: %s",
                                guild_id,
                                post.post_id,
                                exc,
                            )

                            await self.store.record_event(
                                "delivery_error",
                                guild_id=guild_id,
                                metadata={
                                    "post_id": (
                                        post.post_id
                                    ),
                                    "error": (
                                        type(
                                            exc
                                        ).__name__
                                    ),
                                },
                            )

                self.last_sync_finished_at = (
                    datetime.now(
                        UTC
                    ).isoformat()
                )

                await self.bot.control_worker.send_scheduled_broadcasts()

                await self.store.record_event(
                    "sync_complete",
                    metadata={
                        "posts": len(
                            posts
                        ),
                    },
                )

                return {
                    "status": "ok",
                    "posts": len(posts),
                }

            except Exception as exc:
                self.last_sync_error = (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                self.last_sync_finished_at = (
                    datetime.now(
                        UTC
                    ).isoformat()
                )

                await self.store.record_event(
                    "sync_error",
                    metadata={
                        "error": (
                            type(exc).__name__
                        ),
                    },
                )

                logger.exception(
                    "JunctionNow sync failed"
                )

                raise
