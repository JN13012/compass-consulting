"""CLI: python -m app.corpus ingest [--source CODE]"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.db import get_engine
from app.corpus.cellar import CellarClient
from app.corpus.ingest import format_report, ingest_source
from app.corpus.sources import load_sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.corpus")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="download and index official texts")
    ingest.add_argument("--source", help="only this source code (e.g. MICA)")
    sub.add_parser("embed", help="compute missing embeddings (role 'embedding' in config/llm.yaml)")
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.command == "embed":
        from app.corpus.embed import run
        from app.llm.router import LlmConfig, LlmRouter

        llm = LlmRouter(LlmConfig.from_yaml(settings.llm_config_path))
        session = sessionmaker(bind=get_engine())()
        run(session, llm.embed)
        session.close()
        return 0

    sources = load_sources(settings.corpus_dir / "sources.yaml")
    if args.source:
        sources = [s for s in sources if s.code == args.source.upper()]
        if not sources:
            print(f"Source inconnue : {args.source}", file=sys.stderr)
            return 2

    client = CellarClient()
    session = sessionmaker(bind=get_engine())()
    reports = []
    for source in sources:
        print(f"→ {source.code} ({source.short})…", flush=True)
        reports.append(ingest_source(session, source, client, settings.corpus_dir / "raw", date.today()))
    session.close()
    print()
    print(format_report(reports))
    return 1 if any(r.status == "failed" for r in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
