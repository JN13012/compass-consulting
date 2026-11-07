"""benchmarks

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-07
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "benchmarks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("mission_id", sa.Uuid(), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("template", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data", JSONB(), nullable=False),
    )
    op.create_index("ix_benchmarks_mission", "benchmarks", ["mission_id"])


def downgrade() -> None:
    op.drop_table("benchmarks")
