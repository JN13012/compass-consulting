"""missions: focus, notes, analysis results

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-07
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("missions", sa.Column("focus", JSONB(), nullable=False, server_default="[]"))
    op.add_column("missions", sa.Column("notes", sa.Text(), nullable=False, server_default=""))
    for col in ("diagnostic", "solutions", "regulation"):
        op.add_column("missions", sa.Column(col, JSONB(), nullable=True))


def downgrade() -> None:
    for col in ("regulation", "solutions", "diagnostic", "notes", "focus"):
        op.drop_column("missions", col)
