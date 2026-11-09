"""POC evaluation bench (SPEC §3.8 b-d). Pure Python: comparisons, rates, Wilson intervals, verdict, report.

A case is {"id", "input", "expected"}; expected = null means the POC must refuse (a human has to be asked).
The POC answers {"output": {...}} or {"output": {"refus": "..."}} (INTERFACE.md).
"""

from __future__ import annotations

import json
import math
import random
import time
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel

from app.eval.metrics import normalize, wilson

Metric = Literal["justesse_document", "justesse_champs", "refus_corrects", "faux_refus", "latence_p95_s"]
LOWER_IS_BETTER: set[str] = {"faux_refus", "latence_p95_s"}
METRIC_LABELS: dict[str, str] = {
    "justesse_document": "Commandes entièrement justes",
    "justesse_champs": "Champs justes",
    "refus_corrects": "Cas ambigus correctement refusés",
    "faux_refus": "Refus à tort",
    "latence_p95_s": "Latence (95e centile, s)",
}


class Case(BaseModel):
    id: str
    input: str
    expected: dict[str, Any] | None
    note: str = ""


def parse_cases(jsonl: str) -> list[Case]:
    cases = [Case.model_validate_json(line) for line in jsonl.splitlines() if line.strip()]
    if len({c.id for c in cases}) != len(cases):
        raise ValueError("identifiants de cas en double")
    if not cases:
        raise ValueError("aucun cas")
    return cases


def split_cases(cases: list[Case], dev_share: float = 0.4, seed: int = 20261109) -> tuple[list[Case], list[Case]]:
    """Stratified (answer / refuse) deterministic split. Dev goes in the dossier; test stays in Compass."""
    rng = random.Random(seed)
    dev: list[Case] = []
    test: list[Case] = []
    for must_refuse in (False, True):
        pool = sorted((c for c in cases if (c.expected is None) is must_refuse), key=lambda c: c.id)
        rng.shuffle(pool)
        cut = round(len(pool) * dev_share)
        dev += pool[:cut]
        test += pool[cut:]
    return sorted(dev, key=lambda c: c.id), sorted(test, key=lambda c: c.id)


# --- Comparison ----------------------------------------------------------------------------------


