import io
import json
import uuid
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.api import poc as poc_api
from app.api.kb import get_router
from app.core.db import get_engine
from app.core.models import Confidentiality, Mission
from app.main import app
from app.poc.bench import (
    Case,
    Criterion,
    corrections,
    failure_groups,
    judge,
    metrics,
    parse_cases,
    percentile,
    run_cases,
    same,
    split_cases,
    verdict,
)
from app.poc.framing import Framing, constraints, dossier_zip, run_framing

from .fakes import fake_router

DEMO = Path(__file__).parents[2] / "poc_examples" / "commandes" / "data" / "commandes.jsonl"
EXPECTED = {"client": "Atelier Neuf", "date_livraison": "2026-12-04",
            "lignes": [{"reference": "LUM-POC-NOVA", "quantite": 2}], "total_ht": 520.0}


def case(i: int, expected: dict[str, Any] | None = EXPECTED) -> Case:
    return Case(id=f"C{i:02d}", input=f"commande {i}", expected=expected)


def test_same_is_tolerant_on_form_strict_on_content() -> None:
    assert same("Atelier Neuf", " atelier  neuf ")
    assert same(520, 520.004)
    assert not same(520, 521)
    lines = [{"reference": "A", "quantite": 2}, {"reference": "B", "quantite": 1}]
    got = [{"reference": "B", "quantite": 1.0, "prix_unitaire": 9}, {"reference": "A", "quantite": 2}]
    assert same(lines, got)  # order and extra keys do not matter
    assert not same(lines, [{"reference": "A", "quantite": 3}, {"reference": "B", "quantite": 1}])


def test_judge_labels() -> None:
    assert judge(case(1), {**EXPECTED, "total_ht": 520}, 1.0).label == "correct"
    assert judge(case(1), {**EXPECTED, "client": "Autre"}, 1.0).label == "champ_faux"
    assert judge(case(1), {"refus": "ambigu"}, 1.0).label == "faux_refus"
    assert judge(case(2, None), {"refus": "ambigu"}, 1.0).label == "refus_correct"
    assert judge(case(2, None), EXPECTED, 1.0).label == "reponse_au_lieu_de_refus"
    assert judge(case(1), "oops", 1.0).label == "erreur_technique"


def test_split_is_stratified_and_deterministic() -> None:
    cases = [case(i) for i in range(20)] + [case(i, None) for i in range(20, 25)]
    dev, test = split_cases(cases)
    assert (len(dev), len(test)) == (10, 15)
    assert sum(c.expected is None for c in dev) == 2
    assert split_cases(list(reversed(cases))) == (dev, test)
    assert not {c.id for c in dev} & {c.id for c in test}


def test_metrics_verdict_and_report_are_computed_in_python() -> None:
    outputs = {"C01": EXPECTED, "C02": {**EXPECTED, "date_livraison": "2026-12-05"}, "C03": {"refus": "x"},
               "C04": {"refus": "x"}, "C05": EXPECTED}
    cases = [case(1), case(2), case(3), case(4, None), case(5, None)]
    by_input = {c.input: outputs[c.id] for c in cases}
    results = run_cases(cases, lambda text: by_input[text])
    m = metrics(results)
    assert m["justesse_document"]["k"] == 1 and m["justesse_document"]["n"] == 3
    assert m["justesse_champs"] == {**m["justesse_champs"], "k": 7, "n": 12}
    assert m["refus_corrects"]["k"] == 1 and m["faux_refus"]["k"] == 1
    lo, hi = m["justesse_document"]["ic95"]
    assert lo < 1 / 3 < hi

    checks = verdict([Criterion(metrique="justesse_document", seuil=0.3),
                      Criterion(metrique="faux_refus", seuil=0.05)], m)
    assert [c.atteint for c in checks] == [True, False]
    assert not checks[0].robuste  # 1/3 passes 0.3, but the interval does not

    groups = failure_groups(results)
    assert {g["cause"] for g in groups} == {"champ:date_livraison", "faux_refus", "reponse_au_lieu_de_refus"}
    fixes = corrections(groups)
    assert any("date_livraison" in f and "2026-12-04" in f for f in fixes)


def test_transport_error_is_a_result_not_a_crash() -> None:
    def boom(text: str) -> Any:
        raise TimeoutError("trop long")

    [r] = run_cases([case(1)], boom)
    assert r.label == "erreur_technique" and "TimeoutError" in r.detail
    assert metrics([r])["erreurs_techniques"] == 1


def test_percentile() -> None:
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.95) == 10
    assert percentile([], 0.95) == 0


def test_parse_cases_rejects_duplicates() -> None:
    line = json.dumps({"id": "A", "input": "x", "expected": None})
    with pytest.raises(ValueError):
        parse_cases(f"{line}\n{line}")


