"""Cited answers with two-layer refusal.

Layer 1 (no model call): no passage scores above the relevance threshold -> refusal.
Layer 2: the model answers INSUFFISANT, returns invalid JSON twice, or cites an id that was not provided
-> refusal. The model only returns passage ids; displayed texts are always read back from the database.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.models import Confidentiality
from app.llm.router import LlmRouter
from app.retrieval.search import Embedder, Hit, Mode, search

PROMPT = (Path(__file__).parent / "prompts" / "answer.md").read_text(encoding="utf-8")
_JSON_OBJECT = re.compile(r"\{.*\}", re.S)

RefusalReason = Literal["aucun_passage_pertinent", "insuffisant", "citation_invalide", "reponse_invalide"]

REFUSAL_MESSAGES: dict[str, str] = {
    "aucun_passage_pertinent": "Les textes du corpus ne contiennent pas de passage suffisamment pertinent.",
    "insuffisant": "Les passages trouvés ne permettent pas de répondre avec certitude.",
    "citation_invalide": "La réponse générée citait un passage inexistant : elle a été rejetée.",
    "reponse_invalide": "La réponse générée était mal formée : elle a été rejetée.",
}


class ModelAnswer(BaseModel):
    statut: Literal["OK", "INSUFFISANT"]
    reponse: str = ""
    passages: list[str] = []


@dataclass(frozen=True)
class AnswerSettings:
    role: str = "reasoning"
    mode: Mode = "hybrid"
    top_k: int = 8
    min_score: float = 0.30  # layer-1 threshold on the best hit (tuned on the dev set, phase 1c)


@dataclass
class Answer:
    status: Literal["answered", "refused"]
    answer: str
    refusal_reason: RefusalReason | None
    citations: list[Hit]
    retrieved: list[Hit]
    mode_used: Mode
    model: str | None = None
    duration_s: float = 0.0
    attempts: int = 0
    raw: list[str] = field(default_factory=list)

    @property
    def refusal_message(self) -> str | None:
        return REFUSAL_MESSAGES[self.refusal_reason] if self.refusal_reason else None


def format_passages(hits: list[Hit]) -> str:
    return "\n\n".join(f"[{h.ref}] {h.heading}\n{h.text}" for h in hits)


def parse_model_output(raw: str) -> ModelAnswer | None:
    match = _JSON_OBJECT.search(raw.replace("```json", "").replace("```", ""))
    if not match:
        return None
    try:
        return ModelAnswer.model_validate(json.loads(match.group(0)))
    except (json.JSONDecodeError, ValidationError):
        return None


def answer_question(
    session: Session,
    router: LlmRouter,
    question: str,
    settings: AnswerSettings | None = None,
    domains: list[str] | None = None,
    embed: Embedder | None = None,
    confidentiality: Confidentiality = Confidentiality.PUBLIC,
) -> Answer:
    settings = settings or AnswerSettings()
    start = time.perf_counter()
    hits, mode_used = search(session, question, settings.mode, settings.top_k, domains, embed)

    def refuse(reason: RefusalReason, **extra: object) -> Answer:
        ans = Answer("refused", "", reason, [], hits, mode_used, **extra)  # type: ignore[arg-type]
        ans.duration_s = time.perf_counter() - start
        return ans

    if not hits or (mode_used == "fulltext" and hits[0].score < settings.min_score):
        return refuse("aucun_passage_pertinent")

    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": f"Passages :\n\n{format_passages(hits)}\n\nQuestion : {question}"},
    ]
    raws: list[str] = []
    parsed: ModelAnswer | None = None
    model: str | None = None
    for _ in range(2):  # one retry on malformed output
        result = router.complete(settings.role, messages, confidentiality, temperature=0)
        model = result.model
        raws.append(result.content)
        parsed = parse_model_output(result.content)
        if parsed is not None:
            break
    extra = {"model": model, "attempts": len(raws), "raw": raws}
    if parsed is None:
        return refuse("reponse_invalide", **extra)
    if parsed.statut == "INSUFFISANT":
        return refuse("insuffisant", **extra)
    by_ref = {h.ref: h for h in hits}
    if not parsed.passages or any(ref not in by_ref for ref in parsed.passages):
        return refuse("citation_invalide", **extra)

    citations = [by_ref[ref] for ref in dict.fromkeys(parsed.passages)]  # dedupe, keep order
    ans = Answer("answered", parsed.reponse.strip(), None, citations, hits, mode_used, **extra)  # type: ignore[arg-type]
    ans.duration_s = time.perf_counter() - start
    return ans
