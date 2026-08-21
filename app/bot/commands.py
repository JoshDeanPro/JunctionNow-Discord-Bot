from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from app.bot.components import ConfigView


class JunctionCommands(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="setup",
        description="Set up JunctionNow for this server",
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
        manage_guild=True,
    )
    @app_commands.checks.has_permissions(
        manage_guild=True,
    )
    async def setup(
        self,
        interaction: discord.Interaction,
    ) -> None:
        guild = interaction.guild

        if guild is None:
            return

        await self.bot.store.track_guild(guild)

        record = await self.bot.store.get_guild(
            guild.id
        )

        if record and record.get("channel_id"):
            await interaction.response.send_message(
                "JunctionNow is already set up here. Use `/edit` to make changes.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            view=ConfigView(
                self.bot,
                guild,
                interaction.user.id,
                record,
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="edit",
        description="Change JunctionNow settings for this server",
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
        manage_guild=True,
    )
    @app_commands.checks.has_permissions(
        manage_guild=True,
    )
    async def edit(
        self,
        interaction: discord.Interaction,
    ) -> None:
        guild = interaction.guild

        if guild is None:
            return

        record = await self.bot.store.get_guild(guild.id)

        if not record or not record.get("channel_id"):
            await interaction.response.send_message(
                "JunctionNow is not set up here yet. Use `/setup` first.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            view=ConfigView(
                self.bot,
                guild,
                interaction.user.id,
                record,
            ),
            ephemeral=True,
        )

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(
            error,
            app_commands.MissingPermissions,
        ):
            message = (
                "You need Manage Server permission "
                "to use this command."
            )

            if interaction.response.is_done():
                await interaction.followup.send(
                    message,
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    message,
                    ephemeral=True,
                )

            return

        raise error
