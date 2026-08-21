from __future__ import annotations

import logging
from datetime import UTC, datetime

import discord

from app.config import get_settings
from app.photos import DismissView, set_photo_request

logger = logging.getLogger(__name__)


class ManagementManager:
    def __init__(self, bot) -> None:
        self.bot = bot
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.management_guild_id
            and self.settings.management_channel_id
            and self.settings.management_operator_ids
        )

    def is_operator(
        self,
        user_id: int,
    ) -> bool:
        return (
            user_id
            in self.settings.management_operator_ids
        )

    async def allowed(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        return bool(
            self.enabled
            and interaction.guild_id
            == self.settings.management_guild_id
            and interaction.channel_id
            == self.settings.management_channel_id
            and self.is_operator(
                interaction.user.id
            )
        )

    async def management_guild(
        self,
    ) -> discord.Guild | None:
        if not self.settings.management_guild_id:
            return None

        return self.bot.get_guild(
            self.settings.management_guild_id
        )

    async def dashboard_channel(
        self,
    ) -> discord.TextChannel | None:
        channel = self.bot.get_channel(
            self.settings.management_channel_id
        )

        if isinstance(
            channel,
            discord.TextChannel,
        ):
            return channel

        try:
            channel = await self.bot.fetch_channel(
                self.settings.management_channel_id
            )
        except discord.HTTPException:
            return None

        return (
            channel
            if isinstance(
                channel,
                discord.TextChannel,
            )
            else None
        )

    async def ensure_private_channels(
        self,
    ) -> None:
        guild = await self.management_guild()

        if guild is None:
            return

        state = await self.bot.store.snapshot()

        saved = (
            state
            .get("management", {})
            .get("channels", {})
        )

        needs = {
            "photo_submissions": "jn-photo-submissions",
            "service_log": "jn-service-log",
        }

        created = dict(saved)

        for key, name in needs.items():
            channel_id = saved.get(key)

            if channel_id:
                channel = guild.get_channel(
                    int(channel_id)
                )

                if channel:
                    continue

            existing = discord.utils.get(
                guild.text_channels,
                name=name,
            )

            if existing:
                created[key] = str(
                    existing.id
                )
                continue

            member = guild.me

            if (
                member is None
                or not member.guild_permissions
                .manage_channels
            ):
                continue

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=False
                ),
                member: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                ),
            }

            for operator_id in (
                self.settings
                .management_operator_ids
            ):
                operator = guild.get_member(
                    operator_id
                )

                if operator:
                    overwrites[
                        operator
                    ] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        attach_files=True,
                    )

            channel = await guild.create_text_channel(
                name,
                overwrites=overwrites,
                reason="JunctionNow private management",
            )

            created[key] = str(
                channel.id
            )

        def change(data):
            management = data.setdefault(
                "management",
                {},
            )

            management["channels"] = created

        await self.bot.store.mutate(
            change
        )

    async def _saved_channel(
        self,
        key: str,
    ) -> discord.TextChannel | None:
        state = await self.bot.store.snapshot()

        raw = (
            state
            .get("management", {})
            .get("channels", {})
            .get(key)
        )

        if not raw:
            return None

        channel = self.bot.get_channel(
            int(raw)
        )

        return (
            channel
            if isinstance(
                channel,
                discord.TextChannel,
            )
            else None
        )

    async def photo_submission_channel(
        self,
    ) -> discord.TextChannel | None:
        return await self._saved_channel(
            "photo_submissions"
        )

    async def service_log_channel(
        self,
    ) -> discord.TextChannel | None:
        return await self._saved_channel(
            "service_log"
        )

    async def log(
        self,
        title: str,
        text: str,
        *,
        warning: bool = False,
    ) -> None:
        channel = await self.service_log_channel()

        if channel is None:
            return

        embed = discord.Embed(
            title=title,
            description=text,
            timestamp=datetime.now(UTC),
            color=(
                discord.Color.orange()
                if warning
                else discord.Color.blurple()
            ),
        )

        await channel.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def feed_enabled(
        self,
    ) -> bool:
        state = await self.bot.store.snapshot()

        return bool(
            state.get(
                "system",
                {},
            ).get(
                "feed_enabled",
                True,
            )
        )

    async def set_feed_enabled(
        self,
        enabled: bool,
    ) -> None:
        def change(state):
            system = state.setdefault(
                "system",
                {},
            )

            system["feed_enabled"] = enabled

        await self.bot.store.mutate(
            change
        )

    async def panel_message_id(
        self,
    ) -> int | None:
        state = await self.bot.store.snapshot()

        value = (
            state
            .get("management", {})
            .get("panel_message_id")
        )

        return int(value) if value else None

    async def save_panel_message_id(
        self,
        message_id: int | None,
    ) -> None:
        def change(state):
            management = state.setdefault(
                "management",
                {},
            )

            management[
                "panel_message_id"
            ] = (
                str(message_id)
                if message_id
                else None
            )

        await self.bot.store.mutate(
            change
        )

    async def panel_text(
        self,
    ) -> str:
        state = await self.bot.store.snapshot()

        guilds = state.get(
            "guilds",
            {},
        )

        configured = sum(
            1
            for item in guilds.values()
            if item.get("channel_id")
        )

        requested = sum(
            1
            for post in state.get(
                "posts",
                {},
            ).values()
            if post.get("photo_requested")
        )

        return "\n".join(
            [
                "# JunctionNow Management",
                "",
                (
                    "**Feed:** Running"
                    if await self.feed_enabled()
                    else "**Feed:** Paused"
                ),
                f"**Servers:** {len(guilds)}",
                f"**Configured:** {configured}",
                (
                    "**Photo requests:** "
                    f"{requested}"
                ),
                (
                    "**Last sync:** "
                    f"{self.bot.sync_engine.last_sync_finished_at or 'Not yet'}"
                ),
                "",
                "Private operator controls.",
            ]
        )

    async def ensure_panel(
        self,
    ) -> None:
        if not self.enabled:
            return

        await self.ensure_private_channels()

        channel = await self.dashboard_channel()

        if channel is None:
            return

        view = ManagementView(
            self,
            await self.panel_text(),
        )

        message_id = (
            await self.panel_message_id()
        )

        if message_id:
            try:
                message = await channel.fetch_message(
                    message_id
                )

                await message.edit(
                    view=view
                )
                return

            except discord.NotFound:
                pass

        message = await channel.send(
            view=view
        )

        await self.save_panel_message_id(
            message.id
        )

    async def access_link(
        self,
        guild_id: int,
    ) -> str | None:
        guild = self.bot.get_guild(
            guild_id
        )

        if guild is None:
            return None

        member = guild.me

        if member is None:
            return None

        for channel in guild.text_channels:
            permissions = channel.permissions_for(
                member
            )

            if not (
                permissions.view_channel
                and permissions.create_instant_invite
            ):
                continue

            try:
                invite = await channel.create_invite(
                    max_age=900,
                    max_uses=1,
                    unique=True,
                    reason=(
                        "JunctionNow operator access"
                    ),
                )

                return invite.url

            except discord.HTTPException:
                continue

        return None


