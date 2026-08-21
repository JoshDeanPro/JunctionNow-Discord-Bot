from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import discord
from discord.ext import commands, tasks

from app.analytics.events import record_event
from app.bot.commands import JunctionCommands
from app.config import get_settings
from app.db.models import Guild
from app.db.session import SessionLocal
from app.sync.reconciler import SyncEngine

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class JunctionNowBot(commands.Bot):
    def __init__(self) -> None:
        self.settings = get_settings()

        intents = discord.Intents.none()
        intents.guilds = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            application_id=self.settings.discord_application_id,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        self.sync_engine = SyncEngine(self)

        self.background_sync.change_interval(
            seconds=max(
                15,
                self.settings.sync_interval_seconds,
            )
        )

    async def setup_hook(self) -> None:
        await self.add_cog(JunctionCommands(self))

        if self.settings.discord_dev_guild_id:
            guild = discord.Object(
                id=self.settings.discord_dev_guild_id
            )

            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

            logger.info(
                "Synced commands to development guild %s",
                self.settings.discord_dev_guild_id,
            )
        else:
            await self.tree.sync()
            logger.info("Synced global application commands")

        if not self.background_sync.is_running():
            self.background_sync.start()

    async def on_ready(self) -> None:
        logger.info(
            "Logged in as %s (%s); connected to %s guilds.",
            self.user,
            self.user.id if self.user else "unknown",
            len(self.guilds),
        )

        async with SessionLocal() as session:
            for guild in self.guilds:
                await self.upsert_guild(
                    session,
                    guild,
                )

            await session.commit()

    async def on_guild_join(
        self,
        guild: discord.Guild,
    ) -> None:
        async with SessionLocal() as session:
            await self.upsert_guild(
                session,
                guild,
            )

            await record_event(
                session,
                "guild_join",
                guild_id=guild.id,
                metadata={
                    "guild_name": guild.name,
                },
            )

            await session.commit()

    async def on_guild_remove(
        self,
        guild: discord.Guild,
    ) -> None:
        async with SessionLocal() as session:
            db_guild = await session.get(
                Guild,
                guild.id,
            )

            if db_guild is not None:
                db_guild.enabled = False
                db_guild.removed_at = utcnow()
                db_guild.last_seen_at = utcnow()

            await record_event(
                session,
                "guild_remove",
                guild_id=guild.id,
            )

            await session.commit()

    async def upsert_guild(
        self,
        session,
        guild: discord.Guild,
    ) -> None:
        db_guild = await session.get(
            Guild,
            guild.id,
        )

        if db_guild is None:
            session.add(
                Guild(
                    guild_id=guild.id,
                    name=guild.name,
                    enabled=True,
                )
            )
            return

        db_guild.name = guild.name
        db_guild.enabled = True
        db_guild.removed_at = None
        db_guild.last_seen_at = utcnow()

    @tasks.loop(seconds=60)
    async def background_sync(self) -> None:
        try:
            await self.sync_engine.sync_once()
        except Exception:
            logger.exception(
                "Scheduled synchronization failed"
            )

    @background_sync.before_loop
    async def before_background_sync(self) -> None:
        await self.wait_until_ready()

        if not self.settings.sync_on_startup:
            await asyncio.sleep(
                max(
                    15,
                    self.settings.sync_interval_seconds,
                )
            )
