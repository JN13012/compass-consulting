from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_session
from app.core.models import WatchCheck
from app.corpus.cellar import CellarClient
from app.watch.service import (
    CheckResult,
    Deadline,
    Impact,
    VersionDiff,
    VersionLister,
    check_updates,
    diff_latest,
    impacted_missions,
    load_deadlines,
    texts_cited_by_missions,
    versions_with_history,
)

router = APIRouter(prefix="/watch", tags=["watch"])
SessionDep = Annotated[Session, Depends(get_session)]


def get_lister() -> VersionLister:
    return CellarClient()


class WatchStatus(BaseModel):
    last_check: CheckResult | None
    with_history: list[str]  # texts for which an older version is stored (diff available)
    cited_by: dict[str, list[str]]  # text code -> clients whose analysis cites it


class DiffOut(BaseModel):
    diff: VersionDiff
    impacts: list[Impact]


@router.get("/status", response_model=WatchStatus)
def status(session: SessionDep) -> WatchStatus:
    last = session.scalars(select(WatchCheck).order_by(WatchCheck.checked_at.desc())).first()
    return WatchStatus(last_check=CheckResult.model_validate(last.data) if last else None,
                       with_history=versions_with_history(session), cited_by=texts_cited_by_missions(session))


@router.post("/check", response_model=CheckResult)
def check(session: SessionDep, lister: Annotated[VersionLister, Depends(get_lister)]) -> CheckResult:
    now = datetime.now().astimezone()
    result = check_updates(session, lister, date.today(), now)
    session.add(WatchCheck(checked_at=now, data=result.model_dump()))
    session.commit()
    return result


@router.get("/diff/{code}", response_model=DiffOut)
def diff(code: str, session: SessionDep) -> DiffOut:
    result = diff_latest(session, code.upper())
    if result is None:
        raise HTTPException(404, "Aucune version antérieure conservée pour ce texte.")
    return DiffOut(diff=result, impacts=impacted_missions(session, result))


@router.get("/deadlines", response_model=list[Deadline])
def deadlines() -> list[Deadline]:
    return load_deadlines(Path(get_settings().llm_config_path).parent / "deadlines.yaml")
