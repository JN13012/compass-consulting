from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.kb import get_router
from app.core.config import get_settings
from app.core.db import get_session
from app.core.models import Confidentiality, Mission
from app.llm.router import ConfidentialityViolationError, LlmRouter
from app.missions.analysis import (
    Diagnostic,
    Solutions,
    maturity_axes,
    role_for,
    run_diagnostic,
    run_regulation,
    run_solutions,
)
from app.missions.demo import DEMO_MISSIONS

router = APIRouter(prefix="/missions", tags=["missions"])

SessionDep = Annotated[Session, Depends(get_session)]
RouterDep = Annotated[LlmRouter, Depends(get_router)]
Focus = Literal["ia", "blockchain", "cyber"]
Step = Literal["diagnostic", "solutions", "regulation"]


class MissionIn(BaseModel):
    client: str = Field(min_length=1, max_length=200)
    sector: str = Field(min_length=1, max_length=100)
    context: str = ""
    notes: str = Field(default="", max_length=20_000)
    focus: list[Focus] = []
    confidentiality: Confidentiality = Confidentiality.PUBLIC


class MissionSummary(BaseModel):
    id: uuid.UUID
    client: str
    sector: str
    focus: list[str]
    confidentiality: Confidentiality
    created_at: datetime
    steps_done: list[str]


class MissionOut(MissionSummary):
    context: str
    notes: str
    maturity_axes: list[str]
    diagnostic: dict[str, Any] | None
    solutions: dict[str, Any] | None
    regulation: dict[str, Any] | None


def _steps(m: Mission) -> list[str]:
    return [s for s in ("diagnostic", "solutions", "regulation") if getattr(m, s) is not None]


def _summary(m: Mission) -> MissionSummary:
    return MissionSummary(id=m.id, client=m.client, sector=m.sector, focus=m.focus,
                          confidentiality=m.confidentiality, created_at=m.created_at, steps_done=_steps(m))


def _out(m: Mission) -> MissionOut:
    return MissionOut(**_summary(m).model_dump(), context=m.context, notes=m.notes,
                      maturity_axes=maturity_axes(m.focus), diagnostic=m.diagnostic, solutions=m.solutions,
                      regulation=m.regulation)


def _get(session: Session, mission_id: uuid.UUID) -> Mission:
    mission = session.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(404, "Mission introuvable")
    return mission


@router.get("", response_model=list[MissionSummary])
def list_missions(session: SessionDep) -> list[MissionSummary]:
    return [_summary(m) for m in session.scalars(select(Mission).order_by(Mission.created_at))]


@router.post("", response_model=MissionOut, status_code=201)
def create_mission(body: MissionIn, session: SessionDep) -> MissionOut:
    mission = Mission(**body.model_dump(), status="ouverte")
    session.add(mission)
    session.commit()
    return _out(mission)


@router.post("/demo", response_model=list[MissionSummary])
def seed_demo(session: SessionDep) -> list[MissionSummary]:
    """Creates the three demo missions if they do not exist yet (idempotent)."""
    existing = set(session.scalars(select(Mission.client)))
    for data in DEMO_MISSIONS:
        if data["client"] not in existing:
            fields = {**data, "confidentiality": Confidentiality(data["confidentiality"])}
            session.add(Mission(**fields, status="ouverte"))
    session.commit()
    return list_missions(session)


@router.get("/{mission_id}", response_model=MissionOut)
def get_mission(mission_id: uuid.UUID, session: SessionDep) -> MissionOut:
    return _out(_get(session, mission_id))


@router.delete("/{mission_id}", status_code=204)
def delete_mission(mission_id: uuid.UUID, session: SessionDep) -> None:
    session.delete(_get(session, mission_id))
    session.commit()


@router.post("/{mission_id}/analyze/{step}", response_model=MissionOut)
def analyze(mission_id: uuid.UUID, step: Step, session: SessionDep, llm: RouterDep) -> MissionOut:
    mission = _get(session, mission_id)
    if not mission.notes.strip():
        raise HTTPException(422, "Ajoutez des notes d'entretien avant de lancer l'analyse.")
    role = role_for(mission, get_settings().kb_role)
    diagnostic = Diagnostic.model_validate(mission.diagnostic) if mission.diagnostic else None
    solutions = Solutions.model_validate(mission.solutions) if mission.solutions else None
    try:
        if step == "diagnostic":
            mission.diagnostic = run_diagnostic(mission, llm, role).model_dump()
            mission.solutions = mission.regulation = None  # downstream results are now stale
        elif step == "solutions":
            if diagnostic is None:
                raise HTTPException(409, "Lancez d'abord le diagnostic.")
            mission.solutions = run_solutions(mission, diagnostic, llm, role).model_dump()
        else:
            embed = lambda q: llm.embed([q], mission.confidentiality)[0]  # noqa: E731
            mission.regulation = run_regulation(session, mission, diagnostic, solutions, llm, role, embed).model_dump()
    except HTTPException:
        raise
    except ConfidentialityViolationError as exc:
        raise HTTPException(403, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"Analyse impossible : fournisseur IA indisponible ou réponse invalide "
                                 f"({type(exc).__name__}).") from exc
    session.commit()
    return _out(mission)
