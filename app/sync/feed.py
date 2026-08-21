from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

import feedparser
import httpx
from selectolax.parser import HTMLParser

from app.config import get_settings
from app.sync.types import FeedPost

logger = logging.getLogger(__name__)

TRACKING_KEYS = {
    "fbclid",
    "gclid",
}


def hash_payload(
    payload: dict,
) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def canonicalize_url(
    url: str,
) -> str:
    url = (url or "").strip()

    if not url:
        return ""

    parts = urlsplit(url)

    query = []

    for key, value in parse_qsl(
        parts.query,
        keep_blank_values=True,
    ):
        lowered = key.lower()

        if lowered.startswith(
            "utm_"
        ):
            continue

        if lowered in TRACKING_KEYS:
            continue

        query.append(
            (key, value)
        )

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path or "/",
            urlencode(
                query,
                doseq=True,
            ),
            "",
        )
    )


def clean_html(
    value: str | None,
) -> str:
    if not value:
        return ""

    tree = HTMLParser(value)

    for node in tree.css(
        "script, style"
    ):
        node.decompose()

    text = tree.text(
        separator=" ",
        strip=True,
    )

    return " ".join(
        text.split()
    )


def clean_title(value: str | None) -> str:
    title = clean_html(value)
    return re.sub(
        r"\s*[-|–—]\s*JunctionNow\.com\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()


def clean_description(
    value: str | None,
) -> str:
    description = clean_html(
        value
    )

    if not description:
        return ""

    if "the post" in (
        description.lower()
    ):
        description = re.sub(
            r"\s+the post.*$",
            "",
            description,
            flags=re.IGNORECASE,
        ).strip()

        description = re.sub(
            r"[.…\[\]]*\s*$",
            "",
            description,
        ).strip()

    sentences = [
        sentence.strip()
        for sentence in re.split(
            r"(?<=[.!?])\s+",
            description,
        )
        if sentence.strip()
    ]

    if len(sentences) > 4:
        description = " ".join(
            sentences[:4]
        )
    elif sentences:
        description = " ".join(
            sentences
        )

    if description:
        description = (
            description.rstrip(".")
            + "..."
        )

    if len(description) > 2000:
        description = (
            description[:1997].rstrip()
            + "..."
        )

    return description


def parse_datetime(
    value,
) -> datetime | None:
    if not value:
        return None

    if isinstance(
        value,
        datetime,
    ):
        parsed = value

    else:
        candidate = str(
            value
        ).strip()

        try:
            parsed = (
                datetime.fromisoformat(
                    candidate.replace(
                        "Z",
                        "+00:00",
                    )
                )
            )
        except ValueError:
            try:
                parsed = (
                    parsedate_to_datetime(
                        candidate
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                return None

    if parsed.tzinfo is not None:
        parsed = (
            parsed.astimezone(
                UTC
            )
            .replace(
                tzinfo=None
            )
        )

    return parsed


def metadata_content(
    tree: HTMLParser,
    selector: str,
) -> str:
    node = tree.css_first(
        selector
    )

    if not node:
        return ""

    return (
        node.attributes.get(
            "content",
            "",
        )
        .strip()
    )


def article_body(
    tree: HTMLParser,
) -> str:
    selectors = (
        '[itemprop="articleBody"]',
        "article .entry-content",
        ".entry-content",
        ".post-content",
        ".article-content",
    )

    for selector in selectors:
        node = tree.css_first(
            selector
        )

        if not node:
            continue

        text = node.text(
            separator=" ",
            strip=True,
        )

        cleaned = " ".join(
            text.split()
        )

        if cleaned:
            return cleaned[:50000]

    return ""


class JunctionNowFeedClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def inspect_article(
        self,
        client: httpx.AsyncClient,
        post: FeedPost,
    ) -> None:
        if not post.url:
            return

        try:
            response = await client.get(
                post.url,
                timeout=10,
            )

            response.raise_for_status()

        except httpx.HTTPError:
            logger.debug(
                "Article page fetch failed: %s",
                post.url,
                exc_info=True,
            )
            return

        tree = HTMLParser(
            response.text
        )

        og_title = metadata_content(
            tree,
            'meta[property="og:title"]',
        )

        og_description = (
            metadata_content(
                tree,
                'meta[property="og:description"]',
            )
            or metadata_content(
                tree,
                'meta[name="description"]',
            )
        )

        image_url = (
            metadata_content(
                tree,
                'meta[property="og:image"]',
            )
            or metadata_content(
                tree,
                'meta[name="twitter:image"]',
            )
        )

        body = article_body(
            tree
        )

        page_description = clean_description(
            og_description or body
        )

        if og_title:
            post.title = clean_title(og_title)

        if page_description:
            post.body = page_description

        if image_url:
            post.image_url = image_url

        post.page_hash = hash_payload(
            {
                "og_title": og_title,
                "og_description": (
                    og_description
                ),
                "image_url": (
                    image_url
                ),
                "article_body": body,
            }
        )

    async def fetch(
        self,
    ) -> list[FeedPost]:
        url = (
            self.settings
            .junctionnow_feed_url
            .strip()
        )

        if not url:
            raise RuntimeError(
                "JUNCTIONNOW_FEED_URL "
                "is not configured"
            )

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                self.settings
                .junctionnow_request_timeout
            ),
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Macintosh; Intel Mac OS X) "
                    "AppleWebKit/537.36 "
                    "JunctionNowDiscordBot/0.2"
                ),
                "Accept": (
                    "application/rss+xml, "
                    "application/atom+xml, "
                    "text/xml, */*"
                ),
            },
        ) as client:
            response = await client.get(
                url
            )

            response.raise_for_status()

            feed = feedparser.parse(
                response.content
            )

            posts: list[
                FeedPost
            ] = []

            for entry in feed.entries[
                : self.settings
                .max_feed_items
            ]:
                title = clean_title(
                    str(entry.get("title", "Untitled post"))
                )

                url = canonicalize_url(
                    str(
                        entry.get(
                            "link",
                            "",
                        )
                    )
                )

                raw_id = str(
                    entry.get("id")
                    or entry.get(
                        "guid"
                    )
                    or ""
                ).strip()

                if raw_id.startswith(
                    ("http://", "https://")
                ):
                    post_id = (
                        canonicalize_url(
                            raw_id
                        )
                    )
                else:
                    post_id = (
                        raw_id
                        or url
                        or hashlib.sha256(
                            (
                                title
                                + "|"
                                + str(
                                    entry.get(
                                        "published",
                                        "",
                                    )
                                )
                            ).encode(
                                "utf-8"
                            )
                        ).hexdigest()
                    )

                description = (
                    entry.get(
                        "description"
                    )
                    or entry.get(
                        "summary"
                    )
                    or ""
                )

                body = clean_description(
                    str(description)
                )

                image_url = None

                media = (
                    entry.get(
                        "media_content"
                    )
                    or []
                )

                if (
                    media
                    and isinstance(
                        media[0],
                        dict,
                    )
                ):
                    image_url = (
                        media[0].get(
                            "url"
                        )
                    )

                thumbnails = (
                    entry.get(
                        "media_thumbnail"
                    )
                    or []
                )

                if (
                    not image_url
                    and thumbnails
                    and isinstance(
                        thumbnails[0],
                        dict,
                    )
                ):
                    image_url = (
                        thumbnails[0]
                        .get("url")
                    )

                published = parse_datetime(
                    entry.get(
                        "published"
                    )
                    or entry.get(
                        "created"
                    )
                )

                rss_hash = hash_payload(
                    {
                        "post_id": post_id,
                        "title": title,
                        "body": body,
                        "url": url,
                        "image_url": (
                            image_url
                            or ""
                        ),
                        "published": (
                            published.isoformat()
                            if published
                            else ""
                        ),
                    }
                )

                posts.append(
                    FeedPost(
                        post_id=post_id,
                        title=title,
                        body=body,
                        url=url,
                        image_url=(
                            str(image_url)
                            if image_url
                            else None
                        ),
                        published_at=(
                            published
                        ),
                        rss_hash=rss_hash,
                        page_hash=None,
                    )
                )

            semaphore = (
                asyncio.Semaphore(4)
            )

            async def inspect(
                post: FeedPost,
            ) -> None:
                async with semaphore:
                    await self.inspect_article(
                        client,
                        post,
                    )

            await asyncio.gather(
                *(
                    inspect(post)
                    for post in posts
                )
            )

            return posts
