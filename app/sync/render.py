from __future__ import annotations

import hashlib
import json

import discord

from app.config import get_settings
from app.sync.types import FeedPost


def normalized_payload(post: FeedPost) -> dict[str, str]:
    return {
        "post_id": post.post_id.strip(),
        "title": post.title.strip(),
        "body": post.body.strip(),
        "url": post.url.strip(),
        "image_url": (post.image_url or "").strip(),
        "status": post.status.strip().lower(),
    }


def content_hash(post: FeedPost) -> str:
    payload = json.dumps(
        normalized_payload(post),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def render_hash(post: FeedPost) -> str:
    return content_hash(post)


def allowed_mentions() -> discord.AllowedMentions:
    return discord.AllowedMentions(
        everyone=False,
        users=False,
        roles=False,
        replied_user=False,
    )


def build_embed(post: FeedPost) -> discord.Embed:
    settings = get_settings()

    status = post.status.lower()

    if status in {
        "retracted",
        "removed",
        "deleted",
        "withdrawn",
    }:
        embed = discord.Embed(
            title=post.title[:256] if post.title else "JunctionNow Update",
            description=(
                "This JunctionNow post has been withdrawn "
                "or is no longer available."
            ),
            url=post.url or None,
        )

        embed.set_footer(text=settings.bot_footer_text)
        return embed

    description = post.body.strip()

    if len(description) > 3900:
        description = description[:3897].rstrip() + "..."

    embed = discord.Embed(
        title=post.title[:256] if post.title else settings.bot_brand_name,
        description=description or None,
        url=post.url or None,
    )

    if post.image_url:
        embed.set_image(url=post.image_url)

    if post.published_at:
        embed.timestamp = post.published_at

    embed.set_footer(text=settings.bot_footer_text)

    return embed
