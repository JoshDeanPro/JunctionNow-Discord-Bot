from __future__ import annotations

import logging
from datetime import UTC, datetime

import discord

from app.config import get_settings

logger = logging.getLogger(__name__)


def now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


class ManagementManager:
    def __init__(self, bot) -> None:
        self.bot = bot
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.management_guild_id
            and self.settings.management_channel_id
            and len(self.settings.management_operator_ids) == 2
        )

    def is_operator(self, user_id: int) -> bool:
        return user_id in self.settings.management_operator_ids

    async def interaction_allowed(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if not self.enabled:
            return False

        if interaction.guild_id != self.settings.management_guild_id:
            return False

        if interaction.channel_id != self.settings.management_channel_id:
            return False

        return self.is_operator(interaction.user.id)

    async def get_channel(self) -> discord.TextChannel | None:
        if not self.enabled:
            return None

        channel = self.bot.get_channel(
            self.settings.management_channel_id
        )

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    self.settings.management_channel_id
                )
            except (
                discord.Forbidden,
                discord.NotFound,
                discord.HTTPException,
            ):
                logger.exception(
                    "Management channel could not be loaded"
                )
                return None

        if not isinstance(channel, discord.TextChannel):
            logger.error(
                "Management channel is not a text channel"
            )
            return None

        if channel.guild.id != self.settings.management_guild_id:
            logger.error(
                "Management channel does not belong to management guild"
            )
            return None

        return channel

    async def feed_enabled(self) -> bool:
        state = await self.bot.store.snapshot()

        return bool(
            state.get("system", {}).get(
                "feed_enabled",
                True,
            )
        )

    async def set_feed_enabled(self, enabled: bool) -> None:
        def change(state):
            system = state.setdefault("system", {})
            system["feed_enabled"] = enabled
            system["changed_at"] = datetime.now(UTC).isoformat()

        await self.bot.store.mutate(change)

    async def panel_message_id(self) -> int | None:
        state = await self.bot.store.snapshot()

        value = (
            state.get("management", {})
            .get("panel_message_id")
        )

        if not value:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    async def save_panel_message_id(self, message_id: int) -> None:
        def change(state):
            management = state.setdefault("management", {})
            management["panel_message_id"] = str(message_id)
            management["updated_at"] = datetime.now(UTC).isoformat()

        await self.bot.store.mutate(change)

    async def build_panel_text(self) -> str:
        state = await self.bot.store.snapshot()

        feed_enabled = bool(
            state.get("system", {}).get(
                "feed_enabled",
                True,
            )
        )

        guilds = state.get("guilds", {})
        posts = state.get("posts", {})
        deliveries = state.get("deliveries", {})

        configured = sum(
            1
            for record in guilds.values()
            if record.get("channel_id")
        )

        delivery_count = sum(
            len(items)
            for items in deliveries.values()
        )

        sync_engine = self.bot.sync_engine

        last_sync = (
            sync_engine.last_sync_finished_at
            or "Not yet"
        )

        sync_error = (
            sync_engine.last_sync_error
            or "None"
        )

        return "\n".join(
            [
                "# JunctionNow Management",
                "",
                (
                    "**Feed:** Running"
                    if feed_enabled
                    else "**Feed:** Paused"
                ),
                f"**Servers seen:** {len(guilds)}",
                f"**Servers configured:** {configured}",
                f"**Posts tracked:** {len(posts)}",
                f"**Discord deliveries:** {delivery_count}",
                f"**Last sync:** {last_sync}",
                f"**Last sync error:** {sync_error}",
                "",
                "This panel is for approved JunctionNow operators only.",
            ]
        )

    async def ensure_panel(self) -> None:
        channel = await self.get_channel()

        if channel is None:
            return

        text = await self.build_panel_text()
        view = ManagementView(self, text)

        message_id = await self.panel_message_id()

        if message_id:
            try:
                message = await channel.fetch_message(message_id)

                await message.edit(
                    view=view,
                )

                return

            except discord.NotFound:
                pass

            except discord.HTTPException:
                logger.exception(
                    "Management panel could not be updated"
                )
                return

        try:
            message = await channel.send(
                view=view,
            )

        except discord.HTTPException:
            logger.exception(
                "Management panel could not be created"
            )
            return

        await self.save_panel_message_id(message.id)

    async def notify(
        self,
        title: str,
        description: str,
        *,
        level: str = "info",
    ) -> None:
        channel = await self.get_channel()

        if channel is None:
            return

        if level == "error":
            color = discord.Color.red()
        elif level == "warning":
            color = discord.Color.orange()
        else:
            color = discord.Color.blurple()

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(UTC),
        )

        embed.set_footer(
            text="JunctionNow Management"
        )

        try:
            await channel.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            logger.exception(
                "Management notification could not be sent"
            )

    async def server_summary(self) -> str:
        state = await self.bot.store.snapshot()

        guilds = state.get("guilds", {})

        if not guilds:
            return "No servers have been recorded yet."

        rows = []

        for record in sorted(
            guilds.values(),
            key=lambda item: str(
                item.get("guild_name", "")
            ).lower(),
        ):
            name = record.get("guild_name") or "Unknown server"

            if record.get("removed_at"):
                status = "Removed"
            elif record.get("enabled"):
                status = "Enabled"
            elif record.get("channel_id"):
                status = "Disabled"
            else:
                status = "Not configured"

            rows.append(
                f"• {name}: {status}"
            )

        text = "\n".join(rows)

        if len(text) > 1800:
            text = text[:1797] + "..."

        return text


