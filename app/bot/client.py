from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands, tasks

from app.bot.commands import JunctionCommands
from app.config import get_settings
from app.storage import JsonStateStore
from app.sync.reconciler import SyncEngine

logger = logging.getLogger(__name__)


class JunctionNowBot(
    commands.Bot
):
    def __init__(
        self,
        store: JsonStateStore,
    ) -> None:
        self.settings = (
            get_settings()
        )

        self.store = store

        intents = (
            discord.Intents.none()
        )

        intents.guilds = True
        intents.guild_messages = True

        super().__init__(
            command_prefix=(
                commands.when_mentioned
            ),
            intents=intents,
            application_id=(
                self.settings
                .discord_application_id
            ),
            allowed_mentions=(
                discord.AllowedMentions.none()
            ),
        )

        self.sync_engine = SyncEngine(
            self,
            self.store,
        )

        self.background_sync.change_interval(
            seconds=max(
                15,
                self.settings
                .sync_interval_seconds,
            )
        )

    async def setup_hook(
        self,
    ) -> None:
        await self.add_cog(
            JunctionCommands(self)
        )

        commands_synced = (
            await self.tree.sync()
        )

        logger.info(
            "Synced %s global application commands",
            len(commands_synced),
        )

        if not (
            self.background_sync
            .is_running()
        ):
            self.background_sync.start()

    async def on_ready(
        self,
    ) -> None:
        logger.info(
            "Logged in as %s (%s); %s guilds",
            self.user,
            (
                self.user.id
                if self.user
                else "unknown"
            ),
            len(self.guilds),
        )

        for guild in self.guilds:
            await self.store.track_guild(
                guild
            )

    async def on_guild_join(
        self,
        guild: discord.Guild,
    ) -> None:
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

    @tasks.loop(
        seconds=60
    )
    async def background_sync(
        self,
    ) -> None:
        try:
            await self.sync_engine.sync_once()

        except Exception:
            logger.exception(
                "Scheduled synchronization failed"
            )

    @background_sync.before_loop
    async def before_background_sync(
        self,
    ) -> None:
        await self.wait_until_ready()

        if not (
            self.settings
            .sync_on_startup
        ):
            await asyncio.sleep(
                max(
                    15,
                    self.settings
                    .sync_interval_seconds,
                )
            )
