"""Passage retrieval over the current corpus: full-text, vector, or hybrid (Reciprocal Rank Fusion).

Only passages of the *current* version of each source are searched.
Vector search is used only when embeddings exist; otherwise hybrid falls back to full-text.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.models import Passage, SourceDocument

Mode = Literal["fulltext", "vector", "hybrid"]
Embedder = Callable[[str], list[float]]

RRF_K = 60
_WORD = re.compile(r"[\wÀ-ÿ'’-]{2,}", re.UNICODE)


@dataclass(frozen=True)
class Hit:
    passage_id: uuid.UUID
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
    ranks: dict[str, int] = field(default_factory=dict)
    similarity: float | None = None  # cosine similarity to the question (vector / hybrid only)


# Question words carry no legal meaning; the 'french' config does not drop them all.
_QUESTION_WORDS = {
    "comment", "quel", "quelle", "quels", "quelles", "quand", "combien", "pourquoi", "est", "ce", "qu",
    "il", "elle", "ils", "elles", "faut", "doit", "doivent", "peut", "peuvent", "selon", "dans", "sont",
    "définit", "défini", "définie", "définition", "définir", "entend", "partir", "quoi", "lequel",
    "laquelle", "un", "une", "des", "les", "de", "du", "la", "le", "au", "aux", "en", "et", "ou",
}
_INVERSION = re.compile(r"-(t-)?(il|elle|ils|elles|on|ce)\b", re.I)
_DEFINITION_INTENT =re.compile(r"\b(défini\w*|définition|qu[’']est[- ]ce qu|on entend par|signifie)", re.I)

# Text names that may appear in a question -> restrict the search to that source.
SOURCE_ALIASES: dict[str, re.Pattern[str]] = {
    "MICA": re.compile(r"\bmica\b|marchés de crypto-actifs", re.I),
    "TFR": re.compile(r"\btfr\b|travel rule|transferts de fonds", re.I),
    "DAC": re.compile(r"\bdac\b(?!\s?8)|directive 2011/16", re.I),
    "DAC8": re.compile(r"\bdac\s?8\b", re.I),
    "DLT": re.compile(r"régime pilote|\bdlt pilot", re.I),
    "MIFID2": re.compile(r"\bmifid\b", re.I),
    "DORA": re.compile(r"\bdora\b", re.I),
    "NIS2": re.compile(r"\bnis\s?2\b", re.I),
    "CRA": re.compile(r"cyber resilience act|\bcra\b|cyber-résilience", re.I),
    "AMLR": re.compile(r"\bamlr\b", re.I),
    "AIACT": re.compile(r"\bai act\b|règlement (sur l[’'])?ia\b|intelligence artificielle", re.I),
    "RGPD": re.compile(r"\brgpd\b|\bgdpr\b", re.I),
    "ESPR": re.compile(r"\bespr\b|passeport numérique", re.I),
}


def detect_sources(question: str) -> list[str]:
    return [code for code, pattern in SOURCE_ALIASES.items() if pattern.search(question)]


def or_query(question: str) -> str:
    """Natural question -> OR tsquery over its meaningful words."""
    question = _INVERSION.sub("", question)  # "définit-il", "est-ce" -> "définit", "est"
    words = [w.strip("'’-").replace("'", " ").replace("’", " ") for w in _WORD.findall(question)]
    terms = sorted({t for w in words for t in w.split() if len(t) >= 2 and t.lower() not in _QUESTION_WORDS})
    terms = [t for t in terms if not any(p.fullmatch(t) for p in SOURCE_ALIASES.values())]
    return " | ".join(terms)


def _boost(hit: Hit, definition_intent: bool) -> float:
    factor = 0.75 if hit.kind == "considerant" else 1.0
    if definition_intent and "Définitions" in hit.heading:
        factor *= 1.5
    return hit.score * factor


def _base(domains: list[str] | None, sources: list[str] | None = None):  # type: ignore[no-untyped-def]
    stmt = select(Passage, SourceDocument).join(SourceDocument).where(SourceDocument.is_current)
    if domains:
        stmt = stmt.where(SourceDocument.domain.in_(domains))
    if sources:
        stmt = stmt.where(SourceDocument.code.in_(sources))
    return stmt


def fulltext(
    session: Session, question: str, limit: int, domains: list[str] | None = None,
    sources: list[str] | None = None,
) -> list[Hit]:
    query = or_query(question)
    if not query:
        return []
    tsq = func.to_tsquery("french", query)
    # Normalisation 32: rank / (rank + 1) -> score in [0, 1).
    rank = func.ts_rank_cd(text("passages.tsv"), tsq, 32).label("rank")
    stmt = (
        _base(domains, sources)
        .add_columns(rank)
        .where(text("passages.tsv @@ to_tsquery('french', :q)").bindparams(q=query))
        .order_by(rank.desc(), Passage.ref)
        .limit(max(limit * 5, 50))  # re-ranked below
    )
    raw = [_hit(p, d, float(r), {}) for p, d, r in session.execute(stmt)]
    definition_intent = bool(_DEFINITION_INTENT.search(question))
    ranked = sorted(raw, key=lambda h: (-_boost(h, definition_intent), h.ref))[:limit]
    return [
        _replace(h, score=_boost(h, definition_intent), ranks={"fulltext": i})
        for i, h in enumerate(ranked, 1)
    ]


def has_embeddings(session: Session) -> bool:
    stmt = (
        select(func.count()).select_from(Passage).join(SourceDocument)
        .where(SourceDocument.is_current, Passage.embedding.is_not(None))
    )
    return bool(session.scalar(stmt))


def vector(
    session: Session, question: str, limit: int, embed: Embedder, domains: list[str] | None = None,
    sources: list[str] | None = None,
) -> list[Hit]:
    qvec = embed(question)
    distance = Passage.embedding.cosine_distance(qvec).label("distance")
    stmt = (
        _base(domains, sources).add_columns(distance).where(Passage.embedding.is_not(None))
        .order_by(distance, Passage.ref).limit(limit)
    )
    return [
        _replace(_hit(p, d, 1.0 - float(dist), {"vector": i}), similarity=1.0 - float(dist))
        for i, (p, d, dist) in enumerate(session.execute(stmt), 1)
    ]


def rrf(*rankings: list[Hit], limit: int) -> list[Hit]:
    """Reciprocal Rank Fusion: score = sum(1 / (k + rank)). Keeps per-method ranks for explanations."""
    scores: dict[str, float] = {}
    best: dict[str, Hit] = {}
    ranks: dict[str, dict[str, int]] = {}
    sims: dict[str, float] = {}
    for ranking in rankings:
        for position, hit in enumerate(ranking, 1):
            scores[hit.ref] = scores.get(hit.ref, 0.0) + 1.0 / (RRF_K + position)
            best.setdefault(hit.ref, hit)
            ranks.setdefault(hit.ref, {}).update(hit.ranks)
            if hit.similarity is not None:
                sims[hit.ref] = hit.similarity
    ordered = sorted(scores, key=lambda r: (-scores[r], r))[:limit]
    return [_replace(best[r], score=scores[r], ranks=ranks[r], similarity=sims.get(r)) for r in ordered]


def best_similarity(hits: list[Hit]) -> float | None:
    values = [h.similarity for h in hits if h.similarity is not None]
    return max(values) if values else None


def search(
    session: Session,
    question: str,
    mode: Mode = "hybrid",
    limit: int = 8,
    domains: list[str] | None = None,
    embed: Embedder | None = None,
) -> tuple[list[Hit], Mode]:
    """Returns hits and the mode actually used (hybrid/vector degrade to fulltext without embeddings).

    A text named in the question (MiCA, NIS 2, AI Act…) restricts the search to that text.
    """
    sources = detect_sources(question) or None
    can_vector = embed is not None and has_embeddings(session)
    if mode == "fulltext" or not can_vector:
        return fulltext(session, question, limit, domains, sources), "fulltext"
    assert embed is not None
    if mode == "vector":
        return vector(session, question, limit, embed, domains, sources), "vector"
    pool = max(limit * 4, 30)
    fused = rrf(
        fulltext(session, question, pool, domains, sources),
        vector(session, question, pool, embed, domains, sources),
        limit=limit,
    )
    return fused, "hybrid"


def _hit(p: Passage, d: SourceDocument, score: float, ranks: dict[str, int]) -> Hit:
    from_consolidation = d.consolidated and p.source_celex != d.original_celex  # recitals: original act
    return Hit(
        passage_id=p.id, ref=p.ref, kind=p.kind, heading=p.heading, text=p.text,
        source_code=d.code, source_title=d.title, domain=d.domain,
        url=d.url if from_consolidation else d.original_url,
        version=p.source_celex, consolidated=from_consolidation,
        consulted_on=d.consulted_on, original_url=d.original_url, score=score, ranks=ranks,
    )


def _replace(hit: Hit, **changes: object) -> Hit:
    from dataclasses import replace

    return replace(hit, **changes)  # type: ignore[arg-type]
