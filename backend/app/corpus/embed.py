"""Compute embeddings for passages that do not have one yet (current versions only). Resumable."""

from __future__ import annotations

import time
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.models import EMBEDDING_DIM, Passage, SourceDocument

MAX_CHARS = 6000  # bge-m3 handles 8k tokens; keep inputs well below


def embedding_input(heading: str, text: str) -> str:
    """Heading gives context (article title, definition scope) that the bare text often lacks."""
    return f"{heading}\n{text}"[:MAX_CHARS]


def embed_missing(
    session: Session,
    embed: Callable[[list[str]], list[list[float]]],
    batch_size: int = 32,
    progress: Callable[[int, int], None] | None = None,
) -> int:
    pending = select(Passage).join(SourceDocument).where(SourceDocument.is_current, Passage.embedding.is_(None))
    total = session.scalar(select(func.count()).select_from(pending.subquery())) or 0
    done = 0
    while True:
        batch = list(session.scalars(pending.order_by(Passage.id).limit(batch_size)))
        if not batch:
            break
        vectors = embed([embedding_input(p.heading, p.text) for p in batch])
        if len(vectors) != len(batch) or any(len(v) != EMBEDDING_DIM for v in vectors):
            raise ValueError(f"unexpected embedding shape (expected {len(batch)} x {EMBEDDING_DIM})")
        for passage, vector in zip(batch, vectors, strict=True):
            passage.embedding = vector
        session.commit()
        done += len(batch)
        if progress:
            progress(done, total)
    return done


def run(session: Session, embed: Callable[[list[str]], list[list[float]]]) -> None:
    start = time.perf_counter()

    def show(done: int, total: int) -> None:
        print(f"\r  {done}/{total} passages", end="", flush=True)

    n = embed_missing(session, embed, progress=show)
    print(f"\n{n} passages vectorisés en {time.perf_counter() - start:.0f} s")
