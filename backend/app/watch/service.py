"""Regulatory watch: new consolidated versions, article-level diff between versions, missions affected.

No model is involved: versions come from the Publications Office, diffs and impacts are computed in Python.
"""

from __future__ import annotations

import difflib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Literal, Protocol

import yaml
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Mission, Passage, SourceDocument
from app.corpus.cellar import candidates


class VersionLister(Protocol):
    def consolidated_versions(self, celex: str) -> list[str]: ...
    def is_available(self, celex: str) -> bool: ...


# --- 1. update check ----------------------------------------------------------------------------------


class TextStatus(BaseModel):
    code: str
    title: str
    current: str
    latest: str | None
    status: Literal["a_jour", "nouvelle_version", "non_consolide", "erreur"]
    detail: str = ""


class CheckResult(BaseModel):
    checked_at: str
    texts: list[TextStatus]


def _celex(version: str) -> str:
    return version.split("+", 1)[0]  # "<celex>+<hash>" when the same CELEX was re-issued


def check_updates(session: Session, lister: VersionLister, today: date, now: datetime) -> CheckResult:
    docs = session.scalars(select(SourceDocument).where(SourceDocument.is_current).order_by(SourceDocument.code))
    texts = []
    for d in docs:
        try:
            found = candidates(lister.consolidated_versions(d.original_celex), today)
        except Exception as exc:  # one unreachable text must not hide the others
            texts.append(TextStatus(code=d.code, title=d.title, current=_celex(d.version), latest=None,
                                    status="erreur", detail=type(exc).__name__))
            continue
        current = _celex(d.version)
        status: Literal["a_jour", "nouvelle_version", "non_consolide"] = "non_consolide" if not found else "a_jour"
        latest, detail = (found[0].celex if found else None), ""
        for v in found:  # newest first; stop at the version already in the database
            if v.celex == current:
                break
            if lister.is_available(v.celex):
                status, latest = "nouvelle_version", v.celex
                break
        else:
            if found:  # only listed versions without any published text: the stored text is still the latest
                detail = f"version consolidée {found[0].celex} référencée sans texte publié"
                latest = current
        texts.append(TextStatus(code=d.code, title=d.title, current=current, latest=latest, status=status,
                                detail=detail))
    return CheckResult(checked_at=now.isoformat(timespec="seconds"), texts=texts)


# --- 2. diff between two versions ---------------------------------------------------------------------


class Segment(BaseModel):
    op: Literal["equal", "insert", "delete"]
    text: str


class Change(BaseModel):
    ref: str
    heading: str
    kind: Literal["ajoute", "modifie", "supprime"]
    segments: list[Segment]  # word-level diff, old -> new


class VersionDiff(BaseModel):
    code: str
    title: str
    old_version: str
    new_version: str
    changes: list[Change]
    unchanged: int


_TOKENS = re.compile(r"\s+|\S+\s*")  # a word keeps its trailing space, so changes read as phrases


def word_diff(old: str, new: str) -> list[Segment]:
    a, b = _TOKENS.findall(old), _TOKENS.findall(new)
    out: list[Segment] = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            out.append(Segment(op="equal", text="".join(a[i1:i2])))
            continue
        if i2 > i1:
            out.append(Segment(op="delete", text="".join(a[i1:i2])))
        if j2 > j1:
            out.append(Segment(op="insert", text="".join(b[j1:j2])))
    return out


def diff_passages(old: list[Passage], new: list[Passage]) -> tuple[list[Change], int]:
    """Compares two versions passage by passage (stable refs). Recitals come from the original act: skipped."""
    before = {p.ref: p for p in old if p.kind != "recital"}
    after = {p.ref: p for p in new if p.kind != "recital"}
    changes: list[Change] = []
    unchanged = 0
    for p in sorted(after.values(), key=lambda p: p.position):
        prev = before.get(p.ref)
        if prev is None:
            changes.append(Change(ref=p.ref, heading=p.heading, kind="ajoute",
                                  segments=[Segment(op="insert", text=p.text)]))
        elif " ".join(prev.text.split()) != " ".join(p.text.split()):
            changes.append(Change(ref=p.ref, heading=p.heading, kind="modifie", segments=word_diff(prev.text, p.text)))
        else:
            unchanged += 1
    for p in sorted(before.values(), key=lambda p: p.position):
        if p.ref not in after:
            changes.append(Change(ref=p.ref, heading=p.heading, kind="supprime",
                                  segments=[Segment(op="delete", text=p.text)]))
    return changes, unchanged


def versions_with_history(session: Session) -> list[str]:
    docs = session.scalars(select(SourceDocument.code)).all()
    return sorted({c for c in docs if docs.count(c) > 1})


def diff_latest(session: Session, code: str) -> VersionDiff | None:
    """Current version vs the most recent older version kept in the database."""
    docs = session.scalars(select(SourceDocument).where(SourceDocument.code == code)).all()
    current = next((d for d in docs if d.is_current), None)
    older = sorted((d for d in docs if not d.is_current), key=lambda d: _celex(d.version), reverse=True)
    if current is None or not older:
        return None
    changes, unchanged = diff_passages(older[0].passages, current.passages)
    return VersionDiff(code=code, title=current.title, old_version=_celex(older[0].version),
                       new_version=_celex(current.version), changes=changes, unchanged=unchanged)


# --- 3. missions affected -----------------------------------------------------------------------------


class Impact(BaseModel):
    mission_id: str
    client: str
    cited: list[str]  # passages of this text cited in the mission's regulation analysis
    changed: list[str]  # those among them that changed (empty: the analysis is still up to date)


def cited_refs(regulation: dict[str, object] | None) -> set[str]:
    if not regulation:
        return set()
    textes = regulation.get("textes", [])
    assert isinstance(textes, list)
    return {c["ref"] for t in textes for o in t.get("obligations", []) for c in o.get("citations", [])}


def is_affected(ref: str, changed: set[str]) -> bool:
    """A cited paragraph is affected when it, or one of its sub-points, changed."""
    return any(c == ref or c.startswith(ref + "-") for c in changed)


def impacted_missions(session: Session, diff: VersionDiff) -> list[Impact]:
    """Every mission whose analysis cites this text, with the cited passages that changed."""
    changed = {c.ref for c in diff.changes}
    out = []
    for m in session.scalars(select(Mission).order_by(Mission.client)):
        cited = sorted(r for r in cited_refs(m.regulation) if r.split("-", 1)[0] == diff.code)
        if cited:
            out.append(Impact(mission_id=str(m.id), client=m.client, cited=cited,
                              changed=[r for r in cited if is_affected(r, changed)]))
    return out


def texts_cited_by_missions(session: Session) -> dict[str, list[str]]:
    """Text code -> clients whose regulation analysis cites it (to show who watches what)."""
    out: dict[str, set[str]] = {}
    for m in session.scalars(select(Mission)):
        for ref in cited_refs(m.regulation):
            out.setdefault(ref.split("-", 1)[0], set()).add(m.client)
    return {k: sorted(v) for k, v in out.items()}


# --- 4. deadlines -------------------------------------------------------------------------------------


class Deadline(BaseModel):
    date: date
    code: str
    title: str
    detail: str
    ref: str  # passage that sets the date, checked against the corpus


def load_deadlines(path: Path) -> list[Deadline]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return sorted((Deadline.model_validate(d) for d in data["deadlines"]), key=lambda d: d.date)
