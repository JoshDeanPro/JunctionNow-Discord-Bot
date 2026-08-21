#!/usr/bin/env python3

import asyncio

from app.storage import JsonStateStore


async def main() -> None:
    store = JsonStateStore()

    await store.initialize()

    state = await store.snapshot()

    guilds = state.get(
        "guilds",
        {},
    )

    posts = state.get(
        "posts",
        {},
    )

    deliveries = state.get(
        "deliveries",
        {},
    )

    delivery_count = sum(
        len(items)
        for items in deliveries.values()
    )

    counters = (
        state
        .get("analytics", {})
        .get("counters", {})
    )

    print(
        f"Schema:        "
        f"{state.get('schema_version')}"
    )

    print(
        f"Guilds:        "
        f"{len(guilds)}"
    )

    print(
        f"Posts:         "
        f"{len(posts)}"
    )

    print(
        f"Deliveries:    "
        f"{delivery_count}"
    )

    print(
        f"Events:        "
        f"{len(state.get('analytics', {}).get('events', []))}"
    )

    print(
        f"Counters:      "
        f"{counters}"
    )


if __name__ == "__main__":
    asyncio.run(main())
