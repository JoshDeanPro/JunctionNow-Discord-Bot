from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands, tasks

from app.bot.commands import JunctionCommands
from app.config import get_settings
from app.management import ManagementManager, ManagementView
from app.photos import PhotoPostView
from app.storage import JsonStateStore
from app.sync.reconciler import SyncEngine

logger = logging.getLogger(__name__)


class JunctionNowBot(commands.Bot):
    def __init__(
        self,
        store: JsonStateStore,
    ) -> None:
        self.settings = get_settings()
        self.store = store

        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            application_id=self.settings.discord_application_id,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        self.sync_engine = SyncEngine(
            self,
            self.store,
        )

        self.management = ManagementManager(self)

        self._ready_notification_sent = False

        self.background_sync.change_interval(
            seconds=max(
                30,
                self.settings.sync_interval_seconds,
            )
        )

    async def setup_hook(self) -> None:
        await self.add_cog(
            JunctionCommands(self)
        )

        await self.tree.sync()

        if self.management.enabled:
            self.add_view(
                ManagementView(
                    self.management
                )
            )

        self.add_view(
            PhotoPostView(self)
        )

        if not self.background_sync.is_running():
            self.background_sync.start()

    async def on_ready(self) -> None:
        logger.info(
            "Logged in as %s (%s); %s guilds",
            self.user,
            self.user.id if self.user else "unknown",
            len(self.guilds),
        )

        for guild in self.guilds:
            await self.store.track_guild(guild)

        if self.management.enabled:
            await self.management.ensure_panel()

            if not self._ready_notification_sent:
                self._ready_notification_sent = True

                await self.management.ensure_private_channels()

    async def on_guild_join(
        self,
        guild: discord.Guild,
    ) -> None:
        await self.store.track_guild(
            guild,
            joined=True,
        )

        if guild.id != self.settings.management_guild_id:
            await self.management.log(
                "Server added",
                f"JunctionNow was added to **{guild.name}**.",
            )

        await self.management.ensure_panel()

    async def on_guild_remove(
        self,
        guild: discord.Guild,
    ) -> None:
        await self.store.mark_guild_removed(
            guild.id
        )

        if guild.id != self.settings.management_guild_id:
            await self.management.log(
                "Server removed",
                f"JunctionNow was removed from **{guild.name}**.",
                warning=True,
            )

        await self.management.ensure_panel()

    async def on_raw_message_delete(
        self,
        payload: discord.RawMessageDeleteEvent,
    ) -> None:
        panel_id = await self.management.panel_message_id()

        if panel_id == payload.message_id:
            await self.management.save_panel_message_id(0)
            await self.management.ensure_panel()
            return

        await self.store.mark_message_deleted(
            payload.message_id
        )

    @tasks.loop(seconds=300)
    async def background_sync(self) -> None:
        if not await self.management.feed_enabled():
            return

        try:
            await self.sync_engine.sync_once()

            await self.management.ensure_panel()

        except Exception as exc:
            logger.exception(
                "Scheduled JunctionNow sync failed"
            )

            await self.management.log(
                "Feed sync failed",
                f"Scheduled check failed with {type(exc).__name__}.",
                warning=True,
            )

            await self.management.ensure_panel()

    @background_sync.before_loop
    async def before_background_sync(self) -> None:
        await self.wait_until_ready()

        if not self.settings.sync_on_startup:
            await asyncio.sleep(
                max(
                    30,
                    self.settings.sync_interval_seconds,
                )
            )
