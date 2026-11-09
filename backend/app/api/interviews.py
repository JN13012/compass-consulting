from __future__ import annotations

import uuid
from functools import cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.api.missions import MissionOut, RouterDep, SessionDep, _get, _out
from app.core.config import get_settings
from app.core.runtime import active_role
from app.interviews.guide import (
    FollowUps,
    Interview,
    Section,
    compile_notes,
    load_guide,
    render_blank,
    sections_for,
    suggest_followups,
)
from app.llm.router import ConfidentialityViolationError
from app.missions.analysis import role_for

router = APIRouter(prefix="/missions/{mission_id}/interview", tags=["interviews"])


@cache
def guide() -> list[Section]:
    return load_guide(Path(get_settings().llm_config_path).parent / "interview_guide.yaml")


class InterviewOut(BaseModel):
    sections: list[Section]
    interview: Interview


def _interview(raw: dict[str, object] | None) -> Interview:
    return Interview.model_validate(raw or {})


@router.get("", response_model=InterviewOut)
def get_interview(mission_id: uuid.UUID, session: SessionDep) -> InterviewOut:
    m = _get(session, mission_id)
    return InterviewOut(sections=sections_for(guide(), m.focus), interview=_interview(m.interview))


@router.put("", response_model=InterviewOut)
def save_interview(mission_id: uuid.UUID, body: Interview, session: SessionDep) -> InterviewOut:
    m = _get(session, mission_id)
    m.interview = body.model_dump()
    session.commit()
    return InterviewOut(sections=sections_for(guide(), m.focus), interview=body)


@router.post("/notes", response_model=MissionOut)
def to_notes(mission_id: uuid.UUID, session: SessionDep) -> MissionOut:
    """Replaces the mission notes with the answered grid. Analyses based on the old notes are cleared."""
    m = _get(session, mission_id)
    notes = compile_notes(sections_for(guide(), m.focus), _interview(m.interview))
    if not notes:
        raise HTTPException(422, "Aucune réponse saisie dans la grille.")
    if notes != m.notes:
        m.notes = notes
        m.diagnostic = m.solutions = m.regulation = None
    session.commit()
    return _out(m)


@router.post("/followups", response_model=FollowUps)
def followups(mission_id: uuid.UUID, session: SessionDep, llm: RouterDep) -> FollowUps:
    m = _get(session, mission_id)
    role = role_for(m, active_role(session))
    try:
        return suggest_followups(llm, role, m, sections_for(guide(), m.focus), _interview(m.interview))
    except ConfidentialityViolationError as exc:
        raise HTTPException(403, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"Suggestions impossibles : fournisseur IA indisponible "
                                 f"({type(exc).__name__}).") from exc


@router.get("/print", response_class=HTMLResponse)
def print_blank(mission_id: uuid.UUID, session: SessionDep) -> HTMLResponse:
    m = _get(session, mission_id)
    return HTMLResponse(render_blank(sections_for(guide(), m.focus), m))
