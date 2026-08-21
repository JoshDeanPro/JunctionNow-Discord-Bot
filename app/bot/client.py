from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

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


def check_due(value: str | None, interval: int, *, current: datetime | None = None) -> bool:
    if not value:
        return True

    try:
        checked = datetime.fromisoformat(value)
    except ValueError:
        return True

    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=UTC)

    current = current or datetime.now(UTC)
    return (current - checked.astimezone(UTC)).total_seconds() >= interval


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

        self.post_interval_seconds = self.settings.post_interval_seconds
        self.post_update_interval_seconds = self.settings.post_update_interval_seconds

        self.background_sync.change_interval(
            seconds=min(self.post_interval_seconds, self.post_update_interval_seconds)
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

        state = await self.store.snapshot()
        banned_guilds = state.get("banned_guilds", {})

        for guild in list(self.guilds):
            if str(guild.id) in banned_guilds:
                await guild.leave()
                continue

            await self.store.track_guild(
                guild
            )

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

    @tasks.loop(seconds=1800)
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

        system = state.get("system", {})
        current = datetime.now(UTC)
        posts_due = check_due(
            system.get("last_post_check_at"), self.post_interval_seconds, current=current
        )
        updates_due = check_due(
            system.get("last_post_update_check_at"),
            self.post_update_interval_seconds,
            current=current,
        )

        if not posts_due and not updates_due:
            return

        try:
            await self.sync_engine.sync_once(inspect_articles=updates_due)

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
                min(self.post_interval_seconds, self.post_update_interval_seconds)
            )
