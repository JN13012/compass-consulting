from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_session
from app.core.models import SourceDocument, WatchCheck
from app.core.runtime import SELECTABLE_ROLES, active_role, set_active_role
from app.llm.router import LlmConfig, RoleConfig

router = APIRouter(tags=["system"])
SessionDep = Annotated[Session, Depends(get_session)]

Status = Literal["ok", "unreachable", "no_key", "not_configured"]


class AiOption(BaseModel):
    role: str
    label: str  # "IA locale" / "IA via clé API"
    model: str  # model name only, never a key
    local: bool
    status: Status


class Component(BaseModel):
    label: str
    status: Status
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unreachable"]
    version: str
    ai_active: str
    ai_options: list[AiOption]
    search: Component
    texts: Component


@router.get("/health", response_model=HealthResponse)
def health(session: SessionDep) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
        db_ok = True
    except SQLAlchemyError:
        db_ok = False
    try:
        roles = LlmConfig.from_yaml(get_settings().llm_config_path).roles
    except (OSError, ValueError):
        roles = {}
    options = [_option(r, roles[r]) for r in SELECTABLE_ROLES if r in roles]
    embedding = roles.get("embedding")
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="ok" if db_ok else "unreachable",
        version="0.1.0",
        ai_active=active_role(session) if db_ok else get_settings().kb_role,
        ai_options=options,
        search=Component(label="Recherche sémantique", status=_status(embedding), detail=_name(embedding)),
        texts=_texts(session) if db_ok else Component(label="Textes officiels", status="unreachable", detail=""),
    )


class AiChoice(BaseModel):
    role: str


@router.put("/settings/ai", response_model=HealthResponse)
def choose_ai(body: AiChoice, session: SessionDep) -> HealthResponse:
    """Switches the generative AI between the local model and the hosted provider (confidential missions stay
    on the local model whatever is chosen here)."""
    if body.role not in SELECTABLE_ROLES:
        raise HTTPException(422, "Rôle inconnu.")
    set_active_role(session, body.role)
    return health(session)


def _option(role: str, cfg: RoleConfig) -> AiOption:
    return AiOption(role=role, label="IA locale" if cfg.local else "IA via clé API", model=_name(cfg),
                    local=cfg.local, status=_status(cfg))


def _name(role: RoleConfig | None) -> str:
    return "non configuré" if role is None else role.model.split("/", 1)[-1]


def _status(role: RoleConfig | None) -> Status:
    """Local model: is the server answering? Hosted provider: is a key set? (no paid call to check it)."""
    if role is None:
        return "not_configured"
    if not role.local:
        return "ok" if role.api_key else "no_key"
    try:
        httpx.get(f"{role.api_base or 'http://ollama:11434'}/api/tags", timeout=1.5).raise_for_status()
    except httpx.HTTPError:
        return "unreachable"
    return "ok"


def _texts(session: Session) -> Component:
    count = session.scalar(select(func.count()).select_from(SourceDocument).where(SourceDocument.is_current)) or 0
    last = session.scalars(select(WatchCheck).order_by(WatchCheck.checked_at.desc())).first()
    if last is None:
        return Component(label="Textes officiels", status="ok", detail=f"{count} textes")
    outdated = sum(t["status"] == "nouvelle_version" for t in last.data["texts"])
    when = last.checked_at.strftime("%d/%m")
    if outdated:
        return Component(label="Textes officiels", status="unreachable",
                         detail=f"{count} textes · {outdated} à mettre à jour")
    return Component(label="Textes officiels", status="ok", detail=f"{count} textes · à jour au {when}")
