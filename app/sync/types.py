from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class FeedPost:
    post_id: str
    title: str
    body: str
    url: str
    image_url: str | None
    status: str
    revision: int
    published_at: datetime | None
    updated_at: datetime | None
