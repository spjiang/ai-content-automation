"""SQLAlchemy ORM models — M1 entities: topic_raw, topic_canonical."""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.session import Base


class Platform(str, enum.Enum):
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    DOUYIN = "douyin"


class TopicRaw(Base):
    """原始抓取记录，一条对应平台上的一个热点条目。"""

    __tablename__ = "topic_raw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(Enum(Platform), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    heat: Mapped[float | None] = mapped_column(Float, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_topic_raw_platform_crawled_at", "platform", "crawled_at"),
    )


class TopicCanonical(Base):
    """归一化话题，多条 topic_raw 可聚合为一条。"""

    __tablename__ = "topic_canonical"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_title: Mapped[str] = mapped_column(String(512), nullable=False)
    cluster_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    dedup_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    combined_heat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_platforms: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    heat_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_topic_canonical_heat_score", "heat_score"),
        Index("ix_topic_canonical_last_seen_at", "last_seen_at"),
    )