def test_demo_dataset_is_consistent() -> None:
    cases = parse_cases(DEMO.read_text("utf-8"))
    assert len(cases) == 50 and sum(c.expected is None for c in cases) == 10
    catalog = {p["reference"]: p["prix_ht"] for p in json.loads((DEMO.parents[1] / "catalog.json").read_text())}
    for c in cases:
        if c.expected:
            total = sum(catalog[x["reference"]] * x["quantite"] for x in c.expected["lignes"])
            assert c.expected["total_ht"] == pytest.approx(total)


FRAMING = {
    "nom": "Agent commandes", "solution_retenue": "Lecture automatique des commandes", "objectif": "Supprimer la "
    "ressaisie.", "perimetre": ["e-mails"], "user_stories": ["En tant qu'assistante…"], "donnees": "50 commandes",
    "criteres": [{"metrique": "justesse_document", "seuil": 0.9, "justification": "4 % d'erreurs aujourd'hui"}],
}


def mission(conf: Confidentiality = Confidentiality.PUBLIC) -> Mission:
    return Mission(id=uuid.uuid4(), client="Test SA", sector="Distribution", context="ctx", notes="n", focus=["ia"],
                   confidentiality=conf,
                   regulation={"textes": [{"code": "AIACT", "titre": "AI Act", "applicable": "oui"},
                                          {"code": "MICA", "titre": "MiCA", "applicable": "non"}]},
                   solutions={"synthese": "s", "solutions": []})


def test_framing_adds_mission_constraints_in_code() -> None:
    llm, calls = fake_router(json.dumps({**FRAMING, "contraintes": ["inventée"]}))
    f = run_framing(mission(Confidentiality.CONFIDENTIAL), llm, "local")
    assert "inventée" not in f.contraintes
    assert f.contraintes[0].startswith("Mission confidentielle")
    assert any("AIACT" in c for c in f.contraintes) and not any("MICA" in c for c in f.contraintes)
    assert calls.calls[0]["model"] == "fake/local"
    assert constraints(mission())[0].startswith("Données de test")


def test_framing_rejects_out_of_range_threshold() -> None:
    with pytest.raises(ValueError):
        Framing.model_validate({**FRAMING, "criteres": [{"metrique": "faux_refus", "seuil": 5}]})


def test_dossier_contains_dev_cases_only() -> None:
    dev, test = split_cases([case(i) for i in range(10)])
    data = dossier_zip(mission(), Framing.model_validate(FRAMING), dev, len(test))
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()
    for f in ("CLAUDE.md", "SPEC.md", "ARCHITECTURE.md", "INTERFACE.md", "eval/README.md", "eval/cases.jsonl"):
        assert f"poc-agent-commandes/{f}" in names
    shipped = z.read("poc-agent-commandes/eval/cases.jsonl").decode().splitlines()
    assert {json.loads(x)["id"] for x in shipped} == {c.id for c in dev}
    assert "6 cas" in z.read("poc-agent-commandes/CLAUDE.md").decode()


# --- API (database) ------------------------------------------------------------------------------


@pytest.fixture
def db() -> Iterator[Session]:
    try:
        session = sessionmaker(bind=get_engine())()
        session.connection()
    except OperationalError:
        pytest.skip("database unreachable")
    yield session
    session.close()


@pytest.mark.db
def test_poc_api_end_to_end(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    m = mission()
    db.add(m)
    db.commit()
    llm, _ = fake_router(json.dumps(FRAMING))
    app.dependency_overrides[get_router] = lambda: llm
    client = TestClient(app)
    try:
        base = f"/missions/{m.id}/poc"
        assert client.post(f"{base}/evaluate", json={}).status_code == 409
        assert client.post(f"{base}/framing").json()["framing"]["nom"] == "Agent commandes"
        bad = client.put(f"{base}/criteria", json=[{"metrique": "justesse_document", "seuil": 2}])
        assert bad.status_code == 422
        jsonl = "".join(case(i).model_dump_json() + "\n" for i in range(10))
        info = client.put(f"{base}/cases", json={"jsonl": jsonl}).json()["cases"]
        assert (info["dev"], info["test"]) == (4, 6)
        assert client.get(f"{base}/dossier.zip").headers["content-type"] == "application/zip"

        real = poc_api.evaluate_in_background
        monkeypatch.setattr(poc_api, "evaluate_in_background",
                            lambda mid, endpoint: real(mid, endpoint, call=lambda text: EXPECTED))
        started = client.post(f"{base}/evaluate", json={"endpoint": "http://poc:8100/run"})
        assert started.status_code == 202
        report = client.get(base).json()["evaluation"]
        assert report["status"] == "terminee" and report["passage_echelle"] is True
        assert report["metrics"]["justesse_document"]["k"] == 6
        assert "results" not in report
        assert "poc" in client.get(f"/missions/{m.id}").json()["steps_done"]
    finally:
        app.dependency_overrides.clear()
        db.delete(db.get(Mission, m.id))
        db.commit()
