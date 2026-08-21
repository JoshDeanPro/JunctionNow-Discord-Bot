#!/usr/bin/env python3

import asyncio

from sqlalchemy import func, select

from app.db.models import (
    Delivery,
    Guild,
    SourcePost,
    Subscription,
)
from app.db.session import SessionLocal, init_database


async def main() -> None:
    await init_database()

    async with SessionLocal() as session:
        guilds = await session.scalar(
            select(func.count()).select_from(Guild)
        )

        subscriptions = await session.scalar(
            select(func.count()).select_from(Subscription)
        )

        posts = await session.scalar(
            select(func.count()).select_from(SourcePost)
        )

        deliveries = await session.scalar(
            select(func.count()).select_from(Delivery)
        )

    print(f"Guilds:        {guilds}")
    print(f"Subscriptions: {subscriptions}")
    print(f"Posts:         {posts}")
    print(f"Deliveries:    {deliveries}")


if __name__ == "__main__":
    asyncio.run(main())
