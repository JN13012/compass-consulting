"""Phase 0 tables. Other entities from SPEC §6 are added in later phases."""

import enum
import uuid
from datetime import UTC, date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Confidentiality(enum.StrEnum):
    PUBLIC = "public"
    CONFIDENTIAL = "confidentiel"


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str] = mapped_column(String(100))
    context: Mapped[str] = mapped_column(Text, default="")
    confidentiality: Mapped[Confidentiality] = mapped_column(
        Enum(Confidentiality, values_callable=lambda e: [m.value for m in e], name="confidentiality"),
        default=Confidentiality.PUBLIC,
    )
    status: Mapped[str] = mapped_column(String(30), default="ouverte")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # Practices involved: any of "ia", "blockchain", "cyber".
    focus: Mapped[list[str]] = mapped_column(JSONB, default=list)
    # Interview notes / process description provided by the consultant.
    notes: Mapped[str] = mapped_column(Text, default="")
    # Analysis results (validated JSON), None until generated.
    diagnostic: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    solutions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    regulation: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


EMBEDDING_DIM = 1024  # bge-m3


class SourceDocument(Base):
    """One ingested version of an official text. Old versions are kept (is_current=False)."""

    __tablename__ = "source_documents"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_source_code_version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))  # human-facing EUR-Lex link of the version used
    domain: Mapped[str] = mapped_column(String(50))
    version: Mapped[str] = mapped_column(String(50))  # CELEX of the version used for articles/annexes
    consolidated: Mapped[bool] = mapped_column(Boolean, default=False)
    original_celex: Mapped[str] = mapped_column(String(30))
    original_url: Mapped[str] = mapped_column(String(1000))  # Official Journal text (legally binding)
    consulted_on: Mapped[date] = mapped_column(Date)
    sha256: Mapped[str] = mapped_column(String(64))  # main file
    original_sha256: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(5), default="fr")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    parser_version: Mapped[int] = mapped_column(Integer, default=1)

    passages: Mapped[list["Passage"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Passage(Base):
    __tablename__ = "passages"
    __table_args__ = (UniqueConstraint("document_id", "ref", name="uq_passage_doc_ref"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"))
    ref: Mapped[str] = mapped_column(String(80), index=True)  # stable id, e.g. MICA-ART-3-1-5
    kind: Mapped[str] = mapped_column(String(20))  # article | paragraphe | point | considerant | annexe
    heading: Mapped[str] = mapped_column(Text)  # e.g. "Article 3 — Définitions, paragraphe 1"
    text: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    source_celex: Mapped[str] = mapped_column(String(30))  # recitals come from the original act
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    document: Mapped[SourceDocument] = relationship(back_populates="passages")
