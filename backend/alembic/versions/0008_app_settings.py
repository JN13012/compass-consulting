"""app settings

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-09
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(50), primary_key=True),
        sa.Column("value", sa.String(200), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
