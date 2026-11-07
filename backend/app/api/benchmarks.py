from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.benchmark.collect import Template, collect, load_templates
from app.core.config import get_settings
from app.core.db import get_session
from app.core.models import Benchmark, Mission

router = APIRouter(prefix="/benchmarks", tags=["benchmark"])
SessionDep = Annotated[Session, Depends(get_session)]


def templates() -> dict[str, Template]:
    return load_templates(Path(get_settings().llm_config_path).parent / "benchmark_templates.yaml")


class TemplateOut(BaseModel):
    key: str
    title: str
    description: str


class BenchmarkIn(BaseModel):
    template: str
    mission_id: uuid.UUID | None = None


class BenchmarkOut(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID | None
    template: str
    created_at: datetime
    data: dict[str, Any]


def _out(b: Benchmark) -> BenchmarkOut:
    return BenchmarkOut(id=b.id, mission_id=b.mission_id, template=b.template, created_at=b.created_at, data=b.data)


@router.get("/templates", response_model=list[TemplateOut])
def list_templates() -> list[TemplateOut]:
    return [TemplateOut(key=k, title=t.title, description=t.description) for k, t in templates().items()]


@router.post("", response_model=BenchmarkOut, status_code=201)
def run_benchmark(body: BenchmarkIn, session: SessionDep) -> BenchmarkOut:
    tpl = templates().get(body.template)
    if tpl is None:
        raise HTTPException(404, "Gabarit inconnu")
    if body.mission_id and session.get(Mission, body.mission_id) is None:
        raise HTTPException(404, "Mission introuvable")
    try:
        data = collect(body.template, tpl)
    except Exception as exc:
        raise HTTPException(503, f"Source de données injoignable ({type(exc).__name__}).") from exc
    bench = Benchmark(mission_id=body.mission_id, template=body.template, data=data.model_dump())
    session.add(bench)
    session.commit()
    return _out(bench)


@router.get("", response_model=list[BenchmarkOut])
def list_benchmarks(session: SessionDep, mission_id: uuid.UUID | None = None) -> list[BenchmarkOut]:
    stmt = select(Benchmark).order_by(Benchmark.created_at.desc())
    if mission_id:
        stmt = stmt.where(Benchmark.mission_id == mission_id)
    return [_out(b) for b in session.scalars(stmt)]
