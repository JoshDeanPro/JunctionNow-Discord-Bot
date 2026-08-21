from __future__ import annotations

import os

import discord

from app.local_config import read_values


class OperatorChannels:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def photos(self) -> discord.TextChannel | discord.Webhook | None:
        values = read_values()

        def setting(name: str) -> str:
            return values.get(name) or os.environ.get(name, "").strip()

        webhook_url = setting("PHOTO_WEBHOOK_URL")

        if webhook_url:
            try:
                return discord.Webhook.from_url(webhook_url, client=self.bot)
            except ValueError:
                return None

        guild_id = setting("MANAGEMENT_GUILD_ID")
        channel_id = setting("MANAGEMENT_CHANNEL_ID")

        if not guild_id or not channel_id:
            return None

        try:
            guild = self.bot.get_guild(int(guild_id))
            channel = guild.get_channel(int(channel_id)) if guild else None
        except ValueError:
            return None

        return channel if isinstance(channel, discord.TextChannel) else None
