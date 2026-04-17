"""M2: review_record + publish_package

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "review_record",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_job_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.String(128), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("revision_notes", sa.Text(), nullable=True),
        sa.Column("asset_version_at_review", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["content_job_id"], ["content_job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("decision IN ('approve', 'reject')", name="ck_review_record_decision"),
    )
    op.create_index("ix_review_record_job_id", "review_record", ["content_job_id"])

    op.create_table(
        "publish_package",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_job_id", sa.Integer(), nullable=False),
        sa.Column("package_version", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("impressions", sa.BigInteger(), nullable=True),
        sa.Column("plays", sa.BigInteger(), nullable=True),
        sa.Column("interactions", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["content_job_id"], ["content_job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_job_id", "package_version", name="uq_publish_package_job_version"),
    )
    op.create_index("ix_publish_package_job_id", "publish_package", ["content_job_id"])


def downgrade() -> None:
    op.drop_table("publish_package")
    op.drop_table("review_record")
