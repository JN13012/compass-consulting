"""Ingestion against the real PostgreSQL (skipped when the database is unreachable)."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import get_engine
from app.core.models import Passage, SourceDocument
from app.corpus.cellar import Version
from app.corpus.ingest import ingest_source
from app.corpus.parser import PARSER_VERSION
from app.corpus.sources import Source

FIX = Path(__file__).parent / "fixtures"
CODE = "ZZTEST"
SOURCE = Source(code=CODE, celex="32099R0001", short="Test", title="Acte de test", domain="test")
TODAY = date(2026, 11, 7)

pytestmark = pytest.mark.db


class FakeFetcher:
    def __init__(self, consolidated: bytes | None) -> None:
        self.consolidated = consolidated
        self.original = (FIX / "oj_act.xhtml").read_bytes()

    def versions(self, celex: str, today: date) -> list[Version]:
        original = Version(celex=celex, consolidated=False, as_of=None)
        if self.consolidated is None:
            return [original]
        return [
            Version(celex="02099R0001-20260301", consolidated=True, as_of=date(2026, 3, 1)),  # 404
            Version(celex="02099R0001-20260101", consolidated=True, as_of=date(2026, 1, 1)),
            original,
        ]

    def fetch_xhtml(self, celex: str) -> bytes:
        if celex == "02099R0001-20260301":
            raise RuntimeError("404")
        return self.consolidated if celex.startswith("0") and self.consolidated else self.original


@pytest.fixture
def session() -> Iterator[Session]:
    try:
        s = sessionmaker(bind=get_engine())()
        s.execute(select(1))
    except OperationalError:
        pytest.skip("database unreachable")
    s.execute(delete(SourceDocument).where(SourceDocument.code == CODE))
    s.commit()
    yield s
    s.rollback()
    s.execute(delete(SourceDocument).where(SourceDocument.code == CODE))
    s.commit()
    s.close()


def _docs(session: Session) -> list[SourceDocument]:
    return list(session.scalars(select(SourceDocument).where(SourceDocument.code == CODE)))


def test_ingest_is_idempotent_and_versioned(session: Session, tmp_path: Path) -> None:
    first = ingest_source(session, SOURCE, FakeFetcher(None), tmp_path, TODAY)
    assert first.status == "new", first.error
    assert first.counts["considerant"] == 2
    assert (tmp_path / "32099R0001.xhtml").exists()

    again = ingest_source(session, SOURCE, FakeFetcher(None), tmp_path, TODAY)
    assert again.status == "unchanged"
    assert len(_docs(session)) == 1

    # Same text parsed by an older parser -> re-parsed in place, no new version.
    _docs(session)[0].parser_version = 0
    session.commit()
    reparsed = ingest_source(session, SOURCE, FakeFetcher(None), tmp_path, TODAY)
    assert reparsed.status == "reparsed", reparsed.error
    assert len(_docs(session)) == 1 and _docs(session)[0].parser_version == PARSER_VERSION

    consolidated = (FIX / "consolidated_act.xhtml").read_bytes()
    updated = ingest_source(session, SOURCE, FakeFetcher(consolidated), tmp_path, TODAY)
    assert updated.status == "updated", updated.error
    assert "02099R0001-20260301" in updated.error  # unavailable newest version reported, then skipped
    docs = {d.version: d for d in _docs(session)}
    assert set(docs) == {"32099R0001", "02099R0001-20260101"}
    assert docs["02099R0001-20260101"].is_current and not docs["32099R0001"].is_current
    assert docs["02099R0001-20260101"].consolidated

    current = docs["02099R0001-20260101"]
    passages = {p.ref: p for p in session.scalars(select(Passage).where(Passage.document_id == current.id))}
    assert passages["ZZTEST-ART-4-1"].source_celex == "02099R0001-20260101"
    assert passages["ZZTEST-RCT-1"].source_celex == "32099R0001"  # recitals from the original act
    assert current.url.endswith("CELEX:02099R0001-20260101")
    assert current.original_url.endswith("CELEX:32099R0001")
