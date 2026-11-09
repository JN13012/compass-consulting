"""Interview guide: hand-written question bank, answers stored per mission, compiled into interview notes."""

from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.core.models import Mission
from app.llm.router import LlmRouter
from app.llm.structured import complete_json

PROMPTS = Path(__file__).parent / "prompts"


class Question(BaseModel):
    id: str
    question: str
    but: str


class Theme(BaseModel):
    title: str
    questions: list[Question]


class Section(BaseModel):
    key: str
    title: str
    focus: str | None
    intro: str
    themes: list[Theme]
    observer: list[str] = []


class Interview(BaseModel):
    """What the consultant filled in: answers by question id, checked observation items by label."""

    answers: dict[str, str] = {}
    checked: list[str] = []


class FollowUp(BaseModel):
    question: str
    raison: str


class FollowUps(BaseModel):
    questions: list[FollowUp] = Field(max_length=6)


def load_guide(path: Path) -> list[Section]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    sections = [Section.model_validate(s) for s in data["sections"]]
    ids = [q.id for s in sections for t in s.themes for q in t.questions]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate question id in interview guide")
    return sections


def sections_for(guide: list[Section], focus: list[str]) -> list[Section]:
    return [s for s in guide if s.focus is None or s.focus in focus]


def compile_notes(sections: list[Section], interview: Interview) -> str:
    """Interview notes grouped by section and theme; only answered questions are kept, in the client's words."""
    out: list[str] = []
    for s in sections:
        block: list[str] = []
        for t in s.themes:
            answered = [(q, interview.answers.get(q.id, "").strip()) for q in t.questions]
            answered = [(q, a) for q, a in answered if a]
            if answered:
                block.append(f"{t.title} :")
                block += [f"- {q.question}\n  {a}" for q, a in answered]
        seen = [o for o in s.observer if o in interview.checked]
        if seen:
            block.append("Éléments consultés : " + " ; ".join(seen) + ".")
        if block:
            out.append(f"[{s.title}]\n" + "\n".join(block))
    return "\n\n".join(out)


def suggest_followups(router: LlmRouter, role: str, mission: Mission, sections: list[Section],
                      interview: Interview) -> FollowUps:
    notes = compile_notes(sections, interview) or "(aucune réponse saisie)"
    unanswered = [q.question for s in sections for t in s.themes for q in t.questions
                  if not interview.answers.get(q.id, "").strip()]
    user = (f"Client : {mission.client} ({mission.sector})\nContexte : {mission.context}\n\n"
            f"Réponses déjà recueillies :\n{notes}\n\nQuestions de la grille encore sans réponse :\n"
            + "\n".join(f"- {q}" for q in unanswered[:20]))
    system = (PROMPTS / "followups.md").read_text(encoding="utf-8")
    return complete_json(router, role, system, user, FollowUps, mission.confidentiality, str(mission.id))


CSS = """
@page { size: A4; margin: 15mm 14mm; }
body { font-family: Georgia, serif; color: #1a1a1a; font-size: 10pt; }
h1 { font-size: 18pt; margin: 0; } h2 { font-size: 13pt; border-bottom: 1px solid #999; margin-top: 16pt; }
h3 { font-size: 10.5pt; margin: 10pt 0 4pt; } .meta, .but { color: #555; font-size: 8.5pt; }
.q { page-break-inside: avoid; margin-bottom: 6pt; } .box { border: 1px solid #bbb; height: 46pt; margin-top: 3pt; }
ul { padding-left: 14pt; } li { margin: 2pt 0; }
"""


def render_blank(sections: list[Section], mission: Mission, today: date | None = None) -> str:
    """Printable blank interview grid, to take to the meeting."""
    today = today or date.today()
    e = escape
    body: list[str] = []
    for s in sections:
        body.append(f"<h2>{e(s.title)}</h2><p class='meta'>{e(s.intro)}</p>")
        for t in s.themes:
            body.append(f"<h3>{e(t.title)}</h3>")
            body += [f"<div class='q'><strong>{e(q.id)}.</strong> {e(q.question)}"
                     f"<div class='but'>Ce qu'on cherche : {e(q.but)}</div><div class='box'></div></div>"
                     for q in t.questions]
        if s.observer:
            body.append("<h3>À observer ou demander</h3><ul>"
                        + "".join(f"<li>☐ {e(o)}</li>" for o in s.observer) + "</ul>")
    return (f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>Grille d'entretien - "
            f"{e(mission.client)}</title><style>{CSS}</style></head><body>"
            f"<p class='meta'>Compass · Grille d'entretien</p><h1>{e(mission.client)}</h1>"
            f"<p class='meta'>{e(mission.sector)} - {e(mission.context)}<br>Date : ____ / ____ / ______ · "
            f"Interlocuteurs : ______________________________ · Édité le {today.strftime('%d/%m/%Y')}</p>"
            + "".join(body) + "</body></html>")
