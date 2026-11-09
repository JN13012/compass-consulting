from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_session
from app.llm.router import LlmConfig

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unreachable"]
    version: str
    ai_model: str  # model behind the default AI role (name only, never a key)


@router.get("/health", response_model=HealthResponse)
def health(session: Annotated[Session, Depends(get_session)]) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
        db_status: Literal["ok", "unreachable"] = "ok"
    except SQLAlchemyError:
        db_status = "unreachable"
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        database=db_status,
        version="0.1.0",
        ai_model=_ai_model(),
    )


def _ai_model() -> str:
    try:
        settings = get_settings()
        role = LlmConfig.from_yaml(settings.llm_config_path).roles[settings.kb_role]
    except (OSError, KeyError, ValueError):
        return "non configuré"
    return role.model.split("/", 1)[-1] + (" (local)" if role.local else "")