def _canon(value: Any) -> Any:
    if isinstance(value, str):
        return normalize(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {k: _canon(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return sorted((_canon(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True, default=str))
    return value


def same(expected: Any, got: Any) -> bool:
    """Field equality: numbers to the cent, text without case/spacing, lists as multisets. In a list of objects,
    only the keys present in the expected objects are compared (extra keys like a unit price are allowed)."""
    if isinstance(expected, int | float) and isinstance(got, int | float) and not isinstance(got, bool):
        return math.isclose(float(expected), float(got), abs_tol=0.01)
    if isinstance(expected, list) and isinstance(got, list):
        if expected and all(isinstance(e, dict) for e in expected) and all(isinstance(g, dict) for g in got):
            keys = set().union(*(e.keys() for e in expected))
            got = [{k: g.get(k) for k in keys} for g in got]
        return bool(_canon(expected) == _canon(got))
    return bool(_canon(expected) == _canon(got))


class CaseResult(BaseModel):
    id: str
    must_refuse: bool
    status: Literal["reponse", "refus", "erreur"]
    fields_ok: dict[str, bool] = {}
    got: dict[str, Any] | None = None
    expected: dict[str, Any] | None = None
    detail: str = ""
    duration_s: float

    @property
    def label(self) -> str:
        if self.status == "erreur":
            return "erreur_technique"
        if self.must_refuse:
            return "refus_correct" if self.status == "refus" else "reponse_au_lieu_de_refus"
        if self.status == "refus":
            return "faux_refus"
        return "correct" if all(self.fields_ok.values()) else "champ_faux"


def judge(case: Case, output: Any, duration_s: float) -> CaseResult:
    base = {"id": case.id, "must_refuse": case.expected is None, "expected": case.expected, "duration_s": duration_s}
    if not isinstance(output, dict):
        return CaseResult(**base, status="erreur", detail="réponse hors contrat (objet `output` attendu)")
    if output.get("refus"):
        return CaseResult(**base, status="refus", got=output, detail=str(output["refus"]))
    fields = {k: same(v, output.get(k)) for k, v in (case.expected or {}).items()}
    return CaseResult(**base, status="reponse", got=output, fields_ok=fields)


Caller = Callable[[str], Any]  # input text -> the POC's `output` object (raises on transport errors)


def run_cases(cases: list[Case], call: Caller, on_progress: Callable[[int], None] | None = None) -> list[CaseResult]:
    results = []
    for i, case in enumerate(cases):
        start = time.perf_counter()
        try:
            output = call(case.input)
            result = judge(case, output, time.perf_counter() - start)
        except Exception as exc:  # noqa: BLE001 - any POC failure is a result, not a crash of the bench
            result = CaseResult(id=case.id, must_refuse=case.expected is None, status="erreur",
                                expected=case.expected, detail=f"{type(exc).__name__}: {exc}"[:200],
                                duration_s=time.perf_counter() - start)
        results.append(result)
        if on_progress:
            on_progress(i + 1)
    return results


# --- Metrics, verdict, report --------------------------------------------------------------------


class Rate(BaseModel):
    k: int
    n: int
    rate: float
    ic95: tuple[float, float]


def _rate(k: int, n: int) -> Rate:
    lo, hi = wilson(k, n)
    return Rate(k=k, n=n, rate=round(k / n, 3) if n else 0.0, ic95=(round(lo, 3), round(hi, 3)))


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1)]


def metrics(results: list[CaseResult]) -> dict[str, Any]:
    answer = [r for r in results if not r.must_refuse]
    refuse = [r for r in results if r.must_refuse]
    fields = [ok for r in answer for ok in (r.fields_ok.values() if r.status == "reponse"
                                            else [False] * len(r.expected or {}))]
    durations = [r.duration_s for r in results if r.status != "erreur"]
    return {
        "justesse_document": _rate(sum(r.label == "correct" for r in answer), len(answer)).model_dump(),
        "justesse_champs": _rate(sum(fields), len(fields)).model_dump(),
        "refus_corrects": _rate(sum(r.label == "refus_correct" for r in refuse), len(refuse)).model_dump(),
        "faux_refus": _rate(sum(r.label == "faux_refus" for r in answer), len(answer)).model_dump(),
        "erreurs_techniques": sum(r.status == "erreur" for r in results),
        "latence_moyenne_s": round(sum(durations) / len(durations), 2) if durations else 0.0,
        "latence_p95_s": round(percentile(durations, 0.95), 2),
    }


class Criterion(BaseModel):
    metrique: Metric
    seuil: float
    justification: str = ""


class CriterionResult(BaseModel):
    metrique: Metric
    libelle: str
    seuil: float
    valeur: float
    ic95: tuple[float, float] | None
    atteint: bool
    robuste: bool  # the whole 95 % interval is on the right side of the threshold


def verdict(criteria: list[Criterion], m: dict[str, Any]) -> list[CriterionResult]:
    out = []
    for c in criteria:
        raw = m[c.metrique]
        value = float(raw["rate"]) if isinstance(raw, dict) else float(raw)
        ic = tuple(raw["ic95"]) if isinstance(raw, dict) else None
        lower = c.metrique in LOWER_IS_BETTER
        ok = value <= c.seuil if lower else value >= c.seuil
        robust = ok if ic is None else (ic[1] <= c.seuil if lower else ic[0] >= c.seuil)
        out.append(CriterionResult(metrique=c.metrique, libelle=METRIC_LABELS[c.metrique], seuil=c.seuil,
                                   valeur=value, ic95=ic, atteint=ok, robuste=robust))
    return out


def _short(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= 120 else text[:117] + "…"


def failure_groups(results: list[CaseResult]) -> list[dict[str, Any]]:
    """Failures grouped by cause, most frequent first, each with up to 3 examples."""
    groups: dict[str, list[CaseResult]] = {}
    for r in results:
        if r.label == "champ_faux":
            for name, ok in r.fields_ok.items():
                if not ok:
                    groups.setdefault(f"champ:{name}", []).append(r)
        elif r.label not in ("correct", "refus_correct"):
            groups.setdefault(r.label, []).append(r)
    out = []
    for cause, rs in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        examples = []
        for r in rs[:3]:
            if cause.startswith("champ:"):
                name = cause.split(":", 1)[1]
                examples.append({"id": r.id, "attendu": _short((r.expected or {}).get(name)),
                                 "obtenu": _short((r.got or {}).get(name))})
            else:
                examples.append({"id": r.id, "attendu": "refus" if r.must_refuse else "réponse",
                                 "obtenu": r.detail or _short(r.got)})
        out.append({"cause": cause, "nombre": len(rs), "cas": [r.id for r in rs], "exemples": examples})
    return out


_FIX = {
    "faux_refus": "Le POC refuse des commandes complètes : assouplir la règle de refus et ajouter ces cas au jeu "
                  "de développement.",
    "reponse_au_lieu_de_refus": "Le POC répond à des demandes ambiguës au lieu de demander à un humain : renforcer "
                                "les règles de refus (ne jamais deviner).",
    "erreur_technique": "Le POC ne respecte pas le contrat INTERFACE.md (erreur HTTP, délai ou format) : "
                        "corriger avant toute autre mesure.",
}


def corrections(groups: list[dict[str, Any]]) -> list[str]:
    """Correction list to hand back to the POC developer (or to Claude Code)."""
    out = []
    for g in groups:
        ids = ", ".join(g["cas"][:5]) + ("…" if len(g["cas"]) > 5 else "")
        if g["cause"].startswith("champ:"):
            name = g["cause"].split(":", 1)[1]
            ex = g["exemples"][0]
            out.append(f"Champ « {name} » faux dans {g['nombre']} cas ({ids}) - ex. {ex['id']} : attendu "
                       f"{ex['attendu']}, obtenu {ex['obtenu']}.")
        else:
            out.append(f"{_FIX[g['cause']]} ({g['nombre']} cas : {ids})")
    return out
