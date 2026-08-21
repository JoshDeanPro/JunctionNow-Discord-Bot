from __future__ import annotations

from datetime import UTC, datetime

import discord

from app.photos import photo_view
from app.sync.render import (
    build_embed,
    no_mentions,
)
from app.sync.types import FeedPost


def utcnow() -> str:
    return datetime.now(
        UTC
    ).isoformat()


class DeliveryError(
    RuntimeError
):
    pass


class DeliveryService:
    def __init__(
        self,
        bot,
    ) -> None:
        self.bot = bot

    async def get_channel(
        self,
        guild: discord.Guild,
        channel_id: int,
    ):
        channel = guild.get_channel(
            channel_id
        )

        if channel is None:
            try:
                channel = (
                    await guild.fetch_channel(
                        channel_id
                    )
                )
            except (
                discord.NotFound,
                discord.Forbidden,
            ) as exc:
                raise DeliveryError(
                    "Configured channel "
                    "is unavailable"
                ) from exc

        if not isinstance(
            channel,
            discord.TextChannel,
        ):
            raise DeliveryError(
                "Configured channel "
                "is not a text channel"
            )

        member = guild.me

        if member is None:
            raise DeliveryError(
                "Bot guild member "
                "is unavailable"
            )

        permissions = (
            channel.permissions_for(
                member
            )
        )

        required = []

        if not permissions.view_channel:
            required.append(
                "View Channel"
            )

        if not permissions.send_messages:
            required.append(
                "Send Messages"
            )

        if not permissions.embed_links:
            required.append(
                "Embed Links"
            )

        if required:
            raise DeliveryError(
                "Missing permissions: "
                + ", ".join(required)
            )

        return channel

    def mention_payload(
        self,
        guild: discord.Guild,
        role_ids: list[str],
    ) -> tuple[
        str | None,
        discord.AllowedMentions,
    ]:
        roles = []

        member = guild.me

        can_mention_unmentionable = bool(
            member
            and member.guild_permissions
            .mention_everyone
        )

        for raw_id in role_ids:
            try:
                role_id = int(
                    raw_id
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            role = guild.get_role(
                role_id
            )

            if (
                role is None
                or role.is_default()
            ):
                continue

            if (
                role.mentionable
                or can_mention_unmentionable
            ):
                roles.append(
                    role
                )

        if not roles:
            return (
                None,
                discord.AllowedMentions.none(),
            )

        content = " ".join(
            role.mention
            for role in roles
        )

        allowed = (
            discord.AllowedMentions(
                everyone=False,
                users=False,
                roles=roles,
                replied_user=False,
            )
        )

        return content, allowed

    async def send_new(
        self,
        guild: discord.Guild,
        config: dict,
        post: FeedPost,
        source_hash: str,
        *,
        updated: bool = False,
        photo_requested: bool = False,
    ) -> dict:
        channel_id = int(
            config["channel_id"]
        )

        channel = await self.get_channel(
            guild,
            channel_id,
        )

        content, allowed = (
            self.mention_payload(
                guild,
                config.get(
                    "mention_role_ids",
                    [],
                ),
            )
        )

        message = await channel.send(
            content=content,
            embed=build_embed(
                post,
                updated=updated,
            ),
            allowed_mentions=allowed,
            view=photo_view(
                self.bot,
                photo_requested,
            ),
        )

        return {
            "channel_id": str(
                channel.id
            ),
            "message_id": str(
                message.id
            ),
            "source_hash": (
                source_hash
            ),
            "status": "sent",
            "sent_at": utcnow(),
            "updated_at": utcnow(),
        }

    async def update_existing(
        self,
        guild: discord.Guild,
        config: dict,
        delivery: dict,
        post: FeedPost,
        source_hash: str,
        *,
        photo_requested: bool = False,
    ) -> tuple[
        dict,
        str,
    ]:
        message_id = (
            delivery.get(
                "message_id"
            )
        )

        if not message_id:
            replacement = (
                await self.send_new(
                    guild,
                    config,
                    post,
                    source_hash,
                    updated=True,
                    photo_requested=photo_requested,
                )
            )

            replacement[
                "status"
            ] = "recreated"

            return (
                replacement,
                "message_recreated",
            )

        channel_id = int(
            delivery.get(
                "channel_id"
            )
            or config["channel_id"]
        )

        try:
            channel = (
                await self.get_channel(
                    guild,
                    channel_id,
                )
            )

            message = (
                await channel.fetch_message(
                    int(message_id)
                )
            )

        except (
            discord.NotFound,
            DeliveryError,
        ):
            replacement = (
                await self.send_new(
                    guild,
                    config,
                    post,
                    source_hash,
                    updated=True,
                    photo_requested=photo_requested,
                )
            )

            replacement[
                "status"
            ] = "recreated"

            return (
                replacement,
                "message_recreated",
            )

        await message.edit(
            embed=build_embed(
                post,
                updated=True,
            ),
            allowed_mentions=no_mentions(),
            view=photo_view(
                self.bot,
                photo_requested,
            ),
        )

        updated_delivery = dict(
            delivery
        )

        updated_delivery.update(
            {
                "source_hash": (
                    source_hash
                ),
                "status": "updated",
                "updated_at": utcnow(),
            }
        )

        return (
            updated_delivery,
            "message_updated",
        )
