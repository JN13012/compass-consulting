from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.answering.service import AnswerSettings, answer_question
from app.core.config import get_settings
from app.core.db import get_session
from app.core.models import Passage, SourceDocument
from app.llm.router import LlmConfig, LlmRouter
from app.retrieval.search import Hit, Mode, search

router = APIRouter(prefix="/kb", tags=["base de connaissances"])


@lru_cache
def get_router() -> LlmRouter:
    return LlmRouter(LlmConfig.from_yaml(get_settings().llm_config_path))


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    domains: list[str] | None = None
    mode: Mode = "hybrid"


class PassageOut(BaseModel):
    ref: str
    kind: str
    heading: str
    text: str
    source_code: str
    source_title: str
    domain: str
    url: str
    version: str
    consolidated: bool
    consulted_on: date
    original_url: str
    score: float

    @classmethod
    def of(cls, hit: Hit) -> PassageOut:
        return cls(**{k: getattr(hit, k) for k in cls.model_fields})


class AskResponse(BaseModel):
    status: Literal["answered", "refused"]
    answer: str
    refusal_reason: str | None
    refusal_message: str | None
    citations: list[PassageOut]
    retrieved: list[PassageOut]
    mode_used: Mode
    model: str | None
    duration_s: float


class SearchResponse(BaseModel):
    passages: list[PassageOut]
    mode_used: Mode


class SourceOut(BaseModel):
    code: str
    title: str
    domain: str
    version: str
    consolidated: bool
    consulted_on: date
    url: str
    original_url: str
    passages: int


SessionDep = Annotated[Session, Depends(get_session)]
RouterDep = Annotated[LlmRouter, Depends(get_router)]


def _embedder(llm: LlmRouter):  # type: ignore[no-untyped-def]
    return lambda q: llm.embed([q])[0]


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, session: SessionDep, llm: RouterDep) -> AskResponse:
    s = get_settings()
    settings = AnswerSettings(role=s.kb_role, mode=body.mode, min_score=s.kb_min_score)
    try:
        ans = answer_question(session, llm, body.question, settings, body.domains, _embedder(llm))
    except Exception as exc:  # provider unreachable, missing key…
        raise HTTPException(
            status_code=503,
            detail=f"Fournisseur IA indisponible ({type(exc).__name__}). La recherche seule reste disponible.",
        ) from exc
    return AskResponse(
        status=ans.status,
        answer=ans.answer,
        refusal_reason=ans.refusal_reason,
        refusal_message=ans.refusal_message,
        citations=[PassageOut.of(h) for h in ans.citations],
        retrieved=[PassageOut.of(h) for h in ans.retrieved],
        mode_used=ans.mode_used,
        model=ans.model,
        duration_s=round(ans.duration_s, 2),
    )


@router.post("/search", response_model=SearchResponse)
def search_passages(body: AskRequest, session: SessionDep, llm: RouterDep) -> SearchResponse:
    """Retrieval only (no generation): always available, even without an AI provider."""
    try:
        hits, mode_used = search(session, body.question, body.mode, 10, body.domains, _embedder(llm))
    except Exception:
        hits, mode_used = search(session, body.question, "fulltext", 10, body.domains)
    return SearchResponse(passages=[PassageOut.of(h) for h in hits], mode_used=mode_used)


@router.get("/sources", response_model=list[SourceOut])
def sources(session: SessionDep) -> list[SourceOut]:
    count = func.count(Passage.id).label("n")
    rows = session.execute(
        select(SourceDocument, count).join(Passage).where(SourceDocument.is_current)
        .group_by(SourceDocument.id).order_by(SourceDocument.domain, SourceDocument.code)
    ).all()
    return [
        SourceOut(
            code=d.code, title=d.title, domain=d.domain, version=d.version, consolidated=d.consolidated,
            consulted_on=d.consulted_on, url=d.url, original_url=d.original_url, passages=n,
        )
        for d, n in rows
    ]
