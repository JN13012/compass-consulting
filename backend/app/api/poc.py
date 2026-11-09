"""POC tab: framing, test cases, dossier for the builder, evaluation bench and report (SPEC §3.8)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.api.kb import get_router
from app.core.config import get_settings
from app.core.db import get_engine, get_session
from app.core.models import Mission
from app.core.runtime import active_role
from app.llm.router import ConfidentialityViolationError, LlmRouter
from app.missions.analysis import role_for
from app.poc.bench import (
    Case,
    Criterion,
    corrections,
    failure_groups,
    metrics,
    parse_cases,
    run_cases,
    split_cases,
    verdict,
)
from app.poc.framing import Framing, dossier_zip, run_framing

router = APIRouter(prefix="/missions/{mission_id}/poc", tags=["poc"])
SessionDep = Annotated[Session, Depends(get_session)]
RouterDep = Annotated[LlmRouter, Depends(get_router)]

DEFAULT_ENDPOINT = "http://poc-commandes:8100/run"
DEMO_CASES = "commandes/data/commandes.jsonl"


class CasesInfo(BaseModel):
    total: int
    dev: int
    test: int
    a_refuser: int
    source: str


class PocOut(BaseModel):
    framing: dict[str, Any] | None
    cases: CasesInfo | None
    evaluation: dict[str, Any] | None
    default_endpoint: str = DEFAULT_ENDPOINT


class CasesIn(BaseModel):
    jsonl: str = Field(min_length=1, max_length=2_000_000)
    source: str = "fichier importé"


class EvaluateIn(BaseModel):
    endpoint: str = Field(default=DEFAULT_ENDPOINT, pattern=r"^https?://", max_length=500)


def _get(session: Session, mission_id: uuid.UUID) -> Mission:
    mission = session.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(404, "Mission introuvable")
    return mission


def _cases(poc: dict[str, Any]) -> list[Case]:
    return [Case.model_validate(c) for c in poc.get("cases") or []]


def _out(m: Mission) -> PocOut:
    poc = m.poc or {}
    cases = _cases(poc)
    info = None
    if cases:
        dev, test = split_cases(cases)
        info = CasesInfo(total=len(cases), dev=len(dev), test=len(test),
                         a_refuser=sum(c.expected is None for c in cases), source=poc.get("cases_source", ""))
    evaluation = poc.get("evaluation")
    if evaluation:  # per-case results are heavy: the report needs only the failures
        evaluation = {k: v for k, v in evaluation.items() if k != "results"}
    return PocOut(framing=poc.get("framing"), cases=info, evaluation=evaluation)


def _save(session: Session, m: Mission, **changes: Any) -> None:
    session.refresh(m)  # another request (e.g. loading cases during a long framing) may have written meanwhile
    m.poc = {**(m.poc or {}), **changes}  # new dict so SQLAlchemy sees the JSONB change
    session.commit()


@router.get("", response_model=PocOut)
def get_poc(mission_id: uuid.UUID, session: SessionDep) -> PocOut:
    return _out(_get(session, mission_id))


@router.post("/framing", response_model=PocOut)
def frame(mission_id: uuid.UUID, session: SessionDep, llm: RouterDep) -> PocOut:
    mission = _get(session, mission_id)
    if mission.solutions is None:
        raise HTTPException(409, "Lancez d'abord les solutions : le POC en découle.")
    try:
        framing = run_framing(mission, llm, role_for(mission, active_role(session)))
    except ConfidentialityViolationError as exc:
        raise HTTPException(403, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"Cadrage impossible : fournisseur IA indisponible ou réponse invalide "
                                 f"({type(exc).__name__}).") from exc
    _save(session, mission, framing=framing.model_dump())
    return _out(mission)


@router.put("/criteria", response_model=PocOut)
def set_criteria(mission_id: uuid.UUID, criteria: list[Criterion], session: SessionDep) -> PocOut:
    """The consultant has the last word on thresholds."""
    mission = _get(session, mission_id)
    current = (mission.poc or {}).get("framing")
    if current is None:
        raise HTTPException(409, "Cadrez d'abord le POC.")
    try:
        framing = Framing.model_validate({**current, "criteres": [c.model_dump() for c in criteria]})
    except ValidationError as exc:
        raise HTTPException(422, "Seuil invalide (taux entre 0 et 1, latence positive).") from exc
    _save(session, mission, framing=framing.model_dump())
    return _out(mission)


def _store_cases(session: Session, mission: Mission, jsonl: str, source: str) -> PocOut:
    try:
        cases = parse_cases(jsonl)
    except (ValueError, ValidationError) as exc:
        raise HTTPException(422, f"Jeu de cas invalide : {str(exc)[:200]}") from exc
    _save(session, mission, cases=[c.model_dump() for c in cases], cases_source=source, evaluation=None)
    return _out(mission)


@router.put("/cases", response_model=PocOut)
def set_cases(mission_id: uuid.UUID, body: CasesIn, session: SessionDep) -> PocOut:
    return _store_cases(session, _get(session, mission_id), body.jsonl, body.source)


@router.post("/cases/demo", response_model=PocOut)
def demo_cases(mission_id: uuid.UUID, session: SessionDep) -> PocOut:
    path = get_settings().poc_examples_dir / DEMO_CASES
    if not path.exists():
        raise HTTPException(404, "Jeu de démo introuvable (poc_examples non monté).")
    return _store_cases(session, _get(session, mission_id), path.read_text("utf-8"),
                        "démo : 50 commandes fictives Maison Lumen")


@router.get("/dossier.zip")
def dossier(mission_id: uuid.UUID, session: SessionDep) -> Response:
    mission = _get(session, mission_id)
    poc = mission.poc or {}
    if not poc.get("framing"):
        raise HTTPException(409, "Cadrez d'abord le POC.")
    framing = Framing.model_validate(poc["framing"])
    dev, test = split_cases(_cases(poc)) if poc.get("cases") else ([], [])
    data = dossier_zip(mission, framing, dev, len(test))
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="poc-dossier.zip"'})


def _call(endpoint: str) -> Any:
    def call(text: str) -> Any:
        r = httpx.post(endpoint, json={"input": text}, timeout=180)
        r.raise_for_status()
        return r.json().get("output")
    return call


def evaluate_in_background(mission_id: uuid.UUID, endpoint: str, call: Any = None) -> None:
    """Runs the frozen test cases against the POC and stores the report (own session: runs after the response)."""
    session = sessionmaker(bind=get_engine())()
    try:
        mission = _get(session, mission_id)
        poc = mission.poc or {}
        _, test = split_cases(_cases(poc))
        criteria = [Criterion.model_validate(c) for c in (poc.get("framing") or {}).get("criteres", [])]
        state: dict[str, Any] = dict(poc.get("evaluation") or {})

        def progress(done: int) -> None:
            state["done"] = done
            _save(session, mission, evaluation=dict(state))

        results = run_cases(test, call or _call(endpoint), progress)
        m = metrics(results)
        groups = failure_groups(results)
        checks = verdict(criteria, m)
        state.update(
            status="terminee", finished_at=datetime.now(UTC).isoformat(), metrics=m,
            verdict=[c.model_dump() for c in checks], passage_echelle=bool(checks) and all(c.atteint for c in checks),
            groupes=groups, corrections=corrections(groups), results=[r.model_dump() for r in results],
        )
        _save(session, mission, evaluation=state)
    except Exception as exc:  # noqa: BLE001 - reported in the interface instead of being lost in a log
        session.rollback()
        failed = session.get(Mission, mission_id)
        if failed is not None:
            _save(session, failed, evaluation={**((failed.poc or {}).get("evaluation") or {}), "status": "erreur",
                                                "erreur": f"{type(exc).__name__}: {exc}"[:300]})
    finally:
        session.close()


@router.post("/evaluate", response_model=PocOut, status_code=202)
def evaluate(mission_id: uuid.UUID, body: EvaluateIn, session: SessionDep, tasks: BackgroundTasks) -> PocOut:
    mission = _get(session, mission_id)
    poc = mission.poc or {}
    if not poc.get("framing"):
        raise HTTPException(409, "Cadrez d'abord le POC.")
    if not poc.get("cases"):
        raise HTTPException(409, "Ajoutez d'abord un jeu de cas.")
    if (poc.get("evaluation") or {}).get("status") == "en_cours":
        raise HTTPException(409, "Une évaluation est déjà en cours.")
    _, test = split_cases(_cases(poc))
    _save(session, mission, evaluation={"status": "en_cours", "endpoint": body.endpoint, "done": 0,
                                        "total": len(test), "started_at": datetime.now(UTC).isoformat()})
    tasks.add_task(evaluate_in_background, mission_id, body.endpoint)
    return _out(mission)
