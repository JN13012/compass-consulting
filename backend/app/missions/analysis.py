"""Mission analyses: diagnostic -> solutions -> regulation.

Guard rails (SPEC §3.3-3.5):
- diagnostic: each pain point quotes the interview notes; the quote is checked in code (`source_verifiee`);
- solutions: the "do you need a blockchain?" verdict is computed in code from the model's answers, not trusted;
- regulation: every obligation must cite passages that were actually retrieved; others are dropped.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Confidentiality, Mission, SourceDocument
from app.llm.router import LlmRouter
from app.llm.structured import complete_json
from app.retrieval.search import Embedder, Hit, search

PROMPTS = Path(__file__).parent / "prompts"


def _prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


GENERIC_AXES = ["Données", "Outils et ERP", "Intégrations / API", "Compétences", "Gouvernance"]
CYBER_AXES = ["Gouverner", "Identifier", "Protéger", "Détecter", "Répondre", "Rétablir"]  # NIST CSF 2.0


def maturity_axes(focus: list[str]) -> list[str]:
    return GENERIC_AXES + ([f"Cyber - {a}" for a in CYBER_AXES] if "cyber" in focus else [])


# --- Diagnostic ----------------------------------------------------------------------------------


class Process(BaseModel):
    nom: str
    description: str
    outils: list[str] = []
    volume: str = ""


class Irritant(BaseModel):
    id: str
    titre: str
    description: str
    impact: Literal["élevé", "moyen", "faible"]
    source: str
    source_verifiee: bool = False


class Maturity(BaseModel):
    axe: str
    note: int = Field(ge=1, le=3)
    justification: str


class Diagnostic(BaseModel):
    synthese: str
    processus: list[Process]
    irritants: list[Irritant]
    maturite: list[Maturity]


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace("’", "'").replace("«", '"').replace("»", '"')
    return " ".join(text.split()).strip(" .\"'")


def quote_found(quote: str, notes: str) -> bool:
    q = _norm(quote)
    return len(q) >= 12 and q in _norm(notes)


def run_diagnostic(mission: Mission, router: LlmRouter, role: str) -> Diagnostic:
    axes = maturity_axes(mission.focus)
    user = (
        f"Client : {mission.client} - {mission.sector}\nContexte : {mission.context}\n"
        f"Axes de maturité à noter : {', '.join(axes)}\n\nNotes d'entretien :\n{mission.notes}"
    )
    diag = complete_json(router, role, _prompt("diagnostic"), user, Diagnostic, mission.confidentiality,
                         str(mission.id))
    for irritant in diag.irritants:
        irritant.source_verifiee = quote_found(irritant.source, mission.notes)
    return diag


# --- Solutions -----------------------------------------------------------------------------------


class BlockchainCheck(BaseModel):
    plusieurs_parties: bool
    sans_confiance_mutuelle: bool
    registre_partage: bool
    actif_programmable: bool
    intermediaire_suffit: bool
    explication: str
    verdict: Literal["pertinente", "deconseillee"] | None = None


class Solution(BaseModel):
    irritant_id: str
    niveau: Literal["digitaliser", "automatiser", "cyber", "ia", "blockchain"]
    titre: str
    description: str
    gain: str
    cout: str
    delai: str
    risques: str
    horizon: Literal["quick_win", "moyen_terme", "long_terme"]
    verification_blockchain: BlockchainCheck | None = None


class Solutions(BaseModel):
    synthese: str
    solutions: list[Solution]


def blockchain_verdict(check: BlockchainCheck) -> Literal["pertinente", "deconseillee"]:
    """Classic decision grid: shared ledger between parties that do not trust each other, or a programmable
    asset, and no trusted intermediary that would do the job."""
    need = check.plusieurs_parties and check.sans_confiance_mutuelle and (
        check.registre_partage or check.actif_programmable
    )
    return "pertinente" if need and not check.intermediaire_suffit else "deconseillee"


def run_solutions(mission: Mission, diagnostic: Diagnostic, router: LlmRouter, role: str) -> Solutions:
    irritants = "\n".join(f"- {i.id} ({i.impact}) {i.titre} : {i.description}" for i in diagnostic.irritants)
    user = (
        f"Client : {mission.client} - {mission.sector}\nContexte : {mission.context}\n"
        f"Domaines de la mission : {', '.join(mission.focus)}\n\nIrritants :\n{irritants}\n\n"
        f"Notes d'entretien (pour les volumes et contraintes) :\n{mission.notes}"
    )
    sols = complete_json(router, role, _prompt("solutions"), user, Solutions, mission.confidentiality,
                         str(mission.id))
    known = {i.id for i in diagnostic.irritants}
    sols.solutions = [s for s in sols.solutions if s.irritant_id in known]
    for s in sols.solutions:
        if s.niveau == "blockchain" and s.verification_blockchain is None:
            s.verification_blockchain = BlockchainCheck(
                plusieurs_parties=False, sans_confiance_mutuelle=False, registre_partage=False,
                actif_programmable=False, intermediaire_suffit=True, explication="Grille non renseignée.",
            )
        if s.verification_blockchain is not None:
            s.verification_blockchain.verdict = blockchain_verdict(s.verification_blockchain)
    return sols


# --- Regulation ----------------------------------------------------------------------------------


class Applicability(BaseModel):
    code: str
    applicable: Literal["oui", "a_verifier", "non"]
    raisonnement: str


class ApplicabilityList(BaseModel):
    textes: list[Applicability]


class ObligationDraft(BaseModel):
    obligation: str
    statut: Literal["couvert", "manquant", "a_verifier"]
    justification: str
    passages: list[str]


class ObligationList(BaseModel):
    obligations: list[ObligationDraft]


class Citation(BaseModel):
    ref: str
    heading: str
    text: str
    url: str
    version: str
    consolidated: bool


class Obligation(BaseModel):
    obligation: str
    statut: Literal["couvert", "manquant", "a_verifier"]
    justification: str
    citations: list[Citation]


class TextAnalysis(BaseModel):
    code: str
    titre: str
    applicable: Literal["oui", "a_verifier", "non"]
    raisonnement: str
    obligations: list[Obligation] = []
    obligations_rejetees: int = 0  # dropped because they cited nothing valid


class Regulation(BaseModel):
    textes: list[TextAnalysis]
    ecartes: list[Applicability]


def _citation(hit: Hit) -> Citation:
    return Citation(ref=hit.ref, heading=hit.heading, text=hit.text, url=hit.url, version=hit.version,
                    consolidated=hit.consolidated)


def mission_summary(mission: Mission, diagnostic: Diagnostic | None, solutions: Solutions | None) -> str:
    parts = [f"Client : {mission.client} - {mission.sector}", f"Contexte : {mission.context}"]
    if diagnostic:
        parts.append("Irritants : " + "; ".join(i.titre for i in diagnostic.irritants))
    if solutions:
        parts.append("Solutions envisagées : " + "; ".join(f"{s.titre} ({s.niveau})" for s in solutions.solutions))
    parts.append(f"Notes :\n{mission.notes}")
    return "\n".join(parts)


def run_regulation(
    session: Session,
    mission: Mission,
    diagnostic: Diagnostic | None,
    solutions: Solutions | None,
    router: LlmRouter,
    role: str,
    embed: Embedder | None = None,
    max_texts: int = 5,
) -> Regulation:
    docs = session.scalars(select(SourceDocument).where(SourceDocument.is_current).order_by(SourceDocument.code))
    titles = {d.code: d.title for d in docs}
    summary = mission_summary(mission, diagnostic, solutions)
    listing = "\n".join(f"- {code} : {title}" for code, title in titles.items())
    applic = complete_json(router, role, _prompt("applicability"),
                           f"Textes disponibles :\n{listing}\n\nMission :\n{summary}",
                           ApplicabilityList, mission.confidentiality, str(mission.id))
    by_code = {a.code: a for a in applic.textes if a.code in titles}
    order = {"oui": 0, "a_verifier": 1, "non": 2}
    selected = sorted((a for a in by_code.values() if a.applicable != "non"),
                      key=lambda a: order[a.applicable])[:max_texts]

    analyses: list[TextAnalysis] = []
    for app_ in selected:
        query = f"obligations {titles[app_.code]} {mission.sector} {mission.context}"
        try:
            hits, _ = search(session, query, "vector" if embed else "fulltext", 10, None, embed,
                             sources=[app_.code])
        except Exception:  # embedding model unavailable -> keyword search
            hits, _ = search(session, query, "fulltext", 10, None, None, sources=[app_.code])
        hits_by_ref = {h.ref: h for h in hits}
        drafts = complete_json(
            router, role, _prompt("obligations"),
            f"Texte : {app_.code} - {titles[app_.code]}\n\nPassages :\n\n"
            + "\n\n".join(f"[{h.ref}] {h.heading}\n{h.text}" for h in hits)
            + f"\n\nMission :\n{summary}",
            ObligationList, mission.confidentiality, str(mission.id),
        )
        kept, rejected = [], 0
        for d in drafts.obligations:
            cites = [_citation(hits_by_ref[r]) for r in dict.fromkeys(d.passages) if r in hits_by_ref]
            if not cites:
                rejected += 1
                continue
            kept.append(Obligation(obligation=d.obligation, statut=d.statut, justification=d.justification,
                                   citations=cites))
        analyses.append(TextAnalysis(code=app_.code, titre=titles[app_.code], applicable=app_.applicable,
                                     raisonnement=app_.raisonnement, obligations=kept,
                                     obligations_rejetees=rejected))
    ecartes = [a for a in by_code.values() if a.applicable == "non"]
    return Regulation(textes=analyses, ecartes=ecartes)


def role_for(mission: Mission, default_role: str) -> str:
    """Confidential missions always run on the local model."""
    return "local" if mission.confidentiality is Confidentiality.CONFIDENTIAL else default_role
