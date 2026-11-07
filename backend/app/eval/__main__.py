"""Evaluation CLI.

  python -m app.eval split                          # one-time: qa_all -> qa_dev / qa_test (never edit test after)
  python -m app.eval retrieval --split dev          # recall@k + similarity profile per mode (no generation)
  python -m app.eval kb --split dev --mode vector   # full pipeline with the configured model
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from app.answering.service import AnswerSettings, answer_question
from app.api.kb import get_router
from app.core.config import get_settings
from app.core.db import get_engine
from app.eval.metrics import Item, Outcome, matches, split, summarize
from app.retrieval.search import best_similarity, search

EVAL_DIR = Path("/srv/eval")


def load(name: str) -> list[Item]:
    path = EVAL_DIR / f"qa_{name}.jsonl"
    return [Item(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write(name: str, items: list[Item]) -> None:
    lines = [json.dumps(asdict(i), ensure_ascii=False) for i in items]
    (EVAL_DIR / f"qa_{name}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_split() -> int:
    if (EVAL_DIR / "qa_test.jsonl").exists():
        print("qa_test.jsonl existe déjà : le jeu de test est figé, pas de nouveau tirage.", file=sys.stderr)
        return 1
    dev, test = split(load("all"))
    write("dev", dev)
    write("test", test)
    print(f"dev : {len(dev)} questions ({sum(i.answerable for i in dev)} répondables)")
    print(f"test : {len(test)} questions ({sum(i.answerable for i in test)} répondables)")
    return 0


def cmd_retrieval(split_name: str, k: int) -> int:
    session = sessionmaker(bind=get_engine())()
    llm = get_router()
    embed = lambda q: llm.embed([q])[0]  # noqa: E731
    items = load(split_name)
    for mode in ("fulltext", "vector", "hybrid"):
        found = 0
        sims_a: list[float] = []
        sims_u: list[float] = []
        for item in items:
            hits, used = search(session, item.question, mode, k, None, embed)
            sim = best_similarity(hits) if used != "fulltext" else (hits[0].score if hits else 0.0)
            (sims_a if item.answerable else sims_u).append(round(sim or 0.0, 3))
            if item.answerable and any(matches(h.ref, item.expected) for h in hits):
                found += 1
        n = sum(i.answerable for i in items)
        print(f"\n{mode:<8} rappel@{k} = {found}/{n}")
        print(f"  score du meilleur passage — répondables : {sorted(sims_a)}")
        print(f"  score du meilleur passage — hors corpus : {sorted(sims_u)}")
    return 0


def cmd_kb(split_name: str, mode: str, role: str, min_score: float, min_similarity: float, top_k: int) -> int:
    session = sessionmaker(bind=get_engine())()
    llm = get_router()
    embed = lambda q: llm.embed([q])[0]  # noqa: E731
    settings = AnswerSettings(role=role, mode=mode, top_k=top_k, min_score=min_score,  # type: ignore[arg-type]
                              min_similarity=min_similarity)
    outcomes: list[Outcome] = []
    items = load(split_name)
    for n, item in enumerate(items, 1):
        start = time.perf_counter()
        try:
            ans = answer_question(session, llm, item.question, settings, None, embed)
            outcome = Outcome(item, ans.status, [c.ref for c in ans.citations], [h.ref for h in ans.retrieved],
                              ans.answer, ans.refusal_reason, best_similarity(ans.retrieved), ans.duration_s)
        except Exception as exc:
            outcome = Outcome(item, "error", [], [], f"{type(exc).__name__}: {exc}", None, None,
                              time.perf_counter() - start)
        outcomes.append(outcome)
        print(f"[{n:>2}/{len(items)}] {item.id} {outcome.label:<26} {outcome.duration_s:5.1f}s", flush=True)

    summary = summarize(outcomes)
    model = llm.resolve(role, __import__("app.core.models", fromlist=["Confidentiality"]).Confidentiality.PUBLIC)
    run = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "split": split_name,
        "config": {"mode": mode, "role": role, "model": model.model, "top_k": top_k,
                   "min_score": min_score, "min_similarity": min_similarity},
        "summary": summary,
        "outcomes": [
            {"id": o.item.id, "label": o.label, "status": o.status, "cited": o.cited, "expected": o.item.expected,
             "answer": o.answer, "refusal_reason": o.refusal_reason, "best_similarity": o.best_similarity,
             "retrieved": o.retrieved[:5]}
            for o in outcomes
        ],
    }
    runs = EVAL_DIR / "runs"
    runs.mkdir(exist_ok=True)
    out = runs / f"{split_name}_{mode}_{role}_{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(run, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"→ {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m app.eval")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("split")
    r = sub.add_parser("retrieval")
    r.add_argument("--split", default="dev", choices=["dev", "test"])
    r.add_argument("--k", type=int, default=8)
    kb = sub.add_parser("kb")
    kb.add_argument("--split", default="dev", choices=["dev", "test"])
    kb.add_argument("--mode", default="hybrid", choices=["fulltext", "vector", "hybrid"])
    kb.add_argument("--role", default=get_settings().kb_role)
    kb.add_argument("--min-score", type=float, default=0.30)
    kb.add_argument("--min-similarity", type=float, default=0.50)
    kb.add_argument("--top-k", type=int, default=8)
    a = p.parse_args(argv)
    if a.command == "split":
        return cmd_split()
    if a.command == "retrieval":
        return cmd_retrieval(a.split, a.k)
    return cmd_kb(a.split, a.mode, a.role, a.min_score, a.min_similarity, a.top_k)


if __name__ == "__main__":
    raise SystemExit(main())
