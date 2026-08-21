from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from app.bot.components import (
    ConfigView,
    StatusView,
)


class JunctionCommands(
    commands.Cog
):
    def __init__(
        self,
        bot,
    ) -> None:
        self.bot = bot

    @app_commands.command(
        name="config",
        description="Configure JunctionNow for this server",
    )
    @app_commands.allowed_installs(
        guilds=True,
        users=False,
    )
    @app_commands.allowed_contexts(
        guilds=True,
        dms=False,
        private_channels=False,
    )
    @app_commands.default_permissions(
        manage_guild=True
    )
    async def config(
        self,
        interaction: discord.Interaction,
    ) -> None:
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "This command can only be used "
                "in a server.",
                ephemeral=True,
            )
            return

        await self.bot.store.track_guild(
            guild
        )

        await self.bot.store.record_event(
            "command_config",
            guild_id=guild.id,
            metadata={
                "user_id": str(
                    interaction.user.id
                ),
            },
        )

        record = (
            await self.bot.store.get_guild(
                guild.id
            )
        )

        view = ConfigView(
            self.bot,
            guild,
            interaction.user.id,
            record,
        )

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )

    @app_commands.command(
        name="status",
        description="Show JunctionNow status for this server",
    )
    @app_commands.allowed_installs(
        guilds=True,
        users=False,
    )
    @app_commands.allowed_contexts(
        guilds=True,
        dms=False,
        private_channels=False,
    )
    @app_commands.default_permissions(
        manage_guild=True
    )
    async def status(
        self,
        interaction: discord.Interaction,
    ) -> None:
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "This command can only be used "
                "in a server.",
                ephemeral=True,
            )
            return

        await self.bot.store.record_event(
            "command_status",
            guild_id=guild.id,
            metadata={
                "user_id": str(
                    interaction.user.id
                ),
            },
        )

        state = await self.bot.store.snapshot()

        record = (
            state
            .get("guilds", {})
            .get(str(guild.id))
        )

        deliveries = (
            state
            .get("deliveries", {})
            .get(str(guild.id), {})
        )

        view = StatusView(
            guild,
            record,
            len(deliveries),
        )

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )
