from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx
from selectolax.parser import HTMLParser

from app.config import get_settings
from app.sync.types import FeedPost

logger = logging.getLogger(__name__)


def clean_html(value: str | None) -> str:
    if not value:
        return ""

    tree = HTMLParser(value)

    for node in tree.css("script, style"):
        node.decompose()

    text = tree.text(separator=" ", strip=True)

    return " ".join(text.split())


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        candidate = value.strip()

        try:
            dt = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = parsedate_to_datetime(candidate)
            except (TypeError, ValueError):
                return None
    else:
        return None

    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)

    return dt


def stable_id(*parts: str) -> str:
    material = "|".join(
        part.strip()
        for part in parts
        if part and part.strip()
    )

    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:40]


def json_posts(payload: Any) -> list[FeedPost]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = (
            payload.get("posts")
            or payload.get("items")
            or payload.get("results")
            or payload.get("data")
            or []
        )

        if isinstance(records, dict):
            records = records.get("posts") or records.get("items") or []
    else:
        records = []

    posts: list[FeedPost] = []

    for item in records:
        if not isinstance(item, dict):
            continue

        title = str(
            item.get("title")
            or item.get("name")
            or ""
        ).strip()

        body = clean_html(
            str(
                item.get("body")
                or item.get("content")
                or item.get("description")
                or item.get("summary")
                or ""
            )
        )

        url = str(
            item.get("url")
            or item.get("link")
            or item.get("permalink")
            or ""
        ).strip()

        raw_id = (
            item.get("id")
            or item.get("post_id")
            or item.get("guid")
            or item.get("uuid")
        )

        post_id = (
            str(raw_id).strip()
            if raw_id
            else stable_id(url, title)
        )

        if not post_id:
            continue

        try:
            revision = int(
                item.get("revision")
                or item.get("version")
                or 1
            )
        except (TypeError, ValueError):
            revision = 1

        image_url = (
            item.get("image")
            or item.get("image_url")
            or item.get("thumbnail")
            or item.get("featured_image")
        )

        posts.append(
            FeedPost(
                post_id=post_id,
                title=title,
                body=body,
                url=url,
                image_url=str(image_url).strip() if image_url else None,
                status=str(
                    item.get("status")
                    or "published"
                ).strip().lower(),
                revision=max(revision, 1),
                published_at=parse_datetime(
                    item.get("published_at")
                    or item.get("published")
                    or item.get("date")
                ),
                updated_at=parse_datetime(
                    item.get("updated_at")
                    or item.get("updated")
                    or item.get("modified_at")
                ),
            )
        )

    return posts


def rss_posts(raw: bytes) -> list[FeedPost]:
    parsed = feedparser.parse(raw)
    posts: list[FeedPost] = []

    for entry in parsed.entries:
        title = str(entry.get("title") or "").strip()
        url = str(entry.get("link") or "").strip()
        guid = str(
            entry.get("id")
            or entry.get("guid")
            or ""
        ).strip()

        content = entry.get("content") or []

        if content and isinstance(content[0], dict):
            body_source = content[0].get("value") or ""
        else:
            body_source = (
                entry.get("summary")
                or entry.get("description")
                or ""
            )

        body = clean_html(str(body_source))

        image_url = None

        media_content = entry.get("media_content") or []
        if media_content and isinstance(media_content[0], dict):
            image_url = media_content[0].get("url")

        media_thumbnail = entry.get("media_thumbnail") or []
        if (
            not image_url
            and media_thumbnail
            and isinstance(media_thumbnail[0], dict)
        ):
            image_url = media_thumbnail[0].get("url")

        if not image_url:
            for enclosure in entry.get("enclosures") or []:
                href = enclosure.get("href")
                content_type = str(enclosure.get("type") or "")

                if href and content_type.startswith("image/"):
                    image_url = href
                    break

        posts.append(
            FeedPost(
                post_id=guid or stable_id(url, title),
                title=title,
                body=body,
                url=url,
                image_url=str(image_url) if image_url else None,
                status="published",
                revision=1,
                published_at=parse_datetime(
                    entry.get("published")
                    or entry.get("created")
                ),
                updated_at=parse_datetime(entry.get("updated")),
            )
        )

    return posts


class JunctionNowFeedClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def fetch(self) -> list[FeedPost]:
        url = self.settings.junctionnow_feed_url.strip()

        if not url:
            logger.warning(
                "JUNCTIONNOW_FEED_URL is not configured; sync skipped."
            )
            return []

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                self.settings.junctionnow_request_timeout
            ),
            follow_redirects=True,
            headers={
                "User-Agent": "JunctionNowDiscordBot/0.1",
                "Accept": (
                    "application/json, application/rss+xml, "
                    "application/atom+xml, text/xml, */*"
                ),
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        content_type = response.headers.get(
            "content-type",
            "",
        ).lower()

        mode = self.settings.source_mode

        if mode == "json":
            return json_posts(response.json())

        if mode == "rss":
            return rss_posts(response.content)

        if "json" in content_type:
            return json_posts(response.json())

        raw = response.content.lstrip()

        if raw.startswith((b"{", b"[")):
            try:
                return json_posts(json.loads(response.text))
            except json.JSONDecodeError:
                pass

        return rss_posts(response.content)