class ManagementButton(discord.ui.Button):
    def __init__(
        self,
        manager: ManagementManager,
        *,
        label: str,
        custom_id: str,
        style: discord.ButtonStyle,
    ) -> None:
        super().__init__(
            label=label,
            custom_id=custom_id,
            style=style,
        )

        self.manager = manager

    async def allowed(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if await self.manager.interaction_allowed(interaction):
            return True

        await interaction.response.send_message(
            "You do not have access to JunctionNow management.",
            ephemeral=True,
        )

        return False


class RefreshButton(ManagementButton):
    def __init__(self, manager: ManagementManager) -> None:
        super().__init__(
            manager,
            label="Refresh",
            custom_id="jn:management:refresh",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not await self.allowed(interaction):
            return

        await interaction.response.defer(
            ephemeral=True,
        )

        await self.manager.ensure_panel()

        await interaction.followup.send(
            "Management panel refreshed.",
            ephemeral=True,
        )


class SyncButton(ManagementButton):
    def __init__(self, manager: ManagementManager) -> None:
        super().__init__(
            manager,
            label="Sync Now",
            custom_id="jn:management:sync",
            style=discord.ButtonStyle.primary,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not await self.allowed(interaction):
            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        try:
            result = await self.manager.bot.sync_engine.sync_once()

            await self.manager.ensure_panel()

            await interaction.followup.send(
                (
                    "Sync complete. "
                    f"Posts checked: {result.get('posts', 0)}."
                ),
                ephemeral=True,
            )

        except Exception as exc:
            logger.exception(
                "Manual management sync failed"
            )

            await self.manager.notify(
                "Sync failed",
                f"Manual sync failed with {type(exc).__name__}.",
                level="error",
            )

            await interaction.followup.send(
                "Sync failed. Check the management notifications.",
                ephemeral=True,
            )


class ToggleFeedButton(ManagementButton):
    def __init__(self, manager: ManagementManager) -> None:
        super().__init__(
            manager,
            label="Pause / Resume",
            custom_id="jn:management:toggle-feed",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not await self.allowed(interaction):
            return

        current = await self.manager.feed_enabled()
        updated = not current

        await self.manager.set_feed_enabled(updated)

        await interaction.response.defer(
            ephemeral=True,
        )

        await self.manager.ensure_panel()

        word = "resumed" if updated else "paused"

        await self.manager.notify(
            "Feed changed",
            (
                f"Automatic JunctionNow delivery was {word} "
                "from the private management panel."
            ),
        )

        await interaction.followup.send(
            f"Automatic feed delivery is now {word}.",
            ephemeral=True,
        )


class ServersButton(ManagementButton):
    def __init__(self, manager: ManagementManager) -> None:
        super().__init__(
            manager,
            label="Servers",
            custom_id="jn:management:servers",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not await self.allowed(interaction):
            return

        summary = await self.manager.server_summary()

        await interaction.response.send_message(
            summary,
            ephemeral=True,
        )


class ManagementView(discord.ui.LayoutView):
    def __init__(
        self,
        manager: ManagementManager,
        text: str = "# JunctionNow Management",
    ) -> None:
        super().__init__(
            timeout=None,
        )

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(text),
                discord.ui.Separator(),
                discord.ui.ActionRow(
                    SyncButton(manager),
                    RefreshButton(manager),
                    ToggleFeedButton(manager),
                    ServersButton(manager),
                ),
            )
        )
