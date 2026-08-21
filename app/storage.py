from __future__ import annotations

import asyncio
import copy
import fcntl
import json
import os
import shutil
import tempfile
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from app.config import get_settings

T = TypeVar("T")

SCHEMA_VERSION = 2


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utcnow(),
        "guilds": {},
        "posts": {},
        "deliveries": {},
        "analytics": {
            "counters": {},
            "events": [],
        },
    }


class JsonStateStore:
    def __init__(self) -> None:
        settings = get_settings()

        self.path = Path(settings.state_file)
        self.backup_dir = self.path.parent / "backups"
        self.max_posts = settings.state_max_posts
        self.max_events = settings.state_max_events
        self.backup_count = settings.state_backup_count

        self.lock = asyncio.Lock()
        self.process_lock_path = self.path.with_suffix(
            self.path.suffix + ".lock"
        )

    @contextmanager
    def _process_lock(self):
        self.process_lock_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.process_lock_path.open("a+") as handle:
            fcntl.flock(
                handle.fileno(),
                fcntl.LOCK_EX,
            )

            try:
                yield
            finally:
                fcntl.flock(
                    handle.fileno(),
                    fcntl.LOCK_UN,
                )

    async def initialize(self) -> None:
        async with self.lock:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self.backup_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            if not self.path.exists():
                self._write_sync(default_state())
                return

            state = self._read_sync()
            self._validate(state)

    def _validate(
        self,
        state: dict[str, Any],
    ) -> None:
        if not isinstance(state, dict):
            raise RuntimeError(
                "JSON state root must be an object"
            )

        version = state.get("schema_version")

        if version != SCHEMA_VERSION:
            raise RuntimeError(
                f"Unsupported state schema: {version!r}; "
                f"expected {SCHEMA_VERSION}"
            )

        for key in (
            "guilds",
            "posts",
            "deliveries",
            "analytics",
        ):
            if key not in state:
                raise RuntimeError(
                    f"JSON state missing required key: {key}"
                )

    def _read_sync(self) -> dict[str, Any]:
        try:
            data = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"JSON state is corrupt: {self.path}"
            ) from exc

        self._validate(data)

        return data

    def _maybe_backup_sync(self) -> None:
        if not self.path.exists():
            return

        backups = sorted(
            self.backup_dir.glob("state-*.json"),
            key=lambda item: item.stat().st_mtime,
        )

        should_backup = True

        if backups:
            age = (
                datetime.now(UTC).timestamp()
                - backups[-1].stat().st_mtime
            )

            should_backup = age >= 3600

        if not should_backup:
            return

        stamp = datetime.now(UTC).strftime(
            "%Y%m%dT%H%M%SZ"
        )

        target = (
            self.backup_dir
            / f"state-{stamp}.json"
        )

        shutil.copy2(
            self.path,
            target,
        )

        backups = sorted(
            self.backup_dir.glob("state-*.json"),
            key=lambda item: item.stat().st_mtime,
        )

        excess = max(
            0,
            len(backups) - self.backup_count,
        )

        for old in backups[:excess]:
            old.unlink(missing_ok=True)

    def _write_sync(
        self,
        state: dict[str, Any],
    ) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.backup_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._maybe_backup_sync()

        encoded = json.dumps(
            state,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n"

        fd, temp_name = tempfile.mkstemp(
            prefix=".state-",
            suffix=".tmp",
            dir=self.path.parent,
        )

        try:
            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(
                temp_name,
                self.path,
            )

        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    async def snapshot(
        self,
    ) -> dict[str, Any]:
        async with self.lock:
            with self._process_lock():
                if not self.path.exists():
                    self._write_sync(
                        default_state()
                    )

                return copy.deepcopy(
                    self._read_sync()
                )

    async def mutate(
        self,
        callback: Callable[
            [dict[str, Any]],
            T,
        ],
    ) -> T:
        async with self.lock:
            with self._process_lock():
                state = self._read_sync()

                result = callback(state)

                self._prune_posts(state)
                self._prune_events(state)

                self._write_sync(state)

                return copy.deepcopy(result)

    def _prune_events(
        self,
        state: dict[str, Any],
    ) -> None:
        events = (
            state
            .setdefault("analytics", {})
            .setdefault("events", [])
        )

        if len(events) > self.max_events:
            del events[
                : len(events) - self.max_events
            ]

    def _prune_posts(
        self,
        state: dict[str, Any],
    ) -> None:
        posts = state.setdefault(
            "posts",
            {},
        )

        if len(posts) <= self.max_posts:
            return

        ordered = sorted(
            posts.items(),
            key=lambda pair: pair[1].get(
                "first_seen_at",
                "",
            ),
        )

        remove_count = (
            len(posts) - self.max_posts
        )

        doomed = {
            post_id
            for post_id, _ in ordered[
                :remove_count
            ]
        }

        for post_id in doomed:
            posts.pop(
                post_id,
                None,
            )

        deliveries = state.setdefault(
            "deliveries",
            {},
        )

        for guild_deliveries in (
            deliveries.values()
        ):
            for post_id in doomed:
                guild_deliveries.pop(
                    post_id,
                    None,
                )

    def _record_event_sync(
        self,
        state: dict[str, Any],
        event_type: str,
        guild_id: int | str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        analytics = state.setdefault(
            "analytics",
            {},
        )

        counters = analytics.setdefault(
            "counters",
            {},
        )

        counters[event_type] = (
            int(counters.get(event_type, 0))
            + 1
        )

        events = analytics.setdefault(
            "events",
            [],
        )

        events.append(
            {
                "type": event_type,
                "guild_id": (
                    str(guild_id)
                    if guild_id is not None
                    else None
                ),
                "at": utcnow(),
                "metadata": metadata or {},
            }
        )

    async def record_event(
        self,
        event_type: str,
        *,
        guild_id: int | str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        def change(
            state: dict[str, Any],
        ) -> None:
            self._record_event_sync(
                state,
                event_type,
                guild_id,
                metadata,
            )

        await self.mutate(change)

    async def track_guild(
        self,
        guild,
        *,
        joined: bool = False,
    ) -> dict[str, Any]:
        guild_id = str(guild.id)

        def change(
            state: dict[str, Any],
        ) -> dict[str, Any]:
            guilds = state.setdefault(
                "guilds",
                {},
            )

            existing = guilds.get(
                guild_id,
                {},
            )

            now = utcnow()

            existing.setdefault(
                "joined_at",
                now,
            )

            existing.setdefault(
                "configured_at",
                None,
            )

            existing.setdefault(
                "channel_id",
                None,
            )

            existing.setdefault(
                "channel_created_by_bot",
                False,
            )

            existing.setdefault(
                "mention_role_ids",
                [],
            )

            existing.setdefault(
                "enabled",
                False,
            )

            existing.update(
                {
                    "guild_id": guild_id,
                    "guild_name": guild.name,
                    "member_count": (
                        guild.member_count
                        if guild.member_count
                        is not None
                        else None
                    ),
                    "last_seen_at": now,
                    "removed_at": None,
                }
            )

            guilds[guild_id] = existing

            if joined:
                self._record_event_sync(
                    state,
                    "guild_join",
                    guild_id,
                    {
                        "name": guild.name,
                        "member_count": (
                            guild.member_count
                        ),
                    },
                )

            return existing

        return await self.mutate(change)

    async def mark_guild_removed(
        self,
        guild_id: int,
    ) -> None:
        key = str(guild_id)

        def change(
            state: dict[str, Any],
        ) -> None:
            guild = (
                state
                .setdefault("guilds", {})
                .get(key)
            )

            if guild:
                guild["enabled"] = False
                guild["removed_at"] = utcnow()

            self._record_event_sync(
                state,
                "guild_remove",
                key,
            )

        await self.mutate(change)

    async def get_guild(
        self,
        guild_id: int,
    ) -> dict[str, Any] | None:
        state = await self.snapshot()

        guild = state.get(
            "guilds",
            {},
        ).get(str(guild_id))

        return copy.deepcopy(guild)

    async def configure_channel(
        self,
        guild,
        channel_id: int,
        user_id: int,
        *,
        created_by_bot: bool,
    ) -> dict[str, Any]:
        guild_id = str(guild.id)

        def change(
            state: dict[str, Any],
        ) -> dict[str, Any]:
            guilds = state.setdefault(
                "guilds",
                {},
            )

            record = guilds.setdefault(
                guild_id,
                {},
            )

            now = utcnow()

            record.setdefault(
                "joined_at",
                now,
            )

            if not record.get(
                "configured_at"
            ):
                record["configured_at"] = now

            record.update(
                {
                    "guild_id": guild_id,
                    "guild_name": guild.name,
                    "channel_id": str(
                        channel_id
                    ),
                    "channel_created_by_bot": (
                        created_by_bot
                    ),
                    "enabled": True,
                    "configured_by": str(
                        user_id
                    ),
                    "last_configured_at": now,
                    "last_seen_at": now,
                    "removed_at": None,
                }
            )

            record.setdefault(
                "mention_role_ids",
                [],
            )

            self._record_event_sync(
                state,
                "config_channel",
                guild_id,
                {
                    "channel_id": str(
                        channel_id
                    ),
                    "created_by_bot": (
                        created_by_bot
                    ),
                },
            )

            return record

        return await self.mutate(change)

    async def configure_roles(
        self,
        guild_id: int,
        role_ids: list[int],
        user_id: int,
    ) -> dict[str, Any]:
        key = str(guild_id)

        def change(
            state: dict[str, Any],
        ) -> dict[str, Any]:
            record = (
                state
                .setdefault("guilds", {})
                .setdefault(key, {})
            )

            record["mention_role_ids"] = [
                str(role_id)
                for role_id in role_ids
            ]

            record["configured_by"] = str(
                user_id
            )

            record["last_configured_at"] = (
                utcnow()
            )

            self._record_event_sync(
                state,
                "config_roles",
                key,
                {
                    "role_count": len(
                        role_ids
                    ),
                },
            )

            return record

        return await self.mutate(change)

    async def set_enabled(
        self,
        guild_id: int,
        enabled: bool,
        user_id: int,
    ) -> dict[str, Any]:
        key = str(guild_id)

        def change(
            state: dict[str, Any],
        ) -> dict[str, Any]:
            record = (
                state
                .setdefault("guilds", {})
                .setdefault(key, {})
            )

            record["enabled"] = enabled
            record["configured_by"] = str(
                user_id
            )

            record["last_configured_at"] = (
                utcnow()
            )

            self._record_event_sync(
                state,
                (
                    "config_enabled"
                    if enabled
                    else "config_disabled"
                ),
                key,
            )

            return record

        return await self.mutate(change)

    async def get_post(
        self,
        post_id: str,
    ) -> dict[str, Any] | None:
        state = await self.snapshot()

        post = state.get(
            "posts",
            {},
        ).get(post_id)

        return copy.deepcopy(post)

    async def upsert_post(
        self,
        post: dict[str, Any],
    ) -> dict[str, Any]:
        post_id = post["post_id"]

        def change(
            state: dict[str, Any],
        ) -> dict[str, Any]:
            posts = state.setdefault(
                "posts",
                {},
            )

            previous = posts.get(
                post_id
            )

            now = utcnow()

            record = dict(post)

            if previous is None:
                record["first_seen_at"] = now
                is_new = True
                changed = False
            else:
                record["first_seen_at"] = (
                    previous.get(
                        "first_seen_at",
                        now,
                    )
                )

                is_new = False
                changed = (
                    previous.get("source_hash")
                    != record.get(
                        "source_hash"
                    )
                )

            record["last_seen_at"] = now

            posts[post_id] = record

            return {
                "record": record,
                "is_new": is_new,
                "changed": changed,
            }

        return await self.mutate(change)

    async def get_delivery(
        self,
        guild_id: int | str,
        post_id: str,
    ) -> dict[str, Any] | None:
        state = await self.snapshot()

        delivery = (
            state
            .get("deliveries", {})
            .get(str(guild_id), {})
            .get(post_id)
        )

        return copy.deepcopy(delivery)

    async def save_delivery(
        self,
        guild_id: int | str,
        post_id: str,
        delivery: dict[str, Any],
        *,
        event_type: str,
    ) -> None:
        key = str(guild_id)

        def change(
            state: dict[str, Any],
        ) -> None:
            deliveries = (
                state
                .setdefault(
                    "deliveries",
                    {},
                )
                .setdefault(key, {})
            )

            deliveries[post_id] = dict(
                delivery
            )

            self._record_event_sync(
                state,
                event_type,
                key,
                {
                    "post_id": post_id,
                    "channel_id": delivery.get(
                        "channel_id"
                    ),
                    "message_id": delivery.get(
                        "message_id"
                    ),
                },
            )

        await self.mutate(change)

    async def mark_message_deleted(
        self,
        message_id: int,
    ) -> bool:
        target = str(message_id)

        def change(
            state: dict[str, Any],
        ) -> bool:
            deliveries = state.setdefault(
                "deliveries",
                {},
            )

            for guild_id, guild_items in (
                deliveries.items()
            ):
                for post_id, delivery in (
                    guild_items.items()
                ):
                    if str(
                        delivery.get(
                            "message_id"
                        )
                    ) != target:
                        continue

                    delivery["message_id"] = None
                    delivery["status"] = (
                        "message_deleted"
                    )

                    self._record_event_sync(
                        state,
                        "message_deleted",
                        guild_id,
                        {
                            "post_id": post_id,
                            "message_id": target,
                        },
                    )

                    return True

            return False

        return await self.mutate(change)
