from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.events import record_event
from app.db.models import Delivery, SourcePost, Subscription
from app.sync.render import allowed_mentions, build_embed, render_hash
from app.sync.types import FeedPost

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class DeliveryService:
    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot

    async def deliver(
        self,
        session: AsyncSession,
        subscription: Subscription,
        db_post: SourcePost,
        post: FeedPost,
    ) -> None:
        result = await session.execute(
            select(Delivery).where(
                Delivery.subscription_id == subscription.id,
                Delivery.post_id == db_post.post_id,
            )
        )

        delivery = result.scalar_one_or_none()
        desired_hash = render_hash(post)

        if (
            delivery
            and delivery.status == "sent"
            and delivery.render_hash == desired_hash
        ):
            return

        if delivery is None:
            delivery = Delivery(
                subscription_id=subscription.id,
                post_id=db_post.post_id,
                status="pending",
            )
            session.add(delivery)
            await session.flush()

        delivery.attempt_count += 1

        channel = self.bot.get_channel(subscription.channel_id)

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    subscription.channel_id
                )
            except discord.NotFound:
                subscription.status = "channel_missing"
                delivery.status = "channel_missing"
                delivery.last_error = (
                    "Configured Discord channel no longer exists"
                )
                return
            except discord.Forbidden:
                subscription.status = "permission_error"
                delivery.status = "permission_error"
                delivery.last_error = (
                    "Bot cannot access configured Discord channel"
                )
                return

        if not hasattr(channel, "send"):
            delivery.status = "invalid_channel"
            delivery.last_error = "Configured channel is not messageable"
            return

        embed = build_embed(post)

        if delivery.discord_message_id:
            try:
                message = await channel.fetch_message(
                    delivery.discord_message_id
                )

                await message.edit(
                    embed=embed,
                    allowed_mentions=allowed_mentions(),
                )

                delivery.delivered_revision = db_post.revision
                delivery.render_hash = desired_hash
                delivery.status = "sent"
                delivery.last_error = None
                delivery.updated_at = utcnow()

                subscription.status = "active"

                await record_event(
                    session,
                    "message_updated",
                    guild_id=subscription.guild_id,
                    post_id=db_post.post_id,
                )
                return

            except discord.NotFound:
                logger.info(
                    "Discord message %s no longer exists; recreating it.",
                    delivery.discord_message_id,
                )
                delivery.discord_message_id = None

            except discord.Forbidden as exc:
                subscription.status = "permission_error"
                delivery.status = "permission_error"
                delivery.last_error = str(exc)
                return

            except discord.HTTPException as exc:
                delivery.status = "retry"
                delivery.last_error = str(exc)
                raise

        try:
            message = await channel.send(
                embed=embed,
                allowed_mentions=allowed_mentions(),
            )

            delivery.discord_message_id = message.id
            delivery.delivered_revision = db_post.revision
            delivery.render_hash = desired_hash
            delivery.status = "sent"
            delivery.last_error = None
            delivery.sent_at = delivery.sent_at or utcnow()
            delivery.updated_at = utcnow()

            subscription.status = "active"

            await record_event(
                session,
                "message_sent",
                guild_id=subscription.guild_id,
                post_id=db_post.post_id,
            )

        except discord.Forbidden as exc:
            subscription.status = "permission_error"
            delivery.status = "permission_error"
            delivery.last_error = str(exc)

        except discord.HTTPException as exc:
            delivery.status = "retry"
            delivery.last_error = str(exc)
            raise

    async def deliver_with_retry(
        self,
        session: AsyncSession,
        subscription: Subscription,
        db_post: SourcePost,
        post: FeedPost,
    ) -> None:
        delay = 1.0

        for attempt in range(3):
            try:
                await self.deliver(
                    session,
                    subscription,
                    db_post,
                    post,
                )
                return

            except discord.HTTPException:
                if attempt == 2:
                    logger.exception(
                        "Delivery failed after retries: post=%s subscription=%s",
                        db_post.post_id,
                        subscription.id,
                    )
                    return

                await asyncio.sleep(delay)
                delay *= 2
