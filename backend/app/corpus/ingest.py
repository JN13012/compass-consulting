"""Corpus ingestion: download -> hash -> parse -> store, idempotent and versioned.

- Same content as the current version (same SHA-256) -> nothing is rewritten.
- New content -> a new SourceDocument version is created; previous versions are kept (is_current=False).
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.models import Passage, SourceDocument
from app.corpus.cellar import Version, eurlex_url
from app.corpus.parser import PARSER_VERSION, ParsedPassage, parse_articles_and_annexes, parse_recitals
from app.corpus.sources import Source


class Fetcher(Protocol):
    def versions(self, celex: str, today: date) -> list[Version]: ...
    def fetch_xhtml(self, celex: str) -> bytes: ...


def fetch_best(fetcher: Fetcher, celex: str, today: date) -> tuple[Version, bytes, list[str]]:
    """First version that can actually be downloaded; returns skipped versions for the report."""
    skipped: list[str] = []
    last: Exception | None = None
    for version in fetcher.versions(celex, today):
        try:
            return version, fetcher.fetch_xhtml(version.celex), skipped
        except Exception as exc:
            skipped.append(version.celex)
            last = exc
    raise RuntimeError(f"no downloadable version for {celex}: {last}")


@dataclass
class SourceReport:
    code: str
    status: str  # new | updated | reparsed | unchanged | failed
    version: str = ""
    consolidated: bool = False
    counts: Counter[str] = field(default_factory=Counter)
    error: str = ""

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_passages(main: bytes, original: bytes, code: str) -> list[tuple[ParsedPassage, bool]]:
    """Articles/annexes from the version used; recitals from the original act. bool = from original."""
    body = parse_articles_and_annexes(main.decode("utf-8"), code)
    recitals = parse_recitals(original.decode("utf-8"), code)
    if not body:
        raise ValueError("no article found: unexpected document format")
    return [(p, False) for p in body] + [(p, True) for p in recitals]


def ingest_source(
    session: Session, source: Source, fetcher: Fetcher, raw_dir: Path, today: date
) -> SourceReport:
    report = SourceReport(code=source.code, status="failed")
    try:
        version, main, skipped = fetch_best(fetcher, source.celex, today)
        if skipped:
            report.error = f"versions indisponibles ignorées : {', '.join(skipped)}"
        original = main if not version.consolidated else fetcher.fetch_xhtml(source.celex)
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"{version.celex}.xhtml").write_bytes(main)
        (raw_dir / f"{source.celex}.xhtml").write_bytes(original)
        main_sha, orig_sha = sha256(main), sha256(original)
        report.version, report.consolidated = version.celex, version.consolidated

        existing = session.scalars(
            select(SourceDocument).where(SourceDocument.code == source.code)
        ).all()
        same = next(
            (d for d in existing if d.sha256 == main_sha and d.original_sha256 == orig_sha), None
        )
        if same is not None and same.parser_version == PARSER_VERSION:
            _set_current(session, source.code, same)
            session.commit()
            report.status = "unchanged"
            report.counts = Counter(
                session.scalars(select(Passage.kind).where(Passage.document_id == same.id)).all()
            )
            return report

        parsed = build_passages(main, original, source.code)
        if same is not None:  # same text, newer splitting rules: re-parse this version in place
            # Keep embeddings of passages whose content did not change (avoids recomputing them).
            kept = {(p.ref, p.heading, p.text): p.embedding for p in same.passages if p.embedding is not None}
            same.passages.clear()
            session.flush()
            rows = _to_rows(parsed, source.celex, version.celex)
            for row in rows:
                row.embedding = kept.get((row.ref, row.heading, row.text))
            same.passages = rows
            same.parser_version = PARSER_VERSION
            _set_current(session, source.code, same)
            session.commit()
            report.status = "reparsed"
            report.counts = Counter(p.kind for p, _ in parsed)
            return report
        version_key = version.celex
        if any(d.version == version_key for d in existing):  # same CELEX re-issued with new content
            version_key = f"{version.celex}+{main_sha[:8]}"
        doc = SourceDocument(
            code=source.code,
            title=source.title,
            url=eurlex_url(version.celex),
            domain=source.domain,
            version=version_key,
            consolidated=version.consolidated,
            original_celex=source.celex,
            original_url=eurlex_url(source.celex),
            consulted_on=today,
            sha256=main_sha,
            original_sha256=orig_sha,
            language="fr",
            is_current=True,
            parser_version=PARSER_VERSION,
        )
        doc.passages = _to_rows(parsed, source.celex, version.celex)
        session.add(doc)
        session.flush()
        _set_current(session, source.code, doc)
        session.commit()
        report.status = "updated" if existing else "new"
        report.counts = Counter(p.kind for p, _ in parsed)
    except Exception as exc:  # one failing source must not stop the others
        session.rollback()
        report.status, report.error = "failed", f"{type(exc).__name__}: {exc}"
    return report


def _to_rows(
    parsed: list[tuple[ParsedPassage, bool]], original_celex: str, version_celex: str
) -> list[Passage]:
    return [
        Passage(
            ref=p.ref,
            kind=p.kind,
            heading=p.heading,
            text=p.text,
            position=i,
            source_celex=original_celex if from_original else version_celex,
        )
        for i, (p, from_original) in enumerate(parsed)
    ]


def _set_current(session: Session, code: str, doc: SourceDocument) -> None:
    session.execute(
        update(SourceDocument)
        .where(SourceDocument.code == code, SourceDocument.id != doc.id)
        .values(is_current=False)
    )
    doc.is_current = True


def format_report(reports: list[SourceReport]) -> str:
    kinds = ["article", "paragraphe", "point", "considerant", "annexe"]
    header = f"{'source':<8} {'statut':<10} {'version':<22} " + " ".join(f"{k[:6]:>6}" for k in kinds)
    lines = [header + f" {'total':>6}", "-" * (len(header) + 7)]
    for r in reports:
        version = (r.version + (" (cons.)" if r.consolidated else ""))[:22]
        cells = " ".join(f"{r.counts.get(k, 0):>6}" for k in kinds)
        lines.append(f"{r.code:<8} {r.status:<10} {version:<22} {cells} {r.total:>6}")
        if r.error:
            lines.append(f"         {'!' if r.status == 'failed' else 'i'} {r.error}")
    failed = [r.code for r in reports if r.status == "failed"]
    lines.append("")
    summary = f"{len(reports) - len(failed)}/{len(reports)} sources OK"
    lines.append(summary + (f" — échecs : {failed}" if failed else ""))
    return "\n".join(lines)
