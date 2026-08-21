from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Guild(Base):
    __tablename__ = "guilds"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    installed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False,
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime)

    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="guild",
        cascade="all, delete-orphan",
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guilds.guild_id", ondelete="CASCADE"),
        nullable=False,
    )

    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    guild: Mapped[Guild] = relationship(back_populates="subscriptions")

    deliveries: Mapped[list[Delivery]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_subscriptions_guild_enabled", "guild_id", "enabled"),
    )


class SourcePost(Base):
    __tablename__ = "source_posts"

    post_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(
        String(50),
        default="published",
        nullable=False,
    )

    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)

    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False,
    )

    deliveries: Mapped[list[Delivery]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
    )


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    subscription_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )

    post_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("source_posts.post_id", ondelete="CASCADE"),
        nullable=False,
    )

    discord_message_id: Mapped[int | None] = mapped_column(BigInteger)

    delivered_revision: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    render_hash: Mapped[str] = mapped_column(
        String(64),
        default="",
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    last_error: Mapped[str | None] = mapped_column(Text)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    subscription: Mapped[Subscription] = relationship(
        back_populates="deliveries"
    )
    post: Mapped[SourcePost] = relationship(back_populates="deliveries")

    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "post_id",
            name="uq_delivery_subscription_post",
        ),
        Index("ix_deliveries_status", "status"),
    )


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    guild_id: Mapped[int | None] = mapped_column(BigInteger)
    post_id: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False,
    )

    metadata_json: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_analytics_created_at", "created_at"),
        Index("ix_analytics_event_type", "event_type"),
    )