class ManagementButton(discord.ui.Button):
    def __init__(
        self,
        manager: ManagementManager,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.manager = manager

    async def check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if await self.manager.allowed(
            interaction
        ):
            return True

        await interaction.response.send_message(
            (
                "You do not have access to "
                "JunctionNow management."
            ),
            ephemeral=True,
        )

        return False


class SyncButton(ManagementButton):
    def __init__(self, manager) -> None:
        super().__init__(
            manager,
            label="Sync Now",
            custom_id="jn:mgmt:sync",
            style=discord.ButtonStyle.primary,
        )

    async def callback(
        self,
        interaction,
    ) -> None:
        if not await self.check(interaction):
            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        result = await (
            self.manager.bot
            .sync_engine.sync_once()
        )

        await self.manager.ensure_panel()

        await interaction.followup.send(
            (
                f"Checked {result.get('posts', 0)} posts.\n\n"
                "**Only you can see this.**"
            ),
            ephemeral=True,
            view=DismissView(),
        )


class ToggleButton(ManagementButton):
    def __init__(self, manager) -> None:
        super().__init__(
            manager,
            label="Pause / Resume",
            custom_id="jn:mgmt:toggle",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(
        self,
        interaction,
    ) -> None:
        if not await self.check(interaction):
            return

        current = await self.manager.feed_enabled()

        await self.manager.set_feed_enabled(
            not current
        )

        await interaction.response.defer(
            ephemeral=True
        )

        await self.manager.ensure_panel()

        word = (
            "resumed"
            if not current
            else "paused"
        )

        await self.manager.log(
            "Feed changed",
            f"Automatic feed delivery was {word}.",
        )

        await interaction.followup.send(
            (
                f"Feed {word}.\n\n"
                "**Only you can see this.**"
            ),
            ephemeral=True,
            view=DismissView(),
        )


class ServersButton(ManagementButton):
    def __init__(self, manager) -> None:
        super().__init__(
            manager,
            label="Servers",
            custom_id="jn:mgmt:servers",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(
        self,
        interaction,
    ) -> None:
        if not await self.check(interaction):
            return

        guilds = [
            guild
            for guild in self.manager.bot.guilds
            if guild.id
            != self.manager.settings.management_guild_id
        ]

        if not guilds:
            await interaction.response.send_message(
                (
                    "No customer servers are installed.\n\n"
                    "**Only you can see this.**"
                ),
                ephemeral=True,
                view=DismissView(),
            )
            return

        await interaction.response.send_message(
            (
                "Choose a server.\n\n"
                "**Only you can see this.**"
            ),
            ephemeral=True,
            view=ServerPickerView(
                self.manager,
                guilds,
            ),
        )


class PhotosButton(ManagementButton):
    def __init__(self, manager) -> None:
        super().__init__(
            manager,
            label="Request Photos",
            custom_id="jn:mgmt:photos",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(
        self,
        interaction,
    ) -> None:
        if not await self.check(interaction):
            return

        state = await self.manager.bot.store.snapshot()

        posts = list(
            state.get(
                "posts",
                {},
            ).values()
        )

        posts.sort(
            key=lambda item: item.get(
                "published_at",
                "",
            ),
            reverse=True,
        )

        posts = posts[:25]

        if not posts:
            await interaction.response.send_message(
                "No posts are tracked yet.",
                ephemeral=True,
                view=DismissView(),
            )
            return

        await interaction.response.send_message(
            (
                "Choose an article. Selecting it "
                "turns photo requests on or off.\n\n"
                "**Only you can see this.**"
            ),
            ephemeral=True,
            view=PhotoPickerView(
                self.manager,
                posts,
            ),
        )


class ServerSelect(discord.ui.Select):
    def __init__(
        self,
        manager,
        guilds,
    ) -> None:
        self.manager = manager

        options = [
            discord.SelectOption(
                label=guild.name[:100],
                value=str(guild.id),
                description=(
                    f"{guild.member_count or 0} members"
                )[:100],
            )
            for guild in guilds[:25]
        ]

        super().__init__(
            placeholder="Choose server",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(
        self,
        interaction,
    ) -> None:
        guild_id = int(
            self.values[0]
        )

        guild = self.manager.bot.get_guild(
            guild_id
        )

        if guild is None:
            await interaction.response.edit_message(
                content="Server is no longer available.",
                view=DismissView(),
            )
            return

        await interaction.response.edit_message(
            content=(
                f"**{guild.name}**\n\n"
                "Create a short-lived one-use access link "
                "only if you need to enter the server.\n\n"
                "**Only you can see this.**"
            ),
            view=ServerActionsView(
                self.manager,
                guild_id,
            ),
        )


class AccessLinkButton(discord.ui.Button):
    def __init__(
        self,
        manager,
        guild_id,
    ) -> None:
        super().__init__(
            label="Access Link",
            style=discord.ButtonStyle.primary,
        )

        self.manager = manager
        self.guild_id = guild_id

    async def callback(
        self,
        interaction,
    ) -> None:
        if not self.manager.is_operator(
            interaction.user.id
        ):
            return

        link = await self.manager.access_link(
            self.guild_id
        )

        text = (
            f"{link}\n\n"
            "Expires in 15 minutes and can be used once.\n\n"
            "**Only you can see this.**"
            if link
            else (
                "The bot cannot create an invite "
                "for this server.\n\n"
                "**Only you can see this.**"
            )
        )

        await interaction.response.edit_message(
            content=text,
            view=DismissView(),
        )


class ServerActionsView(discord.ui.View):
    def __init__(
        self,
        manager,
        guild_id,
    ) -> None:
        super().__init__(
            timeout=300
        )

        self.add_item(
            AccessLinkButton(
                manager,
                guild_id,
            )
        )

        self.add_item(
            DismissView().children[0]
        )


class ServerPickerView(discord.ui.View):
    def __init__(
        self,
        manager,
        guilds,
    ) -> None:
        super().__init__(
            timeout=300
        )

        self.add_item(
            ServerSelect(
                manager,
                guilds,
            )
        )


class PhotoSelect(discord.ui.Select):
    def __init__(
        self,
        manager,
        posts,
    ) -> None:
        self.manager = manager

        options = []

        for post in posts:
            enabled = bool(
                post.get(
                    "photo_requested"
                )
            )

            options.append(
                discord.SelectOption(
                    label=(
                        post.get(
                            "title",
                            "JunctionNow",
                        )[:95]
                    ),
                    value=post["post_id"],
                    description=(
                        "Photo request ON"
                        if enabled
                        else "Photo request off"
                    ),
                )
            )

        super().__init__(
            placeholder="Choose article",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(
        self,
        interaction,
    ) -> None:
        post_id = self.values[0]

        post = await (
            self.manager.bot.store
            .get_post(post_id)
        )

        if not post:
            await interaction.response.edit_message(
                content="Article not found.",
                view=DismissView(),
            )
            return

        enabled = not bool(
            post.get(
                "photo_requested"
            )
        )

        count = await set_photo_request(
            self.manager.bot,
            post_id,
            enabled,
        )

        await self.manager.log(
            "Photo request changed",
            (
                f"**{post.get('title', 'JunctionNow')}**\n"
                f"Request: {'On' if enabled else 'Off'}\n"
                f"Messages updated: {count}"
            ),
        )

        await self.manager.ensure_panel()

        await interaction.response.edit_message(
            content=(
                f"Photo request is now "
                f"**{'ON' if enabled else 'OFF'}** "
                f"for **{post.get('title', 'JunctionNow')}**.\n"
                f"Updated {count} Discord message(s).\n\n"
                "**Only you can see this.**"
            ),
            view=DismissView(),
        )


class PhotoPickerView(discord.ui.View):
    def __init__(
        self,
        manager,
        posts,
    ) -> None:
        super().__init__(
            timeout=300
        )

        self.add_item(
            PhotoSelect(
                manager,
                posts,
            )
        )


class ManagementView(discord.ui.LayoutView):
    def __init__(
        self,
        manager,
        text="# JunctionNow Management",
    ) -> None:
        super().__init__(
            timeout=None
        )

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    text
                ),
                discord.ui.Separator(),
                discord.ui.ActionRow(
                    SyncButton(manager),
                    ToggleButton(manager),
                    ServersButton(manager),
                    PhotosButton(manager),
                ),
            )
        )
