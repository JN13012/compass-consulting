import json
from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.api.kb import get_router
from app.core.db import get_engine
from app.core.models import Confidentiality, Mission
from app.main import app
from app.missions import analysis
from app.missions.analysis import (
    BlockchainCheck,
    Diagnostic,
    blockchain_verdict,
    maturity_axes,
    quote_found,
    role_for,
    run_diagnostic,
    run_regulation,
    run_solutions,
)
from app.retrieval.search import Hit

from .fakes import fake_router

NOTES = "Deux assistantes ressaisissent chaque commande dans un tableur Excel partagé, puis dans l'ERP."


def mission(confidentiality: Confidentiality = Confidentiality.PUBLIC, focus: list[str] | None = None) -> Mission:
    return Mission(client="Test SA", sector="Distribution", context="ctx", notes=NOTES, focus=focus or ["ia"],
                   confidentiality=confidentiality)


DIAG = {
    "synthese": "Beaucoup de ressaisies.",
    "processus": [{"nom": "Commandes", "description": "par e-mail", "outils": ["Excel"], "volume": "900/mois"}],
    "irritants": [
        {"id": "I1", "titre": "Ressaisie", "description": "…", "impact": "élevé",
         "source": "ressaisissent chaque commande dans un tableur Excel partagé"},
        {"id": "I2", "titre": "Invention", "description": "…", "impact": "faible",
         "source": "Le PDG veut une blockchain quantique"},
    ],
    "maturite": [{"axe": "Données", "note": 1, "justification": "doublons"}],
}


def test_maturity_axes_add_nist_for_cyber() -> None:
    assert len(maturity_axes(["ia"])) == 5
    assert "Cyber — Protéger" in maturity_axes(["cyber"])


def test_quote_found_is_tolerant_but_strict_on_content() -> None:
    assert quote_found("« ressaisissent chaque commande dans un tableur Excel partagé »", NOTES)
    assert not quote_found("ressaisissent chaque facture", NOTES)
    assert not quote_found("ERP", NOTES)  # too short to prove anything


def test_diagnostic_flags_unverified_quotes() -> None:
    router, _ = fake_router(json.dumps(DIAG, ensure_ascii=False))
    diag = run_diagnostic(mission(), router, "reasoning")
    assert [i.source_verifiee for i in diag.irritants] == [True, False]


def test_blockchain_verdict_grid() -> None:
    base = dict(plusieurs_parties=True, sans_confiance_mutuelle=True, registre_partage=True,
                actif_programmable=False, intermediaire_suffit=False, explication="")
    assert blockchain_verdict(BlockchainCheck(**base)) == "pertinente"
    assert blockchain_verdict(BlockchainCheck(**{**base, "intermediaire_suffit": True})) == "deconseillee"
    assert blockchain_verdict(BlockchainCheck(**{**base, "sans_confiance_mutuelle": False})) == "deconseillee"


def test_solutions_verdict_computed_in_code_and_unknown_irritants_dropped() -> None:
    out = {"synthese": "s", "solutions": [
        {"irritant_id": "I1", "niveau": "blockchain", "titre": "Registre", "description": "d", "gain": "g",
         "cout": "c", "delai": "3 mois", "risques": "r", "horizon": "long_terme",
         "verification_blockchain": {"plusieurs_parties": False, "sans_confiance_mutuelle": False,
                                     "registre_partage": True, "actif_programmable": False,
                                     "intermediaire_suffit": True, "explication": "un ERP suffit",
                                     "verdict": "pertinente"}},
        {"irritant_id": "I9", "niveau": "ia", "titre": "Fantôme", "description": "d", "gain": "g", "cout": "c",
         "delai": "d", "risques": "r", "horizon": "quick_win"},
    ]}
    router, _ = fake_router(json.dumps(out))
    sols = run_solutions(mission(), Diagnostic.model_validate(DIAG), router, "reasoning")
    assert len(sols.solutions) == 1
    assert sols.solutions[0].verification_blockchain.verdict == "deconseillee"  # type: ignore[union-attr]


