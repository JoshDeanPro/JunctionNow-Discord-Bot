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
            "sync_now": self.sync_now,
            "sync_interval": self.sync_interval,
            "retention": self.retention,
            "ban_server": self.ban_server,
            "unban_server": self.unban_server,
            "set_channel": self.set_channel,
            "photo_request": self.photo_request,
            "photo_requests": self.photo_requests,
            "withdraw_post": self.withdraw_post,
            "restore_post": self.restore_post,
            "broadcast": self.broadcast,
            "schedule_broadcast": self.schedule_broadcast,
            "withdraw_broadcast": self.withdraw_broadcast,
            "delete_server_data": self.delete_server_data,
            "delete_post_data": self.delete_post_data,
        }

        handler = handlers.get(action)

        if handler is None:
            raise ValueError(
                f"Unknown operator action: {action}"
            )

        await handler(payload)

    async def sync_now(self, payload: dict) -> None:
        await self.bot.sync_engine.sync_once(inspect_articles=True)

    async def sync_interval(self, payload: dict) -> None:
        seconds = int(payload["seconds"])
        schedule = str(payload.get("schedule", "posts"))

        if not 120 <= seconds <= 86400:
            raise ValueError("Post checks must be 2 minutes to 24 hours apart.")

        if schedule == "posts":
            self.bot.post_interval_seconds = seconds
        elif schedule == "updates":
            self.bot.post_update_interval_seconds = seconds
        else:
            raise ValueError("Unknown post schedule.")

        self.bot.background_sync.change_interval(
            seconds=min(
                self.bot.post_interval_seconds,
                self.bot.post_update_interval_seconds,
            )
        )

    async def retention(self, payload: dict) -> None:
        values = {
            "max_posts": (int(payload["max_posts"]), 100, 5000),
            "max_events": (int(payload["max_events"]), 100, 5000),
            "backup_count": (int(payload["backup_count"]), 1, 20),
        }

        for name, (value, minimum, maximum) in values.items():
            if not minimum <= value <= maximum:
                raise ValueError(f"Invalid retention value: {name}")

            setattr(self.bot.store, name, value)

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

            guild = state.setdefault(
                "guilds",
                {},
            ).get(guild_id)

            if guild:
                guild["enabled"] = False

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

    async def photo_requests(self, payload: dict) -> None:
        post_ids = list(dict.fromkeys(str(item) for item in payload.get("post_ids", [])))

        if not post_ids or len(post_ids) > 100:
            raise ValueError("Choose between 1 and 100 articles.")

        enabled = bool(payload.get("enabled"))

        for post_id in post_ids:
            await set_photo_request(self.bot, post_id, enabled)

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
        broadcast_id = str(payload.get("broadcast_id") or uuid.uuid4().hex[:12])
        deliveries = []

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
                message = await channel.send(
                    embed=embed,
                    allowed_mentions=(
                        discord.AllowedMentions.none()
                    ),
                )
                deliveries.append(
                    {
                        "guild_id": guild_id,
                        "channel_id": str(channel.id),
                        "message_id": str(message.id),
                    }
                )
            except discord.HTTPException:
                continue

        def save(data):
            broadcasts = data.setdefault("broadcasts", {})
            broadcasts[broadcast_id] = {
                "id": broadcast_id,
                "message": text,
                "sent_at": now(),
                "withdrawn": False,
                "status": "sent",
                "deliveries": deliveries,
            }

            if len(broadcasts) > 100:
                oldest = sorted(
                    broadcasts.values(),
                    key=lambda item: item.get("sent_at", ""),
                )[:-100]

                for item in oldest:
                    broadcasts.pop(item["id"], None)

        await self.bot.store.mutate(save)

    async def schedule_broadcast(self, payload: dict) -> None:
        text = str(payload.get("message", "")).strip()

        if not text or len(text) > 4000:
            raise ValueError("Broadcast message must be 1 to 4000 characters.")

        broadcast_id = uuid.uuid4().hex[:12]

        def save(state):
            state.setdefault("broadcasts", {})[broadcast_id] = {
                "id": broadcast_id,
                "message": text,
                "created_at": now(),
                "status": "scheduled",
                "withdrawn": False,
                "deliveries": [],
            }

        await self.bot.store.mutate(save)

    async def send_scheduled_broadcasts(self) -> None:
        state = await self.bot.store.snapshot()

        for broadcast in state.get("broadcasts", {}).values():
            if broadcast.get("status") == "scheduled" and not broadcast.get("withdrawn"):
                await self.broadcast(
                    {
                        "broadcast_id": broadcast["id"],
                        "message": broadcast["message"],
                    }
                )

    async def withdraw_broadcast(self, payload: dict) -> None:
        broadcast_id = str(payload["broadcast_id"])
        state = await self.bot.store.snapshot()
        broadcast = state.get("broadcasts", {}).get(broadcast_id)

        if not broadcast:
            raise ValueError("Broadcast was not found.")

        if broadcast.get("withdrawn"):
            return

        for delivery in broadcast.get("deliveries", []):
            guild = self.bot.get_guild(int(delivery["guild_id"]))
            channel = guild.get_channel(int(delivery["channel_id"])) if guild else None

            if not isinstance(channel, discord.TextChannel):
                continue

            try:
                message = await channel.fetch_message(int(delivery["message_id"]))
                await message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue

        def mark(data):
            record = data.setdefault("broadcasts", {}).get(broadcast_id)

            if record:
                record["withdrawn"] = True
                record["withdrawn_at"] = now()

        await self.bot.store.mutate(mark)

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
