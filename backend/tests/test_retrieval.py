from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.api.kb import get_router
from app.core.db import get_engine
from app.core.models import SourceDocument
from app.main import app
from app.retrieval.search import detect_sources, or_query, search

from .fakes import fake_router


def test_or_query_drops_question_words() -> None:
    q = or_query("Comment MiCA définit-il un crypto-actif ?")
    assert "Comment" not in q and "définit" not in q and "MiCA" not in q
    assert "crypto-actif" in q


def test_detect_sources() -> None:
    assert detect_sources("Que dit NIS 2 sur les incidents ?") == ["NIS2"]
    assert detect_sources("articulation entre DORA et le RGPD") == ["DORA", "RGPD"]
    assert detect_sources("Question générale") == []


# --- against the ingested corpus (skipped if the database or corpus is missing) ---------------


@pytest.fixture
def session() -> Iterator[Session]:
    try:
        s = sessionmaker(bind=get_engine())()
        n = s.scalar(select(func.count()).select_from(SourceDocument).where(SourceDocument.code == "MICA"))
    except OperationalError:
        pytest.skip("database unreachable")
    if not n:
        pytest.skip("corpus not ingested")
    yield s
    s.close()


@pytest.mark.db
def test_definition_is_found(session: Session) -> None:
    hits, mode = search(session, "Qu'est-ce qu'un jeton de monnaie électronique ?", limit=3)
    assert mode == "fulltext"
    assert "MICA-ART-3-1-33" in [h.ref for h in hits]


@pytest.mark.db
def test_named_text_restricts_search(session: Session) -> None:
    hits, _ = search(session, "Délai de notification d'un incident significatif selon NIS 2", limit=5)
    assert hits and all(h.source_code == "NIS2" for h in hits)


@pytest.mark.db
def test_api_ask_end_to_end_with_fake_model(session: Session) -> None:
    router, _ = fake_router('{"statut": "OK", "reponse": "Synthèse.", "passages": ["{first}"]}')
    app.dependency_overrides[get_router] = lambda: router
    try:
        r = TestClient(app).post("/kb/ask", json={"question": "Qu'est-ce qu'un jeton de monnaie électronique ?"})
    finally:
        app.dependency_overrides.clear()
    body = r.json()
    assert r.status_code == 200 and body["status"] == "answered"
    cited = body["citations"][0]
    assert cited["url"].startswith("https://eur-lex.europa.eu/") and cited["text"]


@pytest.mark.db
def test_api_refuses_off_topic(session: Session) -> None:
    router, completion = fake_router("{}")
    app.dependency_overrides[get_router] = lambda: router
    try:
        r = TestClient(app).post("/kb/ask", json={"question": "Quelle est la recette de la tarte tatin ?"})
    finally:
        app.dependency_overrides.clear()
    assert r.json()["status"] == "refused" and completion.calls == []


@pytest.mark.db
def test_api_sources_lists_corpus(session: Session) -> None:
    rows = TestClient(app).get("/kb/sources").json()
    codes = {row["code"] for row in rows}
    assert {"MICA", "AIACT", "NIS2", "CRA"} <= codes
    assert all(row["passages"] > 0 for row in rows)
