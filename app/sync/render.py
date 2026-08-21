from __future__ import annotations

import hashlib
import json

import discord

from app.sync.types import FeedPost


def render_hash(
    post: FeedPost,
    *,
    updated: bool,
) -> str:
    payload = {
        "title": post.title,
        "body": post.body,
        "url": post.url,
        "image_url": (
            post.image_url
            or ""
        ),
        "updated": updated,
    }

    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def build_embed(
    post: FeedPost,
    *,
    updated: bool,
) -> discord.Embed:
    description = post.body.strip()

    if len(description) > 4000:
        description = (
            description[:3997].rstrip()
            + "..."
        )

    embed = discord.Embed(
        title=(
            post.title[:256]
            if post.title
            else "JunctionNow"
        ),
        description=(
            description
            or None
        ),
        url=post.url or None,
    )

    if post.image_url:
        embed.set_image(
            url=post.image_url
        )

    if post.published_at:
        embed.timestamp = (
            post.published_at
        )

    embed.set_footer(
        text=(
            "JunctionNow • Updated"
            if updated
            else "JunctionNow"
        )
    )

    return embed


def no_mentions(
) -> discord.AllowedMentions:
    return discord.AllowedMentions.none()
