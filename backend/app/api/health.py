from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_session
from app.llm.router import LlmConfig, RoleConfig

router = APIRouter(tags=["system"])

AiStatus = Literal["ok", "unreachable", "no_key", "not_configured"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unreachable"]
    version: str
    ai_model: str  # model that writes the answers (name only, never a key)
    ai_status: AiStatus
    search_model: str  # embedding model used for meaning-based search


@router.get("/health", response_model=HealthResponse)
def health(session: Annotated[Session, Depends(get_session)]) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
        db_status: Literal["ok", "unreachable"] = "ok"
    except SQLAlchemyError:
        db_status = "unreachable"
    settings = get_settings()
    try:
        roles = LlmConfig.from_yaml(settings.llm_config_path).roles
    except (OSError, ValueError):
        roles = {}
    answer, search = roles.get(settings.kb_role), roles.get("embedding")
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        database=db_status,
        version="0.1.0",
        ai_model=_name(answer),
        ai_status=_ai_status(answer),
        search_model=_name(search),
    )


def _name(role: RoleConfig | None) -> str:
    if role is None:
        return "non configuré"
    return role.model.split("/", 1)[-1] + (" (local)" if role.local else "")


def _ai_status(role: RoleConfig | None) -> AiStatus:
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
