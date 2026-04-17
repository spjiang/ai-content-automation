"""SQLAlchemy ORM models — M1 topics + M2 jobs / assets / review / packages."""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.session import Base


class Platform(str, enum.Enum):
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    DOUYIN = "douyin"


class JobStatus(str, enum.Enum):
    NEW = "NEW"
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PACKAGED = "PACKAGED"
    FAILED = "FAILED"
    REVISE_REQUIRED = "REVISE_REQUIRED"


class PublishTarget(str, enum.Enum):
    DOUYIN_GRAPHIC = "douyin_graphic"
    XIAOHONGSHU = "xiaohongshu"


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

    __table_args__ = (Index("ix_topic_raw_platform_crawled_at", "platform", "crawled_at"),)


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

    rule_evaluations: Mapped[list["TopicRuleEvaluation"]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )


class TopicRuleEvaluation(Base):
    """规则引擎单次评估审计，用于回放与误杀/漏放排查（M3）。"""

    __tablename__ = "topic_rule_evaluation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_canonical_id: Mapped[int] = mapped_column(
        ForeignKey("topic_canonical.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    passed: Mapped[bool] = mapped_column(nullable=False)
    hit_details: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    topic: Mapped["TopicCanonical"] = relationship(back_populates="rule_evaluations")


class ContentJob(Base):
    """生成任务，贯穿抓取后到发布包的全链路状态机。"""

    __tablename__ = "content_job"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=JobStatus.NEW.value)
    topic_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    canonical_title: Mapped[str] = mapped_column(String(512), nullable=False)
    rule_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    template_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    asset_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    assets: Mapped[list["ContentAsset"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    reviews: Mapped[list["ReviewRecord"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    packages: Mapped[list["PublishPackage"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_content_job_status", "status"),)


class ContentAsset(Base):
    """按平台版本保存的生成内容资产。"""

    __tablename__ = "content_asset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_job_id: Mapped[int] = mapped_column(ForeignKey("content_job.id", ondelete="CASCADE"), index=True)
    publish_target: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cover_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_suggestions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    job: Mapped["ContentJob"] = relationship(back_populates="assets")

    __table_args__ = (
        UniqueConstraint("content_job_id", "publish_target", "version", name="uq_asset_job_target_version"),
    )


class ReviewRecord(Base):
    """人工审核记录。"""

    __tablename__ = "review_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_job_id: Mapped[int] = mapped_column(ForeignKey("content_job.id", ondelete="CASCADE"), index=True)
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_version_at_review: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    job: Mapped["ContentJob"] = relationship(back_populates="reviews")


class PublishPackage(Base):
    """审核通过后的版本化发布包。"""

    __tablename__ = "publish_package"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_job_id: Mapped[int] = mapped_column(ForeignKey("content_job.id", ondelete="CASCADE"), index=True)
    package_version: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    impressions: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    plays: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    interactions: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    job: Mapped["ContentJob"] = relationship(back_populates="packages")

    __table_args__ = (
        UniqueConstraint("content_job_id", "package_version", name="uq_publish_package_job_version"),
    )
