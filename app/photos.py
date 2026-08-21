from __future__ import annotations

from datetime import UTC, datetime

import discord


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


async def find_delivery(
    bot,
    message_id: int,
) -> tuple[str, str, dict] | None:
    state = await bot.store.snapshot()
    target = str(message_id)

    for guild_id, deliveries in state.get(
        "deliveries",
        {},
    ).items():
        for post_id, delivery in deliveries.items():
            if str(
                delivery.get("message_id")
            ) == target:
                return guild_id, post_id, delivery

    return None


class DismissView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(
            timeout=300
        )

    @discord.ui.button(
        label="Dismiss",
        style=discord.ButtonStyle.secondary,
    )
    async def dismiss(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.edit_message(
            content="Dismissed.",
            view=None,
        )


class PhotoSubmitModal(discord.ui.Modal):
    def __init__(
        self,
        bot,
        post_id: str,
        source_guild_id: int,
        source_message_id: int,
    ) -> None:
        super().__init__(
            title="Submit Photos",
            timeout=300,
        )

        self.bot = bot
        self.post_id = post_id
        self.source_guild_id = source_guild_id
        self.source_message_id = source_message_id

        self.files = discord.ui.FileUpload(
            custom_id="jn:photo:files",
            min_values=1,
            max_values=5,
            required=True,
        )

        self.confirm = discord.ui.Checkbox(
            custom_id="jn:photo:confirm",
            default=False,
        )

        self.add_item(
            discord.ui.Label(
                text="Photos",
                description="Upload up to five photos.",
                component=self.files,
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Photo ownership",
                description=(
                    "Confirm these are your photos "
                    "and you can share them."
                ),
                component=self.confirm,
            )
        )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not self.confirm.value:
            await interaction.response.send_message(
                (
                    "You must confirm that these are "
                    "your photos before submitting."
                ),
                ephemeral=True,
                view=DismissView(),
            )
            return

        post = await self.bot.store.get_post(
            self.post_id
        )

        if not post:
            await interaction.response.send_message(
                "This article is no longer available.",
                ephemeral=True,
                view=DismissView(),
            )
            return

        channel = await self.bot.operator_channels.photos()

        if channel is None:
            await interaction.response.send_message(
                "Photo submissions are not available right now.",
                ephemeral=True,
                view=DismissView(),
            )
            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        files = []

        for attachment in self.files.values:
            files.append(
                await attachment.to_file()
            )

        source_guild = self.bot.get_guild(
            self.source_guild_id
        )

        embed = discord.Embed(
            title="Photo Submission",
            description=(
                f"**Article:** [{post.get('title', 'JunctionNow')}]"
                f"({post.get('url', '')})\n"
                f"**User:** {interaction.user.mention}\n"
                f"**User ID:** `{interaction.user.id}`\n"
                f"**Server:** "
                f"{source_guild.name if source_guild else self.source_guild_id}\n"
                f"**Source message:** `{self.source_message_id}`\n"
                "**Ownership confirmed:** Yes"
            ),
            timestamp=datetime.now(UTC),
        )

        embed.set_footer(
            text="JunctionNow Photo Submission"
        )

        await channel.send(
            embed=embed,
            files=files,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        await self.bot.store.record_event(
            "photo_submission",
            guild_id=self.source_guild_id,
            metadata={
                "post_id": self.post_id,
                "article_title": post.get("title", "JunctionNow"),
                "article_url": post.get("url", ""),
                "user_id": str(
                    interaction.user.id
                ),
                "user_display_name": interaction.user.display_name,
                "guild_name": source_guild.name if source_guild else None,
                "source_message_id": str(self.source_message_id),
                "file_count": len(files),
            },
        )

        await interaction.followup.send(
            (
                "Your photos were sent to JunctionNow.\n\n"
                "**Only you can see this.**"
            ),
            ephemeral=True,
            view=DismissView(),
        )


class SubmitPhotosButton(discord.ui.Button):
    def __init__(self, bot) -> None:
        super().__init__(
            label="Submit Photos",
            style=discord.ButtonStyle.primary,
            custom_id="jn:post:submit-photos",
        )

        self.bot = bot

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not interaction.message:
            return

        found = await find_delivery(
            self.bot,
            interaction.message.id,
        )

        if not found:
            await interaction.response.send_message(
                "This article is no longer available.",
                ephemeral=True,
                view=DismissView(),
            )
            return

        guild_id, post_id, _ = found

        post = await self.bot.store.get_post(
            post_id
        )

        if not post or not post.get(
            "photo_requested",
            False,
        ):
            await interaction.response.send_message(
                "Photo submissions are not open for this article.",
                ephemeral=True,
                view=DismissView(),
            )
            return

        await self.bot.store.record_event(
            "photo_button_click",
            guild_id=guild_id,
            metadata={"post_id": post_id},
        )

        await interaction.response.send_modal(
            PhotoSubmitModal(
                self.bot,
                post_id,
                int(guild_id),
                interaction.message.id,
            )
        )


class PhotoPostView(discord.ui.View):
    def __init__(self, bot) -> None:
        super().__init__(
            timeout=None
        )

        self.add_item(
            SubmitPhotosButton(bot)
        )


def photo_view(
    bot,
    requested: bool,
) -> discord.ui.View | None:
    if not requested:
        return None

    return PhotoPostView(bot)


async def set_photo_request(
    bot,
    post_id: str,
    enabled: bool,
) -> int:
    def change(state):
        post = (
            state
            .setdefault("posts", {})
            .get(post_id)
        )

        if post is None:
            return False

        post["photo_requested"] = enabled
        post["photo_request_changed_at"] = utcnow()

        return True

    changed = await bot.store.mutate(
        change
    )

    if not changed:
        return 0

    state = await bot.store.snapshot()

    edited = 0

    for guild_id, deliveries in state.get(
        "deliveries",
        {},
    ).items():
        delivery = deliveries.get(
            post_id
        )

        if not delivery:
            continue

        guild = bot.get_guild(
            int(guild_id)
        )

        if guild is None:
            continue

        channel_id = delivery.get(
            "channel_id"
        )

        message_id = delivery.get(
            "message_id"
        )

        if not channel_id or not message_id:
            continue

        channel = guild.get_channel(
            int(channel_id)
        )

        if not isinstance(
            channel,
            discord.TextChannel,
        ):
            continue

        try:
            message = await channel.fetch_message(
                int(message_id)
            )

            await message.edit(
                view=photo_view(
                    bot,
                    enabled,
                )
            )

            edited += 1

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
        ):
            continue

    return edited
