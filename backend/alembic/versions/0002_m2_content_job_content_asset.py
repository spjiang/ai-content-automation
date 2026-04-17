"""M2: content_job + content_asset

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JOB_STATUSES = (
    "NEW",
    "QUEUED",
    "GENERATING",
    "GENERATED",
    "IN_REVIEW",
    "APPROVED",
    "PACKAGED",
    "FAILED",
    "REVISE_REQUIRED",
)

_ASSET_TARGETS = ("douyin_graphic", "xiaohongshu")


def upgrade() -> None:
    op.create_table(
        "content_job",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="NEW"),
        sa.Column("topic_fingerprint", sa.String(128), nullable=False),
        sa.Column("canonical_title", sa.String(512), nullable=False),
        sa.Column("rule_version", sa.String(64), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("template_version", sa.String(64), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.Column("asset_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in _JOB_STATUSES)})",
            name="ck_content_job_status",
        ),
    )
    op.create_index("ix_content_job_topic_fingerprint", "content_job", ["topic_fingerprint"])
    op.create_index("ix_content_job_status", "content_job", ["status"])
    op.create_index("ix_content_job_created_at", "content_job", ["created_at"])

    op.create_table(
        "content_asset",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_job_id", sa.Integer(), nullable=False),
        sa.Column("publish_target", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("cover_text", sa.String(512), nullable=True),
        sa.Column("image_suggestions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["content_job_id"], ["content_job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_job_id", "publish_target", "version", name="uq_asset_job_target_version"),
        sa.CheckConstraint(
            f"publish_target IN ({', '.join(repr(t) for t in _ASSET_TARGETS)})",
            name="ck_content_asset_publish_target",
        ),
    )
    op.create_index("ix_content_asset_job_id", "content_asset", ["content_job_id"])


def downgrade() -> None:
    op.drop_table("content_asset")
    op.drop_table("content_job")
