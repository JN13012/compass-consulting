"""Structured (JSON) completions validated by a Pydantic schema, with one retry."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from app.core.models import Confidentiality
from app.llm.router import LlmRouter

_JSON = re.compile(r"\{.*\}", re.S)


class StructuredOutputError(ValueError):
    pass


def parse_json[T: BaseModel](raw: str, schema: type[T]) -> T | None:
    match = _JSON.search(raw.replace("```json", "").replace("```", ""))
    if not match:
        return None
    try:
        return schema.model_validate(json.loads(match.group(0)))
    except (json.JSONDecodeError, ValidationError):
        return None


def complete_json[T: BaseModel](
    router: LlmRouter,
    role: str,
    system: str,
    user: str,
    schema: type[T],
    confidentiality: Confidentiality,
    mission_id: str | None = None,
) -> T:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    last = ""
    for _ in range(2):
        result = router.complete(role, messages, confidentiality, mission_id=mission_id, temperature=0)
        last = result.content
        parsed = parse_json(last, schema)
        if parsed is not None:
            return parsed
        messages = [
            *messages,
            {"role": "assistant", "content": last},
            {"role": "user", "content": "Ta réponse n'est pas un JSON valide conforme au format demandé. "
                                        "Réponds UNIQUEMENT avec le JSON."},
        ]
    raise StructuredOutputError(f"invalid structured output: {last[:200]}")
