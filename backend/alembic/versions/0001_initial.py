"""initial: pgvector, missions, source_documents

Revision ID: 0001
Revises:
Create Date: 2026-11-07
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    confidentiality = sa.Enum("public", "confidentiel", name="confidentiality")
    op.create_table(
        "missions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("client", sa.String(200), nullable=False),
        sa.Column("sector", sa.String(100), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("confidentiality", confidentiality, nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "source_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("consulted_on", sa.Date(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("language", sa.String(5), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("source_documents")
    op.drop_table("missions")
    sa.Enum(name="confidentiality").drop(op.get_bind(), checkfirst=True)
