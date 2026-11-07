"""Phase 0 tables. Other entities from SPEC §6 are added in later phases."""

import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

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


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    domain: Mapped[str] = mapped_column(String(50))
    version: Mapped[str] = mapped_column(String(50), default="1")
    consulted_on: Mapped[date] = mapped_column(Date)
    sha256: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(5), default="fr")
