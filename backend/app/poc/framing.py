"""POC framing (SPEC §3.8 a): the model proposes, the code adds the mission's hard constraints and checks thresholds.

Compass does not build the POC: it frames it, hands a dossier to whoever builds it, then evaluates it.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from pydantic import BaseModel, field_validator

from app.core.models import Confidentiality, Mission
from app.llm.router import LlmRouter
from app.llm.structured import complete_json
from app.missions.analysis import Diagnostic, Solutions, mission_summary
from app.poc.bench import LOWER_IS_BETTER, METRIC_LABELS, Case, Criterion

PROMPTS = Path(__file__).parent / "prompts"


class Framing(BaseModel):
    nom: str
    solution_retenue: str
    objectif: str
    perimetre: list[str]
    hors_perimetre: list[str] = []
    user_stories: list[str]
    donnees: str
    architecture: list[str] = []
    criteres: list[Criterion]
    risques: list[str] = []
    contraintes: list[str] = []  # set by the code from the mission, never by the model

    @field_validator("criteres")
    @classmethod
    def _thresholds(cls, criteres: list[Criterion]) -> list[Criterion]:
        for c in criteres:
            if c.metrique != "latence_p95_s" and not 0 <= c.seuil <= 1:
                raise ValueError(f"seuil hors [0, 1] pour {c.metrique}")
            if c.metrique == "latence_p95_s" and c.seuil <= 0:
                raise ValueError("latence : seuil positif attendu")
        return criteres


def constraints(mission: Mission) -> list[str]:
    out = ["Données de test fictives ou anonymisées ; aucune donnée personnelle réelle dans le dépôt du POC.",
           "Un humain valide chaque sortie avant tout effet réel (ERP, envoi, paiement).",
           "Le POC refuse plutôt que deviner : un cas ambigu doit renvoyer {\"refus\": \"raison\"}."]
    if mission.confidentiality is Confidentiality.CONFIDENTIAL:
        out.insert(0, "Mission confidentielle : modèle local uniquement (Ollama), aucun appel à une API externe.")
    for t in (mission.regulation or {}).get("textes", []):
        if t.get("applicable") in ("oui", "a_verifier"):
            flag = "" if t["applicable"] == "oui" else " (applicabilité à vérifier)"
            out.append(f"{t['code']} - {t['titre']}{flag} : voir l'onglet Réglementation de la mission.")
    return out


def run_framing(mission: Mission, router: LlmRouter, role: str) -> Framing:
    diagnostic = Diagnostic.model_validate(mission.diagnostic) if mission.diagnostic else None
    solutions = Solutions.model_validate(mission.solutions) if mission.solutions else None
    user = mission_summary(mission, diagnostic, solutions)
    if solutions:
        user += "\n\nSolutions détaillées :\n" + "\n".join(
            f"- {s.titre} ({s.niveau}, {s.horizon}) : {s.description} Gain : {s.gain}" for s in solutions.solutions)
    framing = complete_json(router, role, (PROMPTS / "framing.md").read_text("utf-8"), user, Framing,
                            mission.confidentiality, str(mission.id))
    framing.contraintes = constraints(mission)
    return framing


# --- Dossier for the POC builder (zip) -----------------------------------------------------------


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items) or "- (aucun)"


def _criteria_table(criteres: list[Criterion]) -> str:
    rows = [f"| {METRIC_LABELS[c.metrique]} (`{c.metrique}`) | {'≤' if c.metrique in LOWER_IS_BETTER else '≥'} "
            f"{c.seuil:g} | {c.justification} |" for c in criteres]
    return "| Critère | Seuil | Pourquoi |\n|---|---|---|\n" + "\n".join(rows)


def dossier_files(mission: Mission, f: Framing, dev_cases: list[Case], n_test: int) -> dict[str, str]:
    cases = "".join(c.model_dump_json() + "\n" for c in dev_cases)
    return {
        "CLAUDE.md": (
            f"# POC {f.nom} - {mission.client}\n\nDossier produit par Compass. Lire `SPEC.md`, puis `INTERFACE.md`.\n\n"
            f"## Contexte\n{mission.context}\n\n## Règles non négociables\n{_bullets(f.contraintes)}\n\n"
            "## Méthode\n- Régler le POC uniquement sur `eval/cases.jsonl` (jeu de développement).\n"
            f"- Compass garde un jeu de test séparé ({n_test} cas) qu'il ne transmet pas : c'est lui qui décide.\n"
        ),
        "SPEC.md": (
            f"# {f.nom}\n\n**Solution retenue :** {f.solution_retenue}\n\n## Objectif\n{f.objectif}\n\n"
            f"## Périmètre\n{_bullets(f.perimetre)}\n\n## Hors périmètre\n{_bullets(f.hors_perimetre)}\n\n"
            f"## User stories\n{_bullets(f.user_stories)}\n\n## Critères d'acceptation\n{_criteria_table(f.criteres)}"
            f"\n\n## Données\n{f.donnees}\n\n## Risques\n{_bullets(f.risques)}\n"
        ),
        "ARCHITECTURE.md": f"# Architecture proposée\n\n{_bullets(f.architecture)}\n",
        "INTERFACE.md": (
            "# Contrat d'évaluation\n\nLe POC expose une route HTTP :\n\n```\nPOST /run\n{\"input\": \"<texte>\"}\n"
            "→ {\"output\": {<champs>}}\n→ {\"output\": {\"refus\": \"<raison>\"}}  (un humain doit trancher)\n```\n\n"
            "Les champs attendus sont ceux de `expected` dans `eval/cases.jsonl` ; des champs en plus sont acceptés.\n"
        ),
        "eval/README.md": (
            "# Évaluation\n\n`cases.jsonl` : une ligne par cas, `{\"id\", \"input\", \"expected\"}` ; `expected = null`"
            " signifie que le POC doit refuser.\n\nComparaison champ par champ : texte sans casse ni espaces, nombres "
            "au centime, listes sans ordre.\nChaque taux est donné avec son intervalle de confiance à 95 % (Wilson)."
            f"\n\n{_criteria_table(f.criteres)}\n"
        ),
        "eval/cases.jsonl": cases,
    }


def dossier_zip(mission: Mission, f: Framing, dev_cases: list[Case], n_test: int) -> bytes:
    slug = "".join(ch if ch.isalnum() else "-" for ch in f.nom.lower()).strip("-").removeprefix("poc-")[:40] or "poc"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in dossier_files(mission, f, dev_cases, n_test).items():
            z.writestr(f"poc-{slug}/{name}", content)
        z.writestr(f"poc-{slug}/framing.json", json.dumps(f.model_dump(), ensure_ascii=False, indent=2))
    return buffer.getvalue()
