"""Mission note: a print-ready HTML document built only from stored, validated results (SPEC §3.10).

The browser turns it into a PDF ("Imprimer > Enregistrer en PDF"); no model is called here.
"""

from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

from app.core.models import Benchmark, Mission

LEVELS = {"digitaliser": "Digitaliser", "automatiser": "Automatiser", "cyber": "Cybersécurité",
          "ia": "IA", "blockchain": "Blockchain"}
HORIZONS = {"quick_win": "Gain rapide", "moyen_terme": "Moyen terme", "long_terme": "Long terme"}
STATUS = {"couvert": "Couvert", "manquant": "Manquant", "a_verifier": "À vérifier"}
APPLICABLE = {"oui": "Applicable", "a_verifier": "À vérifier", "non": "Non applicable"}

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: Georgia, 'Times New Roman', serif; color: #1a1a1a; font-size: 10.5pt; line-height: 1.45; }
h1 { font-size: 22pt; margin: 0 0 4pt; } h2 { font-size: 14pt; border-bottom: 1px solid #999;
padding-bottom: 3pt; margin-top: 22pt; page-break-after: avoid; } h3 { font-size: 11.5pt; margin: 12pt 0 4pt; }
.meta { color: #555; font-size: 9.5pt; } .cover { border-bottom: 3px solid #1a1a1a; padding-bottom: 10pt; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 6pt 0; }
th, td { border: 1px solid #ccc; padding: 3pt 5pt; text-align: left; vertical-align: top; }
th { background: #f0eee8; } blockquote { margin: 4pt 0 4pt 10pt; padding-left: 8pt; border-left: 2px solid #aaa;
color: #333; font-size: 9pt; } .ref { font-family: monospace; font-size: 8.5pt; color: #555; }
.empty { color: #777; font-style: italic; } .warn { border: 1px solid #c9a227; background: #fbf6e3; padding: 6pt 8pt;
font-size: 9pt; margin-top: 10pt; } .item { page-break-inside: avoid; margin-bottom: 8pt; }
"""

DISCLAIMER = ("Document d'aide à la décision produit par Compass. Il ne constitue pas un avis juridique : "
              "les obligations et qualifications doivent être validées par un juriste. Les extraits de textes "
              "officiels sont relus depuis la base documentaire, jamais générés par le modèle.")


def _e(value: Any) -> str:
    return escape(str(value or ""))


def _missing(step: str) -> str:
    return f'<p class="empty">Étape « {step} » non encore réalisée pour cette mission.</p>'


def _diagnostic(d: dict[str, Any] | None) -> str:
    if not d:
        return _missing("diagnostic")
    irritants = "".join(
        f'<div class="item"><strong>{_e(i["titre"])}</strong> - impact {_e(i["impact"])}<br>{_e(i["description"])}'
        f'<blockquote>« {_e(i["source"])} »{"" if i.get("source_verifiee") else " (citation non retrouvée)"}'
        f"</blockquote></div>"
        for i in d.get("irritants", [])
    )
    maturity = "".join(f"<tr><td>{_e(m['axe'])}</td><td>{m['note']}/3</td><td>{_e(m['justification'])}</td></tr>"
                       for m in d.get("maturite", []))
    return (f"<p>{_e(d.get('synthese'))}</p><h3>Irritants</h3>{irritants or _missing('irritants')}"
            f"<h3>Maturité</h3><table><tr><th>Axe</th><th>Note</th><th>Justification</th></tr>{maturity}</table>")


def _solutions(s: dict[str, Any] | None) -> str:
    if not s:
        return _missing("solutions")
    rows = []
    for x in s.get("solutions", []):
        check = x.get("verification_blockchain")
        verdict = ""
        if check:
            label = "pertinente" if check.get("verdict") == "pertinente" else "déconseillée"
            verdict = f"<br><em>Blockchain {label} : {_e(check.get('explication'))}</em>"
        rows.append(f"<tr><td>{_e(LEVELS.get(x['niveau'], x['niveau']))}</td><td><strong>{_e(x['titre'])}</strong>"
                    f"<br>{_e(x['description'])}{verdict}</td><td>{_e(x['gain'])}</td><td>{_e(x['cout'])}</td>"
                    f"<td>{_e(x['delai'])}</td><td>{_e(HORIZONS.get(x['horizon'], x['horizon']))}</td></tr>")
    return (f"<p>{_e(s.get('synthese'))}</p><table><tr><th>Niveau</th><th>Solution</th><th>Gain</th><th>Coût</th>"
            f"<th>Délai</th><th>Horizon</th></tr>{''.join(rows)}</table>")


def _regulation(r: dict[str, Any] | None) -> str:
    if not r:
        return _missing("réglementation")
    parts = []
    for t in r.get("textes", []):
        obligations = "".join(
            f'<div class="item"><strong>{_e(STATUS.get(o["statut"], o["statut"]))}</strong> - {_e(o["obligation"])}'
            f"<br>{_e(o['justification'])}"
            + "".join(f'<blockquote><span class="ref">{_e(c["ref"])} · {_e(c["heading"])}</span><br>{_e(c["text"])}'
                      f"</blockquote>" for c in o.get("citations", []))
            + "</div>"
            for o in t.get("obligations", [])
        )
        parts.append(f"<h3>{_e(t['titre'])} - {_e(APPLICABLE.get(t['applicable'], t['applicable']))}</h3>"
                     f"<p>{_e(t['raisonnement'])}</p>{obligations}")
    later = ", ".join(_e(x["code"]) for x in r.get("non_analyses", []))
    if later:
        parts.append(f'<p class="meta">Textes applicables non détaillés (moins prioritaires) : {later}.</p>')
    discarded = ", ".join(_e(x["code"]) for x in r.get("ecartes", []))
    if discarded:
        parts.append(f'<p class="meta">Textes écartés : {discarded}.</p>')
    return "".join(parts) or _missing("réglementation")


def _benchmark(b: Benchmark | None) -> str:
    if b is None:
        return _missing("benchmark")
    data = b.data
    cols = data["columns"]
    head = "".join(f"<th>{_e(c['label'])}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{_e(r['cells'].get(c['key'], {}).get('display'))}</td>" for c in cols)
                   + "</tr>" for r in data["rows"])
    sources = " · ".join(f"{_e(s['name'])} ({_e(s['url'])})" for s in data["sources"])
    return (f"<p>{_e(data['title'])} - {_e(data['description'])}</p><table><tr>{head}</tr>{body}</table>"
            f'<p class="meta">Collecté le {_e(data["collected_at"][:10])}. Sources : {sources}.</p>')


def render_note(mission: Mission, benchmark: Benchmark | None, today: date | None = None) -> str:
    today = today or date.today()
    conf = " · CONFIDENTIEL" if mission.confidentiality.value == "confidentiel" else ""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Note de mission - {_e(mission.client)}</title><style>{CSS}</style></head><body>
<div class="cover"><p class="meta">Compass · Note de mission{conf}</p><h1>{_e(mission.client)}</h1>
<p class="meta">{_e(mission.sector)} - {_e(mission.context)}<br>Édité le {today.strftime("%d/%m/%Y")}</p></div>
<h2>1. Diagnostic</h2>{_diagnostic(mission.diagnostic)}
<h2>2. Solutions et feuille de route</h2>{_solutions(mission.solutions)}
<h2>3. Réglementation applicable</h2>{_regulation(mission.regulation)}
<h2>4. Benchmark</h2>{_benchmark(benchmark)}
<p class="warn">{DISCLAIMER}</p></body></html>"""
