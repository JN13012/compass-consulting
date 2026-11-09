from datetime import date

from app.core.models import Benchmark, Confidentiality, Mission
from app.deliverables.note import render_note


def mission(**kw: object) -> Mission:
    base: dict[str, object] = {"client": "Banque <Azur>", "sector": "Banque", "context": "ctx", "notes": "n",
                               "focus": ["blockchain"], "confidentiality": Confidentiality.CONFIDENTIAL,
                               "status": "ouverte"}
    return Mission(**{**base, **kw})


def test_empty_mission_lists_missing_steps_and_escapes() -> None:
    html = render_note(mission(), None, date(2026, 11, 7))
    assert "Banque &lt;Azur&gt;" in html and "<Azur>" not in html
    assert "CONFIDENTIEL" in html and "07/11/2026" in html
    assert html.count("non encore réalisée") == 5
    assert "ne constitue pas un avis juridique" in html


def test_citations_and_benchmark_rendered() -> None:
    regulation = {"ecartes": [{"code": "AIACT", "applicable": "non", "raisonnement": "r"}], "textes": [{
        "code": "MICA", "titre": "MiCA", "applicable": "oui", "raisonnement": "émet un EMT",
        "obligations": [{"obligation": "Publier un livre blanc", "statut": "manquant", "justification": "j",
                         "citations": [{"ref": "MICA-ART-51-1", "heading": "Article 51", "text": "Texte officiel",
                                        "url": "u", "version": "v", "consolidated": True}]}]}]}
    bench = Benchmark(template="eur", data={
        "title": "Stablecoins euro", "description": "d", "collected_at": "2026-11-07T10:00:00",
        "columns": [{"key": "token", "label": "Token"}],
        "rows": [{"key": "a", "cells": {"token": {"display": "EURC"}}}],
        "sources": [{"name": "DefiLlama", "url": "https://defillama.com"}]})
    html = render_note(mission(regulation=regulation), bench)
    assert "MICA-ART-51-1" in html and "Texte officiel" in html and "Manquant" in html
    assert "Textes écartés : AIACT" in html
    assert "EURC" in html and "DefiLlama" in html
    assert html.count("non encore réalisée") == 3


def test_poc_section_shows_verdict_and_corrections() -> None:
    poc = {
        "framing": {"nom": "Agent commandes", "solution_retenue": "Lecture des commandes", "objectif": "o",
                    "criteres": [{"metrique": "justesse_document", "seuil": 0.85}]},
        "evaluation": {"status": "terminee", "total": 30, "passage_echelle": False,
                       "verdict": [{"metrique": "justesse_document", "libelle": "Commandes entièrement justes",
                                    "seuil": 0.85, "valeur": 0.8, "ic95": [0.6, 0.91], "atteint": False}],
                       "corrections": ["Champ « date » faux dans 2 cas"]},
    }
    html = render_note(mission(poc=poc), None, date(2026, 11, 9))
    assert "Agent commandes" in html and "30 cas de test" in html and "pas encore" in html
    assert "80 %" in html and "60 % - 91 %" in html and "Champ « date » faux" in html
