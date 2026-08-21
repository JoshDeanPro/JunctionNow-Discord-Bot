from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands, tasks

from app.bot.commands import JunctionCommands
from app.config import get_settings
from app.control import ControlWorker
from app.operator_channels import OperatorChannels
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
            store,
        )

        self.control_worker = ControlWorker(
            self
        )

        self.operator_channels = (
            OperatorChannels(self)
        )

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

        self.add_view(
            PhotoPostView(self)
        )

        self.background_sync.start()
        self.operator_control.start()

    async def on_ready(self) -> None:
        logger.info(
            "Logged in as %s; %s guilds",
            self.user,
            len(self.guilds),
        )

        for guild in self.guilds:
            await self.store.track_guild(
                guild
            )

        await self.operator_channels.ensure()

    async def on_guild_join(
        self,
        guild: discord.Guild,
    ) -> None:
        state = await self.store.snapshot()

        if str(guild.id) in state.get(
            "banned_guilds",
            {},
        ):
            await guild.leave()
            return

        await self.store.track_guild(
            guild,
            joined=True,
        )

    async def on_guild_remove(
        self,
        guild: discord.Guild,
    ) -> None:
        await self.store.mark_guild_removed(
            guild.id
        )

    async def on_raw_message_delete(
        self,
        payload: discord.RawMessageDeleteEvent,
    ) -> None:
        await self.store.mark_message_deleted(
            payload.message_id
        )

    @tasks.loop(seconds=1)
    async def operator_control(
        self,
    ) -> None:
        await self.control_worker.run_once()

    @operator_control.before_loop
    async def before_operator_control(
        self,
    ) -> None:
        await self.wait_until_ready()

    @tasks.loop(seconds=300)
    async def background_sync(
        self,
    ) -> None:
        state = await self.store.snapshot()

        if not state.get(
            "system",
            {},
        ).get(
            "feed_enabled",
            True,
        ):
            return

        try:
            await self.sync_engine.sync_once()

        except Exception:
            logger.exception(
                "Scheduled feed check failed"
            )

    @background_sync.before_loop
    async def before_background_sync(
        self,
    ) -> None:
        await self.wait_until_ready()

        if not self.settings.sync_on_startup:
            await asyncio.sleep(
                max(
                    30,
                    self.settings.sync_interval_seconds,
                )
            )
