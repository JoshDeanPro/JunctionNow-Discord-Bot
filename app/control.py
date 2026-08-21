from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

import discord

from app.photos import set_photo_request

logger = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(UTC).isoformat()


async def enqueue(
    store,
    action: str,
    payload: dict | None = None,
) -> str:
    action_id = uuid.uuid4().hex[:12]

    def change(state):
        control = state.setdefault(
            "control",
            {},
        )

        queue = control.setdefault(
            "queue",
            [],
        )

        queue.append(
            {
                "id": action_id,
                "action": action,
                "payload": payload or {},
                "status": "pending",
                "created_at": now(),
            }
        )

        if len(queue) > 100:
            del queue[:-100]

    await store.mutate(change)

    return action_id


class ControlWorker:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def next_action(self) -> dict | None:
        def change(state):
            queue = (
                state.setdefault(
                    "control",
                    {},
                )
                .setdefault(
                    "queue",
                    [],
                )
            )

            for item in queue:
                if item.get("status") != "pending":
                    continue

                item["status"] = "running"
                item["started_at"] = now()

                return dict(item)

            return None

        return await self.bot.store.mutate(
            change
        )

    async def finish(
        self,
        action_id: str,
        *,
        error: str | None = None,
    ) -> None:
        def change(state):
            queue = (
                state.setdefault(
                    "control",
                    {},
                )
                .setdefault(
                    "queue",
                    [],
                )
            )

            for item in queue:
                if item.get("id") != action_id:
                    continue

                item["status"] = (
                    "failed"
                    if error
                    else "done"
                )

                item["finished_at"] = now()

                if error:
                    item["error"] = error

                break

        await self.bot.store.mutate(change)

    async def run_once(self) -> bool:
        item = await self.next_action()

        if not item:
            return False

        try:
            await self.execute(
                item["action"],
                item.get("payload", {}),
            )

            await self.finish(
                item["id"]
            )

        except Exception as exc:
            logger.exception(
                "Operator action failed: %s",
                item["action"],
            )

            await self.finish(
                item["id"],
                error=(
                    f"{type(exc).__name__}: {exc}"
                ),
            )

        return True

    async def execute(
        self,
        action: str,
        payload: dict,
    ) -> None:
        handlers = {
            "feed": self.feed,
            "ban_server": self.ban_server,
            "unban_server": self.unban_server,
            "set_channel": self.set_channel,
            "photo_request": self.photo_request,
            "withdraw_post": self.withdraw_post,
            "restore_post": self.restore_post,
            "broadcast": self.broadcast,
            "delete_server_data": self.delete_server_data,
            "delete_post_data": self.delete_post_data,
        }

        handler = handlers.get(action)

        if handler is None:
            raise ValueError(
                f"Unknown operator action: {action}"
            )

        await handler(payload)

    async def feed(self, payload: dict) -> None:
        enabled = bool(
            payload.get("enabled")
        )

        def change(state):
            state.setdefault(
                "system",
                {},
            )["feed_enabled"] = enabled

        await self.bot.store.mutate(change)

    async def ban_server(
        self,
        payload: dict,
    ) -> None:
        guild_id = str(
            int(payload["guild_id"])
        )

        def change(state):
            bans = state.setdefault(
                "banned_guilds",
                {},
            )

            bans[guild_id] = {
                "banned_at": now(),
                "reason": str(
                    payload.get(
                        "reason",
                        "",
                    )
                )[:300],
            }

        await self.bot.store.mutate(change)

        guild = self.bot.get_guild(
            int(guild_id)
        )

        if guild:
            await guild.leave()

    async def unban_server(
        self,
        payload: dict,
    ) -> None:
        guild_id = str(
            int(payload["guild_id"])
        )

        def change(state):
            state.setdefault(
                "banned_guilds",
                {},
            ).pop(
                guild_id,
                None,
            )

        await self.bot.store.mutate(change)

    async def set_channel(
        self,
        payload: dict,
    ) -> None:
        guild_id = int(
            payload["guild_id"]
        )

        channel_id = int(
            payload["channel_id"]
        )

        guild = self.bot.get_guild(
            guild_id
        )

        if guild is None:
            raise ValueError(
                "Server is not installed."
            )

        channel = guild.get_channel(
            channel_id
        )

        if not isinstance(
            channel,
            discord.TextChannel,
        ):
            raise ValueError(
                "Channel is not a text channel."
            )

        member = guild.me

        if member is None:
            raise ValueError(
                "Bot member was not found."
            )

        permissions = channel.permissions_for(
            member
        )

        if not (
            permissions.view_channel
            and permissions.send_messages
            and permissions.embed_links
        ):
            raise ValueError(
                "Bot cannot post in that channel."
            )

        def change(state):
            record = (
                state.setdefault(
                    "guilds",
                    {},
                )
                .setdefault(
                    str(guild_id),
                    {},
                )
            )

            record["channel_id"] = str(
                channel_id
            )

            record["enabled"] = True
            record["last_configured_at"] = now()

        await self.bot.store.mutate(change)

    async def photo_request(
        self,
        payload: dict,
    ) -> None:
        await set_photo_request(
            self.bot,
            str(payload["post_id"]),
            bool(payload["enabled"]),
        )

    async def withdraw_post(
        self,
        payload: dict,
    ) -> None:
        post_id = str(
            payload["post_id"]
        )

        state = await self.bot.store.snapshot()

        for guild_id, deliveries in (
            state.get(
                "deliveries",
                {},
            ).items()
        ):
            delivery = deliveries.get(
                post_id
            )

            if not delivery:
                continue

            guild = self.bot.get_guild(
                int(guild_id)
            )

            if guild is None:
                continue

            channel = guild.get_channel(
                int(
                    delivery["channel_id"]
                )
            )

            if not isinstance(
                channel,
                discord.TextChannel,
            ):
                continue

            message_id = delivery.get(
                "message_id"
            )

            if message_id:
                try:
                    message = (
                        await channel.fetch_message(
                            int(message_id)
                        )
                    )

                    await message.delete()

                except discord.NotFound:
                    pass

        def change(data):
            post = (
                data.setdefault(
                    "posts",
                    {},
                )
                .get(post_id)
            )

            if post:
                post["withdrawn"] = True
                post["withdrawn_at"] = now()

            for deliveries in (
                data.setdefault(
                    "deliveries",
                    {},
                ).values()
            ):
                delivery = deliveries.get(
                    post_id
                )

                if delivery:
                    delivery["message_id"] = None
                    delivery["status"] = "withdrawn"

        await self.bot.store.mutate(change)

    async def restore_post(
        self,
        payload: dict,
    ) -> None:
        post_id = str(
            payload["post_id"]
        )

        def change(state):
            post = (
                state.setdefault(
                    "posts",
                    {},
                )
                .get(post_id)
            )

            if post:
                post["withdrawn"] = False
                post["restored_at"] = now()

        await self.bot.store.mutate(change)

    async def broadcast(
        self,
        payload: dict,
    ) -> None:
        text = str(
            payload.get("message", "")
        ).strip()

        if not text:
            raise ValueError(
                "Broadcast message is empty."
            )

        if len(text) > 4000:
            raise ValueError(
                "Broadcast message is too long."
            )

        state = await self.bot.store.snapshot()

        embed = discord.Embed(
            description=text,
            title="JunctionNow",
        )

        for guild_id, config in (
            state.get(
                "guilds",
                {},
            ).items()
        ):
            if not (
                config.get("enabled")
                and config.get("channel_id")
            ):
                continue

            guild = self.bot.get_guild(
                int(guild_id)
            )

            if guild is None:
                continue

            channel = guild.get_channel(
                int(
                    config["channel_id"]
                )
            )

            if not isinstance(
                channel,
                discord.TextChannel,
            ):
                continue

            try:
                await channel.send(
                    embed=embed,
                    allowed_mentions=(
                        discord.AllowedMentions.none()
                    ),
                )
            except discord.HTTPException:
                continue

    async def delete_server_data(
        self,
        payload: dict,
    ) -> None:
        guild_id = str(
            int(payload["guild_id"])
        )

        def change(state):
            state.setdefault(
                "guilds",
                {},
            ).pop(
                guild_id,
                None,
            )

            state.setdefault(
                "deliveries",
                {},
            ).pop(
                guild_id,
                None,
            )

        await self.bot.store.mutate(change)

    async def delete_post_data(
        self,
        payload: dict,
    ) -> None:
        post_id = str(
            payload["post_id"]
        )

        def change(state):
            post = (
                state.setdefault(
                    "posts",
                    {},
                )
                .get(post_id)
            )

            if (
                post
                and not post.get(
                    "withdrawn"
                )
            ):
                raise ValueError(
                    "Withdraw the post before deleting its data."
                )

            state.setdefault(
                "posts",
                {},
            ).pop(
                post_id,
                None,
            )

            for deliveries in (
                state.setdefault(
                    "deliveries",
                    {},
                ).values()
            ):
                deliveries.pop(
                    post_id,
                    None,
                )

        await self.bot.store.mutate(change)


async def control_loop(
    worker: ControlWorker,
) -> None:
    while True:
        handled = await worker.run_once()

        if not handled:
            await asyncio.sleep(1)
