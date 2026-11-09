from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import get_engine
from app.core.models import Passage, SourceDocument
from app.watch.service import (
    check_updates,
    cited_refs,
    diff_passages,
    load_deadlines,
    word_diff,
)

CONFIG = Path(__file__).resolve().parents[2] / "config"


def p(ref: str, text: str, pos: int, kind: str = "paragraph") -> Passage:
    return Passage(ref=ref, kind=kind, heading=ref, text=text, position=pos)


def test_word_diff_marks_only_changed_words() -> None:
    segs = word_diff("applicable à partir du 2 août 2026.", "applicable à partir du 2 décembre 2027.")
    ops = [(s.op, s.text) for s in segs]
    assert ("delete", "août 2026.") in ops and ("insert", "décembre 2027.") in ops
    assert "".join(s.text for s in segs if s.op != "insert") == "applicable à partir du 2 août 2026."


def test_diff_passages_classifies_changes_and_skips_recitals() -> None:
    old = [p("X-ART-1", "a b", 0), p("X-ART-2", "gone", 1), p("X-RCT-1", "old recital", 2, "recital")]
    new = [p("X-ART-1", "a  c", 0), p("X-ART-3", "new", 1), p("X-RCT-1", "changed recital", 2, "recital")]
    changes, unchanged = diff_passages(old, new)
    kinds = [(c.ref, c.kind) for c in changes]
    assert kinds == [("X-ART-1", "modifie"), ("X-ART-3", "ajoute"), ("X-ART-2", "supprime")]
    assert unchanged == 0
    same, n = diff_passages([p("Y-ART-1", "a  b", 0)], [p("Y-ART-1", "a b", 0)])
    assert same == [] and n == 1  # whitespace-only differences are not changes


class Lister:
    def consolidated_versions(self, celex: str) -> list[str]:
        if celex == "BROKEN":
            raise RuntimeError("down")
        return {"32022R2554": ["02022R2554-20221227", "02022R2554-20270101"],  # future version ignored
                "32014L0065": ["02014L0065-20250117", "02014L0065-20260606"]}.get(celex, [])


def test_check_updates_statuses() -> None:
    docs = [
        SourceDocument(code="DORA", title="t", version="02022R2554-20221227", original_celex="32022R2554"),
        SourceDocument(code="MIFID2", title="t", version="02014L0065-20250117", original_celex="32014L0065"),
        SourceDocument(code="DLT", title="t", version="32022R0858", original_celex="32022R0858"),
        SourceDocument(code="KO", title="t", version="x", original_celex="BROKEN"),
    ]

    class FakeSession:
        def scalars(self, _: object) -> list[SourceDocument]:
            return docs

    result = check_updates(FakeSession(), Lister(), date(2026, 11, 9), datetime(2026, 11, 9))  # type: ignore[arg-type]
    status = {t.code: (t.status, t.latest) for t in result.texts}
    assert status["DORA"] == ("a_jour", "02022R2554-20221227")
    assert status["MIFID2"] == ("nouvelle_version", "02014L0065-20260606")
    assert status["DLT"] == ("non_consolide", None)
    assert status["KO"][0] == "erreur"


def test_cited_refs_from_regulation() -> None:
    reg = {"textes": [{"obligations": [{"citations": [{"ref": "MIFID2-ART-48-1"}, {"ref": "RGPD-ART-3-2"}]}]}]}
    assert cited_refs(reg) == {"MIFID2-ART-48-1", "RGPD-ART-3-2"}
    assert cited_refs(None) == set()


@pytest.fixture
def session() -> Iterator[Session]:
    try:
        s = sessionmaker(bind=get_engine())()
        s.execute(select(1))
    except OperationalError:
        pytest.skip("database unreachable")
    yield s
    s.close()


@pytest.mark.db
def test_every_deadline_is_backed_by_its_passage(session: Session) -> None:
    """Dates are written by hand: each one must appear in the current text of the passage it cites."""
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
              "novembre", "décembre"]
    for d in load_deadlines(CONFIG / "deadlines.yaml"):
        text = session.scalars(select(Passage.text).join(SourceDocument)
                               .where(SourceDocument.is_current, Passage.ref == d.ref)).first()
        assert text is not None, d.ref
        day = "1er" if d.date.day == 1 else str(d.date.day)
        assert f"{day} {months[d.date.month - 1]} {d.date.year}" in text, (d.ref, d.date)


def test_is_affected_matches_paragraph_and_sub_points() -> None:
    from app.watch.service import is_affected

    assert is_affected("M-ART-48-1", {"M-ART-48-1-a"}) and not is_affected("M-ART-48-1", {"M-ART-48-10"})
