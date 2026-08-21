from __future__ import annotations

import discord

from app.storage import JsonStateStore


def role_summary(
    guild: discord.Guild,
    role_ids: list[str],
) -> str:
    mentions = []

    for raw_id in role_ids:
        try:
            role_id = int(
                raw_id
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        role = guild.get_role(
            role_id
        )

        if role:
            mentions.append(
                role.mention
            )

    return (
        ", ".join(mentions)
        if mentions
        else "None"
    )


def config_text(
    guild: discord.Guild,
    record: dict | None,
) -> str:
    record = record or {}

    channel_id = record.get(
        "channel_id"
    )

    channel = (
        guild.get_channel(
            int(channel_id)
        )
        if channel_id
        else None
    )

    channel_text = (
        channel.mention
        if channel
        else "Not configured"
    )

    roles = role_summary(
        guild,
        record.get(
            "mention_role_ids",
            [],
        ),
    )

    enabled = bool(
        record.get(
            "enabled"
        )
    )

    status = (
        "Enabled"
        if enabled
        else "Disabled"
    )

    return "\n".join(
        [
            "# JunctionNow Configuration",
            "",
            f"**Status:** {status}",
            f"**Posting channel:** {channel_text}",
            f"**Mention roles:** {roles}",
            "",
            (
                "Choose an existing channel below, "
                "or use **Make Channel**."
            ),
            (
                "Role mentions are optional. "
                "Article text itself can never create pings."
            ),
        ]
    )


class ChannelPicker(
    discord.ui.ChannelSelect
):
    def __init__(
        self,
        panel: ConfigView,
    ) -> None:
        super().__init__(
            custom_id="jn:config:channel",
            placeholder=(
                "Choose posting channel"
            ),
            min_values=1,
            max_values=1,
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.news,
            ],
        )

        self.panel = panel

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not self.values:
            return

        channel_id = int(
            self.values[0].id
        )

        await self.panel.set_channel(
            interaction,
            channel_id,
            created_by_bot=False,
        )


class RolePicker(
    discord.ui.RoleSelect
):
    def __init__(
        self,
        panel: ConfigView,
    ) -> None:
        super().__init__(
            custom_id="jn:config:roles",
            placeholder=(
                "Choose roles to mention"
            ),
            min_values=1,
            max_values=3,
        )

        self.panel = panel

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self.panel.set_roles(
            interaction,
            list(self.values),
        )


class MakeChannelButton(
    discord.ui.Button
):
    def __init__(
        self,
        panel: ConfigView,
        *,
        disabled: bool,
    ) -> None:
        super().__init__(
            custom_id="jn:config:make-channel",
            label="Make Channel",
            style=discord.ButtonStyle.primary,
            disabled=disabled,
        )

        self.panel = panel

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self.panel.make_channel(
            interaction
        )


class NoMentionsButton(
    discord.ui.Button
):
    def __init__(
        self,
        panel: ConfigView,
    ) -> None:
        super().__init__(
            custom_id="jn:config:no-mentions",
            label="No Mentions",
            style=discord.ButtonStyle.secondary,
        )

        self.panel = panel

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self.panel.clear_roles(
            interaction
        )


class ToggleButton(
    discord.ui.Button
):
    def __init__(
        self,
        panel: ConfigView,
        enabled: bool,
    ) -> None:
        super().__init__(
            custom_id="jn:config:toggle",
            label=(
                "Disable"
                if enabled
                else "Enable"
            ),
            style=(
                discord.ButtonStyle.danger
                if enabled
                else discord.ButtonStyle.success
            ),
        )

        self.panel = panel

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self.panel.toggle(
            interaction
        )


