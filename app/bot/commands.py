from __future__ import annotations

from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from app.analytics.events import record_event
from app.db.models import Guild, Subscription
from app.db.session import SessionLocal


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def has_manage_server(
    interaction: discord.Interaction,
) -> bool:
    if interaction.guild is None:
        await interaction.response.send_message(
            "This command must be used inside a Discord server.",
            ephemeral=True,
        )
        return False

    permissions = interaction.user.guild_permissions

    if not (
        permissions.manage_guild
        or permissions.administrator
    ):
        await interaction.response.send_message(
            "You need the Manage Server permission to configure JunctionNow.",
            ephemeral=True,
        )
        return False

    return True


class JunctionCommands(
    commands.GroupCog,
    group_name="junction",
    group_description="Configure JunctionNow updates",
):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="setup",
        description="Choose the channel where JunctionNow should post",
    )
    @app_commands.describe(
        channel="Channel where JunctionNow should post"
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        if not await has_manage_server(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        assert interaction.guild is not None

        bot_member = interaction.guild.me

        if bot_member is None:
            await interaction.followup.send(
                "I could not determine my permissions in this server.",
                ephemeral=True,
            )
            return

        permissions = channel.permissions_for(bot_member)

        missing: list[str] = []

        if not permissions.view_channel:
            missing.append("View Channel")

        if not permissions.send_messages:
            missing.append("Send Messages")

        if not permissions.embed_links:
            missing.append("Embed Links")

        if missing:
            await interaction.followup.send(
                "I cannot use that channel. Missing: "
                + ", ".join(missing),
                ephemeral=True,
            )
            return

        async with SessionLocal() as session:
            guild = await session.get(
                Guild,
                interaction.guild.id,
            )

            if guild is None:
                guild = Guild(
                    guild_id=interaction.guild.id,
                    name=interaction.guild.name,
                    enabled=True,
                )
                session.add(guild)
                await session.flush()

            guild.enabled = True
            guild.removed_at = None
            guild.last_seen_at = utcnow()

            subscriptions = (
                await session.execute(
                    select(Subscription).where(
                        Subscription.guild_id == interaction.guild.id
                    )
                )
            ).scalars().all()

            current = next(
                (
                    item
                    for item in subscriptions
                    if item.enabled
                    and item.channel_id == channel.id
                ),
                None,
            )

            if current is not None:
                current.status = "active"
                await session.commit()

                await interaction.followup.send(
                    f"JunctionNow is already configured for {channel.mention}.",
                    ephemeral=True,
                )
                return

            for item in subscriptions:
                if item.enabled:
                    item.enabled = False
                    item.status = "replaced"
                    item.updated_at = utcnow()

            subscription = Subscription(
                guild_id=interaction.guild.id,
                channel_id=channel.id,
                enabled=True,
                status="active",
            )

            session.add(subscription)

            await record_event(
                session,
                "subscription_created",
                guild_id=interaction.guild.id,
                metadata={
                    "channel_id": channel.id,
                },
            )

            await session.commit()

        await interaction.followup.send(
            f"JunctionNow updates are enabled in {channel.mention}.",
            ephemeral=True,
        )

    @app_commands.command(
        name="status",
        description="Show the current JunctionNow configuration",
    )
    async def status(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not await has_manage_server(interaction):
            return

        assert interaction.guild is not None

        async with SessionLocal() as session:
            subscription = (
                await session.execute(
                    select(Subscription).where(
                        Subscription.guild_id == interaction.guild.id,
                        Subscription.enabled.is_(True),
                    )
                )
            ).scalar_one_or_none()

        if subscription is None:
            await interaction.response.send_message(
                "JunctionNow updates are disabled.",
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(
            subscription.channel_id
        )

        channel_text = (
            channel.mention
            if channel
            else f"{subscription.channel_id} (channel unavailable)"
        )

        await interaction.response.send_message(
            "\n".join(
                [
                    "**JunctionNow Status**",
                    "Enabled: **Yes**",
                    f"Channel: {channel_text}",
                    f"State: `{subscription.status}`",
                ]
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="disable",
        description="Disable JunctionNow updates",
    )
    async def disable(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not await has_manage_server(interaction):
            return

        assert interaction.guild is not None

        async with SessionLocal() as session:
            subscriptions = (
                await session.execute(
                    select(Subscription).where(
                        Subscription.guild_id == interaction.guild.id,
                        Subscription.enabled.is_(True),
                    )
                )
            ).scalars().all()

            for subscription in subscriptions:
                subscription.enabled = False
                subscription.status = "disabled"
                subscription.updated_at = utcnow()

            await record_event(
                session,
                "subscription_disabled",
                guild_id=interaction.guild.id,
            )

            await session.commit()

        await interaction.response.send_message(
            "JunctionNow updates are now disabled.",
            ephemeral=True,
        )

    @app_commands.command(
        name="enable",
        description="Re-enable the latest JunctionNow channel",
    )
    async def enable(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not await has_manage_server(interaction):
            return

        assert interaction.guild is not None

        async with SessionLocal() as session:
            subscriptions = (
                await session.execute(
                    select(Subscription)
                    .where(
                        Subscription.guild_id
                        == interaction.guild.id
                    )
                    .order_by(Subscription.id.desc())
                )
            ).scalars().all()

            if not subscriptions:
                await interaction.response.send_message(
                    "Run /junction setup first.",
                    ephemeral=True,
                )
                return

            target = subscriptions[0]

            for subscription in subscriptions:
                subscription.enabled = (
                    subscription.id == target.id
                )

            target.status = "active"
            target.updated_at = utcnow()

            await record_event(
                session,
                "subscription_enabled",
                guild_id=interaction.guild.id,
                metadata={
                    "channel_id": target.channel_id,
                },
            )

            await session.commit()

        channel = interaction.guild.get_channel(
            target.channel_id
        )

        if channel:
            text = (
                f"JunctionNow updates are enabled in "
                f"{channel.mention}."
            )
        else:
            text = (
                "JunctionNow was enabled, but its saved channel "
                "no longer exists. Run /junction setup again."
            )

        await interaction.response.send_message(
            text,
            ephemeral=True,
        )

    @app_commands.command(
        name="test",
        description="Send a test post to the configured channel",
    )
    async def test(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not await has_manage_server(interaction):
            return

        assert interaction.guild is not None

        async with SessionLocal() as session:
            subscription = (
                await session.execute(
                    select(Subscription).where(
                        Subscription.guild_id == interaction.guild.id,
                        Subscription.enabled.is_(True),
                    )
                )
            ).scalar_one_or_none()

        if subscription is None:
            await interaction.response.send_message(
                "Run /junction setup first.",
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(
            subscription.channel_id
        )

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "The configured channel no longer exists. "
                "Run /junction setup again.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="JunctionNow Bot Test",
            description=(
                "Configuration is working. "
                "JunctionNow posts will be delivered here."
            ),
        )
        embed.set_footer(text="JunctionNow")

        try:
            message = await channel.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I no longer have permission to send messages there.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Test sent successfully: {message.jump_url}",
            ephemeral=True,
        )

    @app_commands.command(
        name="sync",
        description="Immediately check JunctionNow for updates",
    )
    async def sync(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not await has_manage_server(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        try:
            result = await self.bot.sync_engine.sync_once()
        except Exception as exc:
            await interaction.followup.send(
                f"Synchronization failed: {type(exc).__name__}",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            (
                "Synchronization complete. "
                f"Checked {result.get('posts', 0)} source posts."
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="help",
        description="Show JunctionNow bot commands",
    )
    async def help_command(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.send_message(
            "\n".join(
                [
                    "**JunctionNow Bot**",
                    "",
                    "/junction setup - choose posting channel",
                    "/junction status - view configuration",
                    "/junction enable - enable updates",
                    "/junction disable - disable updates",
                    "/junction test - send a test",
                    "/junction sync - synchronize now",
                    "/junction help - show commands",
                ]
            ),
            ephemeral=True,
        )