def test_confidential_missions_use_local_model() -> None:
    assert role_for(mission(Confidentiality.CONFIDENTIAL), "reasoning") == "local"
    assert role_for(mission(), "reasoning") == "reasoning"


def _hit(ref: str) -> Hit:
    import uuid

    return Hit(passage_id=uuid.uuid4(), ref=ref, kind="paragraphe", heading=ref, text="texte", source_code="NIS2",
               source_title="NIS 2", domain="cyber", url="https://eur-lex", version="X", consolidated=True,
               consulted_on=date(2026, 11, 7), original_url="https://eur-lex/o", score=0.8)


def test_regulation_keeps_only_obligations_with_retrieved_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSession:
        def scalars(self, *_: Any) -> list[Any]:
            from types import SimpleNamespace

            return [SimpleNamespace(code="NIS2", title="NIS 2"), SimpleNamespace(code="MICA", title="MiCA")]

    monkeypatch.setattr(analysis, "search", lambda *a, **k: ([_hit("NIS2-ART-21-2"), _hit("NIS2-ART-23-4")],
                                                              "fulltext"))
    router, _ = fake_router(
        json.dumps({"textes": [{"code": "NIS2", "applicable": "oui", "raisonnement": "fabricant"},
                               {"code": "MICA", "applicable": "non", "raisonnement": "pas de crypto"},
                               {"code": "INCONNU", "applicable": "oui", "raisonnement": "?"}]}),
        json.dumps({"obligations": [
            {"obligation": "Mesures de gestion des risques", "statut": "manquant", "justification": "pas de MFA",
             "passages": ["NIS2-ART-21-2"]},
            {"obligation": "Obligation inventée", "statut": "manquant", "justification": "…",
             "passages": ["NIS2-ART-999"]},
        ]}),
    )
    reg = run_regulation(FakeSession(), mission(), None, None, router, "reasoning")  # type: ignore[arg-type]
    assert [t.code for t in reg.textes] == ["NIS2"]
    assert [e.code for e in reg.ecartes] == ["MICA"]
    nis2 = reg.textes[0]
    assert [o.obligation for o in nis2.obligations] == ["Mesures de gestion des risques"]
    assert nis2.obligations_rejetees == 1
    assert nis2.obligations[0].citations[0].ref == "NIS2-ART-21-2"


# --- API (database) ------------------------------------------------------------------------------


@pytest.fixture
def session() -> Iterator[Session]:
    try:
        s = sessionmaker(bind=get_engine())()
        s.execute(select(1))
    except OperationalError:
        pytest.skip("database unreachable")
    yield s
    s.execute(delete(Mission).where(Mission.client == "Test API SA"))
    s.commit()
    s.close()


@pytest.mark.db
def test_api_create_analyze_and_seed(session: Session) -> None:
    client = TestClient(app)
    created = client.post("/missions", json={"client": "Test API SA", "sector": "Distribution", "notes": NOTES,
                                             "focus": ["ia"]}).json()
    router, _ = fake_router(json.dumps(DIAG, ensure_ascii=False))
    app.dependency_overrides[get_router] = lambda: router
    try:
        r = client.post(f"/missions/{created['id']}/analyze/diagnostic")
        blocked = client.post(f"/missions/{created['id']}/analyze/solutions")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200, r.text
    assert r.json()["diagnostic"]["irritants"][0]["source_verifiee"] is True
    assert r.json()["steps_done"] == ["diagnostic"]
    assert blocked.status_code in (200, 503)  # depends on the fake output, not on ordering rules

    first = client.post("/missions/demo").json()
    again = client.post("/missions/demo").json()
    demo = [m for m in again if m["client"] in {"Maison Lumen", "Banque Azur", "Hexa Industrie"}]
    assert len(demo) == 3 and len(first) == len(again)