class ConfigView(
    discord.ui.LayoutView
):
    def __init__(
        self,
        bot,
        guild: discord.Guild,
        owner_id: int,
        record: dict | None,
    ) -> None:
        super().__init__(
            timeout=300
        )

        self.bot = bot
        self.store: JsonStateStore = (
            bot.store
        )

        self.guild = guild
        self.owner_id = owner_id
        self.record = record or {}

        member = guild.me

        can_make_channel = bool(
            member
            and member.guild_permissions
            .manage_channels
        )

        buttons = discord.ui.ActionRow(
            MakeChannelButton(
                self,
                disabled=(
                    not can_make_channel
                ),
            ),
            NoMentionsButton(self),
            ToggleButton(
                self,
                bool(
                    self.record.get(
                        "enabled"
                    )
                ),
            ),
        )

        container = discord.ui.Container(
            discord.ui.TextDisplay(
                config_text(
                    guild,
                    self.record,
                )
            ),
            discord.ui.Separator(),
            discord.ui.ActionRow(
                ChannelPicker(self)
            ),
            discord.ui.ActionRow(
                RolePicker(self)
            ),
            buttons,
        )

        self.add_item(
            container
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if (
            interaction.user.id
            != self.owner_id
        ):
            await interaction.response.send_message(
                "This configuration panel "
                "belongs to another server manager.",
                ephemeral=True,
            )
            return False

        permissions = getattr(
            interaction.user,
            "guild_permissions",
            None,
        )

        if not (
            permissions
            and permissions.manage_guild
        ):
            await interaction.response.send_message(
                "Manage Server permission "
                "is required.",
                ephemeral=True,
            )
            return False

        return True

    async def refresh(
        self,
        interaction: discord.Interaction,
    ) -> None:
        record = await self.store.get_guild(
            self.guild.id
        )

        view = ConfigView(
            self.bot,
            self.guild,
            self.owner_id,
            record,
        )

        await interaction.response.edit_message(
            view=view
        )

    async def set_channel(
        self,
        interaction: discord.Interaction,
        channel_id: int,
        *,
        created_by_bot: bool,
    ) -> None:
        channel = self.guild.get_channel(
            channel_id
        )

        if not isinstance(
            channel,
            discord.TextChannel,
        ):
            try:
                fetched = (
                    await self.guild.fetch_channel(
                        channel_id
                    )
                )
            except (
                discord.NotFound,
                discord.Forbidden,
            ):
                fetched = None

            channel = (
                fetched
                if isinstance(
                    fetched,
                    discord.TextChannel,
                )
                else None
            )

        if channel is None:
            await interaction.response.send_message(
                "That channel is unavailable.",
                ephemeral=True,
            )
            return

        member = self.guild.me

        if member is None:
            await interaction.response.send_message(
                "Unable to check bot permissions.",
                ephemeral=True,
            )
            return

        permissions = (
            channel.permissions_for(
                member
            )
        )

        missing = []

        if not permissions.view_channel:
            missing.append(
                "View Channel"
            )

        if not permissions.send_messages:
            missing.append(
                "Send Messages"
            )

        if not permissions.embed_links:
            missing.append(
                "Embed Links"
            )

        if missing:
            await interaction.response.send_message(
                "I cannot use that channel. "
                "Missing: "
                + ", ".join(missing),
                ephemeral=True,
            )
            return

        await self.store.configure_channel(
            self.guild,
            channel.id,
            interaction.user.id,
            created_by_bot=(
                created_by_bot
            ),
        )

        await self.refresh(
            interaction
        )

    async def make_channel(
        self,
        interaction: discord.Interaction,
    ) -> None:
        member = self.guild.me

        if not (
            member
            and member.guild_permissions
            .manage_channels
        ):
            await interaction.response.send_message(
                "I need Manage Channels "
                "to create a channel.",
                ephemeral=True,
            )
            return

        try:
            channel = (
                await self.guild
                .create_text_channel(
                    "junction-now",
                    topic=(
                        "Latest posts and updates "
                        "from JunctionNow"
                    ),
                    reason=(
                        "JunctionNow /config "
                        "Make Channel"
                    ),
                )
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Discord refused the channel "
                "creation because I do not have "
                "sufficient permissions.",
                ephemeral=True,
            )
            return

        await self.store.configure_channel(
            self.guild,
            channel.id,
            interaction.user.id,
            created_by_bot=True,
        )

        await self.store.record_event(
            "channel_created",
            guild_id=self.guild.id,
            metadata={
                "channel_id": str(
                    channel.id
                ),
            },
        )

        await self.refresh(
            interaction
        )

    async def set_roles(
        self,
        interaction: discord.Interaction,
        roles: list[discord.Role],
    ) -> None:
        member = self.guild.me

        can_mention_unmentionable = bool(
            member
            and member.guild_permissions
            .mention_everyone
        )

        invalid = []

        selected = []

        for role in roles:
            if role.is_default():
                invalid.append(
                    "@everyone"
                )
                continue

            if (
                not role.mentionable
                and not can_mention_unmentionable
            ):
                invalid.append(
                    role.name
                )
                continue

            selected.append(
                role.id
            )

        if invalid:
            await interaction.response.send_message(
                "I cannot mention these roles: "
                + ", ".join(invalid)
                + ". Make the role mentionable, "
                "or give the bot permission "
                "to mention roles.",
                ephemeral=True,
            )
            return

        await self.store.configure_roles(
            self.guild.id,
            selected,
            interaction.user.id,
        )

        await self.refresh(
            interaction
        )

    async def clear_roles(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self.store.configure_roles(
            self.guild.id,
            [],
            interaction.user.id,
        )

        await self.refresh(
            interaction
        )

    async def toggle(
        self,
        interaction: discord.Interaction,
    ) -> None:
        record = await self.store.get_guild(
            self.guild.id
        )

        record = record or {}

        current = bool(
            record.get(
                "enabled"
            )
        )

        if (
            not current
            and not record.get(
                "channel_id"
            )
        ):
            await interaction.response.send_message(
                "Choose or make a channel first.",
                ephemeral=True,
            )
            return

        await self.store.set_enabled(
            self.guild.id,
            not current,
            interaction.user.id,
        )

        await self.refresh(
            interaction
        )


class StatusView(
    discord.ui.LayoutView
):
    def __init__(
        self,
        guild: discord.Guild,
        record: dict | None,
        delivery_count: int,
    ) -> None:
        super().__init__(
            timeout=120
        )

        record = record or {}

        text = config_text(
            guild,
            record,
        )

        text += (
            "\n"
            "\n"
            f"**Tracked deliveries:** "
            f"{delivery_count}"
        )

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    text
                )
            )
        )
