"""corpus: versioned source documents, passages (full-text + vector)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-07
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # source_documents was empty in phase 0: recreate it with the versioned schema.
    op.drop_table("source_documents")
    op.create_table(
        "source_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("consolidated", sa.Boolean(), nullable=False),
        sa.Column("original_celex", sa.String(30), nullable=False),
        sa.Column("original_url", sa.String(1000), nullable=False),
        sa.Column("consulted_on", sa.Date(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("original_sha256", sa.String(64), nullable=False),
        sa.Column("language", sa.String(5), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("code", "version", name="uq_source_code_version"),
    )
    op.create_table(
        "passages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id", sa.Uuid(), sa.ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("ref", sa.String(80), nullable=False, index=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("heading", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("source_celex", sa.String(30), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column(
            "tsv",
            sa.dialects.postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('french', heading || ' ' || text)", persisted=True),
        ),
        sa.UniqueConstraint("document_id", "ref", name="uq_passage_doc_ref"),
    )
    op.create_index("ix_passages_tsv", "passages", ["tsv"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_table("passages")
    op.drop_table("source_documents")
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
