"""M1: create topic_raw and topic_canonical tables

Revision ID: 0001
Revises:
Create Date: 2026-04-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE platform AS ENUM ('weibo', 'zhihu', 'douyin')")

    op.create_table(
        "topic_raw",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.Enum("weibo", "zhihu", "douyin", name="platform"), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("heat", sa.Float(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("crawled_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_topic_raw_platform", "topic_raw", ["platform"])
    op.create_index("ix_topic_raw_platform_crawled_at", "topic_raw", ["platform", "crawled_at"])

    op.create_table(
        "topic_canonical",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("canonical_title", sa.String(512), nullable=False),
        sa.Column("cluster_key", sa.String(256), nullable=False),
        sa.Column("dedup_fingerprint", sa.String(128), nullable=False),
        sa.Column("combined_heat", sa.Float(), nullable=False),
        sa.Column("source_platforms", sa.JSON(), nullable=False),
        sa.Column("heat_score", sa.Float(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_fingerprint"),
    )
    op.create_index("ix_topic_canonical_cluster_key", "topic_canonical", ["cluster_key"])
    op.create_index("ix_topic_canonical_heat_score", "topic_canonical", ["heat_score"])
    op.create_index("ix_topic_canonical_last_seen_at", "topic_canonical", ["last_seen_at"])


def downgrade() -> None:
    op.drop_table("topic_canonical")
    op.drop_table("topic_raw")
    op.execute("DROP TYPE IF EXISTS platform")
