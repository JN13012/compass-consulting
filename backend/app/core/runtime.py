"""Settings chosen from the interface, stored in the database (fallback: environment)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.models import AppSetting

SELECTABLE_ROLES = ("local", "reasoning")  # generative AI: local model or hosted provider


def active_role(session: Session) -> str:
    row = session.get(AppSetting, "ai_role")
    return row.value if row and row.value in SELECTABLE_ROLES else get_settings().kb_role


def set_active_role(session: Session, role: str) -> None:
    if role not in SELECTABLE_ROLES:
        raise ValueError(role)
    row = session.get(AppSetting, "ai_role")
    if row is None:
        session.add(AppSetting(key="ai_role", value=role))
    else:
        row.value = role
    session.commit()
