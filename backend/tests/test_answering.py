from datetime import date
from typing import Any

import pytest

from app.answering import service
from app.answering.service import AnswerSettings, answer_question, parse_model_output
from app.retrieval.search import Hit

from .fakes import fake_router


def hit(ref: str, score: float = 0.8) -> Hit:
    import uuid

    return Hit(
        passage_id=uuid.uuid4(), ref=ref, kind="paragraphe", heading=f"Heading {ref}", text=f"Texte {ref}",
        source_code="MICA", source_title="MiCA", domain="crypto", url="https://eur-lex/x", version="X",
        consolidated=True, consulted_on=date(2026, 11, 7), original_url="https://eur-lex/o", score=score,
    )


@pytest.fixture
def hits(monkeypatch: pytest.MonkeyPatch) -> list[Hit]:
    found = [hit("MICA-ART-3-1-33"), hit("MICA-ART-48-1", 0.6)]

    def fake_search(*args: Any, **kwargs: Any) -> tuple[list[Hit], str]:
        return list(found), "fulltext"

    monkeypatch.setattr(service, "search", fake_search)
    return found


def ask(router: Any, question: str = "Qu'est-ce qu'un EMT ?") -> service.Answer:
    return answer_question(None, router, question, AnswerSettings(min_score=0.3))  # type: ignore[arg-type]


def test_answer_with_valid_citations(hits: list[Hit]) -> None:
    router, completion = fake_router('{"statut": "OK", "reponse": "Un EMT est…", "passages": ["MICA-ART-3-1-33"]}')
    ans = ask(router)
    assert ans.status == "answered"
    assert [c.ref for c in ans.citations] == ["MICA-ART-3-1-33"]
    assert ans.citations[0].text == "Texte MICA-ART-3-1-33"  # text comes from retrieval, not the model
    assert "[MICA-ART-3-1-33]" in completion.calls[0]["messages"][1]["content"]


def test_layer1_refusal_does_not_call_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "search", lambda *a, **k: ([hit("X-1", score=0.1)], "fulltext"))
    router, completion = fake_router("{}")
    ans = ask(router)
    assert ans.status == "refused" and ans.refusal_reason == "aucun_passage_pertinent"
    assert completion.calls == []


def test_layer1_uses_similarity_in_vector_modes() -> None:
    from dataclasses import replace

    from app.answering.service import is_relevant

    settings = AnswerSettings(min_similarity=0.5)
    assert not is_relevant([replace(hit("A"), similarity=0.42)], "hybrid", settings)
    assert is_relevant([replace(hit("A"), similarity=0.42), replace(hit("B"), similarity=0.61)], "vector", settings)
    assert not is_relevant([hit("A")], "hybrid", settings)  # no similarity known -> refuse


def test_model_says_insufficient(hits: list[Hit]) -> None:
    router, _ = fake_router('{"statut": "INSUFFISANT", "reponse": "", "passages": []}')
    assert ask(router).refusal_reason == "insuffisant"


def test_invented_citation_is_rejected(hits: list[Hit]) -> None:
    router, _ = fake_router('{"statut": "OK", "reponse": "…", "passages": ["MICA-ART-999"]}')
    ans = ask(router)
    assert ans.status == "refused" and ans.refusal_reason == "citation_invalide"
    assert ans.citations == []


def test_answer_without_citation_is_rejected(hits: list[Hit]) -> None:
    router, _ = fake_router('{"statut": "OK", "reponse": "…", "passages": []}')
    assert ask(router).refusal_reason == "citation_invalide"


def test_malformed_output_retried_once(hits: list[Hit]) -> None:
    router, completion = fake_router(
        "désolé, voici :", '```json\n{"statut": "OK", "reponse": "R", "passages": ["MICA-ART-48-1"]}\n```'
    )
    ans = ask(router)
    assert ans.status == "answered" and ans.attempts == 2 and len(completion.calls) == 2


def test_malformed_output_twice_is_refused(hits: list[Hit]) -> None:
    router, completion = fake_router("pas du json")
    ans = ask(router)
    assert ans.refusal_reason == "reponse_invalide" and len(completion.calls) == 2


def test_parse_model_output_tolerates_surrounding_text() -> None:
    parsed = parse_model_output('Voici: {"statut":"OK","reponse":"x","passages":["A-1"]} fin')
    assert parsed is not None and parsed.passages == ["A-1"]
    assert parse_model_output('{"statut":"PEUT-ETRE"}') is None
