"""POC - order-processing agent for Maison Lumen (built from the Compass dossier, evaluated by Compass).

Contract (INTERFACE.md): POST /run {"input": "<e-mail text>"} -> {"output": {...}} or {"output": {"refus": "..."}}.

The model only reads the e-mail and maps products to catalogue references. Everything that can be checked or
computed is done in code: unknown references are refused, prices come from the catalogue, the total is a sum.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

import litellm
from fastapi import FastAPI
from pydantic import BaseModel, ValidationError

HERE = Path(__file__).parent
CATALOG = {p["reference"]: p for p in json.loads((HERE / "catalog.json").read_text("utf-8"))}
PROMPT = (HERE / "prompt.md").read_text("utf-8").replace(
    "{catalogue}", "\n".join(f"- {r} : {p['designation']}" for r, p in CATALOG.items())
)

app = FastAPI(title="POC commandes Maison Lumen")


class RunIn(BaseModel):
    input: str


class Line(BaseModel):
    reference: str
    quantite: int


class Extraction(BaseModel):
    client: str | None = None
    date_livraison: str | None = None
    lignes: list[Line] = []
    refus: str | None = None


def _llm(text: str) -> str:
    params: dict[str, Any] = {
        "model": os.environ.get("POC_MODEL", "ollama_chat/qwen3.5:9b"),
        "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": text}],
        "temperature": 0,
    }
    if params["model"].startswith("ollama"):
        params["api_base"] = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
        params["think"] = False
    elif os.environ.get("AI_API_KEY"):
        params["api_key"] = os.environ["AI_API_KEY"]
    return litellm.completion(**params).choices[0].message.content or ""


def extract(text: str, llm: Any = _llm) -> Extraction:
    raw = llm(text)
    match = re.search(r"\{.*\}", raw.replace("```json", "").replace("```", ""), re.S)
    try:
        return Extraction.model_validate(json.loads(match.group(0) if match else ""))
    except (json.JSONDecodeError, ValidationError):
        return Extraction(refus="réponse du modèle illisible")


def sent_date(text: str) -> date | None:
    m = re.search(r"^Date : (\d{2})/(\d{2})/(\d{4})", text, re.M)
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def next_occurrence(due: date, sent: date | None) -> date:
    """A delivery date cannot be before the e-mail: '2 janvier' written in November is next year (computed here,
    not left to the model - iteration 2 after Compass's report)."""
    while sent and due < sent:
        due = due.replace(year=due.year + 1)
    return due


def to_order(e: Extraction, text: str = "") -> dict[str, Any]:
    if e.refus:
        return {"refus": e.refus}
    if not e.client or e.client.strip().lower() in {"client", "inconnu", "non précisé"}:
        return {"refus": "client non identifié"}
    try:
        due = next_occurrence(date.fromisoformat(e.date_livraison or ""), sent_date(text))
    except ValueError:
        return {"refus": "date de livraison absente ou illisible"}
    if not e.lignes or any(line.quantite <= 0 for line in e.lignes):
        return {"refus": "aucune ligne ou quantité invalide"}
    unknown = [line.reference for line in e.lignes if line.reference not in CATALOG]
    if unknown:
        return {"refus": f"références hors catalogue : {', '.join(unknown)}"}
    lignes = [{"reference": line.reference, "quantite": line.quantite,
               "prix_unitaire": CATALOG[line.reference]["prix_ht"]} for line in e.lignes]
    return {
        "client": e.client,
        "date_livraison": due.isoformat(),
        "lignes": lignes,
        "total_ht": round(sum(x["prix_unitaire"] * x["quantite"] for x in lignes), 2),
    }


@app.post("/run")
def run(body: RunIn) -> dict[str, Any]:
    return {"output": to_order(extract(body.input), body.input)}
