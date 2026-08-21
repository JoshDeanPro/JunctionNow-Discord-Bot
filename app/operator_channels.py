from __future__ import annotations

import discord


class OperatorChannels:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def ensure(self) -> None:
        guild_id = self.bot.settings.management_guild_id

        if not guild_id:
            return

        guild = self.bot.get_guild(guild_id)

        if guild is None:
            return

        state = await self.bot.store.snapshot()

        raw = (
            state.get("operator", {})
            .get("photo_channel_id")
        )

        if raw:
            channel = guild.get_channel(int(raw))

            if channel:
                return

        existing = discord.utils.get(
            guild.text_channels,
            name="jn-photo-submissions",
        )

        if existing:
            await self._save(existing.id)
            return

        member = guild.me

        if (
            member is None
            or not member.guild_permissions.manage_channels
        ):
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
            ),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
        }

        for user_id in self.bot.settings.management_operator_ids:
            operator = guild.get_member(user_id)

            if operator:
                overwrites[operator] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                )

        channel = await guild.create_text_channel(
            "jn-photo-submissions",
            overwrites=overwrites,
            reason="JunctionNow photo submissions",
        )

        await self._save(channel.id)

    async def _save(self, channel_id: int) -> None:
        def change(state):
            operator = state.setdefault(
                "operator",
                {},
            )

            operator["photo_channel_id"] = str(
                channel_id
            )

        await self.bot.store.mutate(change)

    async def photos(
        self,
    ) -> discord.TextChannel | None:
        state = await self.bot.store.snapshot()

        raw = (
            state.get("operator", {})
            .get("photo_channel_id")
        )

        if not raw:
            return None

        channel = self.bot.get_channel(
            int(raw)
        )

        if isinstance(
            channel,
            discord.TextChannel,
        ):
            return channel

        return None
