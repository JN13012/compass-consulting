"""Evaluation metrics for the knowledge base (pure functions, no I/O)."""

from __future__ import annotations

import math
import random
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    id: str
    question: str
    answerable: bool
    expected: list[str]
    must_contain: list[str]
    domain: str


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95 % Wilson score interval — reliable for small samples and proportions near 0 or 1."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def matches(ref: str, expected: list[str]) -> bool:
    """A cited ref matches an expected prefix on a segment boundary (MICA-ART-3-1 ⊃ MICA-ART-3-1-5)."""
    return any(ref == e or ref.startswith(e + "-") for e in expected)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace("’", "'").replace(" ", " ").replace("\xa0", " ")
    return " ".join(text.split())


def contains_all(answer: str, facts: list[str]) -> bool:
    a = normalize(answer)
    return all(normalize(f) in a for f in facts)


def split(items: list[Item], dev_share: float = 0.4, seed: int = 20261107) -> tuple[list[Item], list[Item]]:
    """Stratified (answerable / not) deterministic split."""
    rng = random.Random(seed)
    dev: list[Item] = []
    test: list[Item] = []
    for group in (True, False):
        pool = sorted((i for i in items if i.answerable is group), key=lambda i: i.id)
        rng.shuffle(pool)
        cut = round(len(pool) * dev_share)
        dev += pool[:cut]
        test += pool[cut:]
    return sorted(dev, key=lambda i: i.id), sorted(test, key=lambda i: i.id)


@dataclass
class Outcome:
    item: Item
    status: str  # answered | refused | error
    cited: list[str]
    retrieved: list[str]
    answer: str
    refusal_reason: str | None
    best_similarity: float | None
    duration_s: float

    @property
    def cited_expected(self) -> bool:
        return any(matches(r, self.item.expected) for r in self.cited)

    @property
    def retrieved_expected(self) -> bool:
        return any(matches(r, self.item.expected) for r in self.retrieved)

    @property
    def label(self) -> str:
        if not self.item.answerable:
            return "refus_correct" if self.status == "refused" else "reponse_hors_corpus"
        if self.status != "answered":
            return "faux_refus"
        if not self.cited_expected:
            return "mauvaise_source"
        return "correct" if contains_all(self.answer, self.item.must_contain) else "bonne_source_fait_absent"


def summarize(outcomes: list[Outcome]) -> dict[str, object]:
    ans = [o for o in outcomes if o.item.answerable]
    una = [o for o in outcomes if not o.item.answerable]

    def rate(k: int, n: int) -> dict[str, object]:
        lo, hi = wilson(k, n)
        return {"k": k, "n": n, "rate": round(k / n, 3) if n else 0.0, "ic95": [round(lo, 3), round(hi, 3)]}

    labels = [o.label for o in outcomes]
    good_source = sum(1 for o in ans if o.status == "answered" and o.cited_expected)
    return {
        "bonne_source": rate(good_source, len(ans)),
        "correct_strict": rate(labels.count("correct"), len(ans)),
        "faux_refus": rate(labels.count("faux_refus"), len(ans)),
        "mauvaise_source": rate(labels.count("mauvaise_source"), len(ans)),
        "refus_corrects": rate(labels.count("refus_correct"), len(una)),
        "global": rate(good_source + labels.count("refus_correct"), len(outcomes)),
        "rappel_recherche": rate(sum(1 for o in ans if o.retrieved_expected), len(ans)),
        "duree_moyenne_s": round(sum(o.duration_s for o in outcomes) / max(len(outcomes), 1), 2),
    }
