"""M3: topic_rule_evaluation for rule hit replay / audit

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topic_rule_evaluation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_canonical_id", sa.Integer(), nullable=False),
        sa.Column("rule_version", sa.String(64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("hit_details", sa.JSON(), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["topic_canonical_id"],
            ["topic_canonical.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_topic_rule_evaluation_topic_id_evaluated",
        "topic_rule_evaluation",
        ["topic_canonical_id", "evaluated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_topic_rule_evaluation_topic_id_evaluated", table_name="topic_rule_evaluation")
    op.drop_table("topic_rule_evaluation")
