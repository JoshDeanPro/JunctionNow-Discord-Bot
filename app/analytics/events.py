from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnalyticsEvent


async def record_event(
    session: AsyncSession,
    event_type: str,
    *,
    guild_id: int | None = None,
    post_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    session.add(
        AnalyticsEvent(
            event_type=event_type,
            guild_id=guild_id,
            post_id=post_id,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
    )
