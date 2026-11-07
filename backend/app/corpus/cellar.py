"""Access to the EU Publications Office (Cellar): same texts as EUR-Lex, machine-readable.

EUR-Lex HTML pages block automated clients; the Publications Office API serves the
official XHTML manifestation of each act and of its consolidated versions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import httpx

CELLAR = "https://publications.europa.eu/resource/celex/{celex}"
SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"
EURLEX = "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:{celex}"
USER_AGENT = "compass-corpus/0.1 (regulatory corpus ingestion)"

_CONSOLIDATED = re.compile(r"^0\d{4}[A-Z]\d{4}-(\d{8})$")


@dataclass(frozen=True)
class Version:
    celex: str
    consolidated: bool
    as_of: date | None  # consolidation date


def eurlex_url(celex: str) -> str:
    return EURLEX.format(celex=celex)


def consolidated_prefix(celex: str) -> str:
    """32014L0065 -> 02014L0065 (consolidated versions share this prefix + '-YYYYMMDD')."""
    return "0" + celex[1:]


def candidates(celexes: list[str], today: date) -> list[Version]:
    """Consolidated versions dated <= today, newest first (future-dated versions are skipped)."""
    found: list[Version] = []
    for raw_celex in celexes:
        celex = raw_celex.strip().strip('"')
        match = _CONSOLIDATED.match(celex)
        if not match:
            continue
        raw = match.group(1)
        as_of = date(int(raw[:4]), int(raw[4:6]), int(raw[6:]))
        if as_of <= today:
            found.append(Version(celex=celex, consolidated=True, as_of=as_of))
    return sorted(found, key=lambda v: v.as_of or date.min, reverse=True)


def pick_latest(celexes: list[str], today: date) -> Version | None:
    found = candidates(celexes, today)
    return found[0] if found else None


class CellarClient:
    def __init__(self, http: httpx.Client | None = None) -> None:
        self._http = http or httpx.Client(
            timeout=120, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        )

    def consolidated_versions(self, celex: str) -> list[str]:
        prefix = consolidated_prefix(celex)
        query = f"""PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?celex WHERE {{
  ?w cdm:resource_legal_id_celex ?celex .
  FILTER(STRSTARTS(STR(?celex), "{prefix}-"))
}}"""
        resp = self._get(SPARQL, params={"query": query, "format": "text/csv"})
        return [line.strip().strip('"') for line in resp.text.splitlines()[1:] if line.strip()]

    def versions(self, celex: str, today: date) -> list[Version]:
        """Versions to try, best first: consolidated (newest -> oldest), then the original act.

        Some consolidated versions are listed but have no French XHTML manifestation: the
        ingestion falls back to the next candidate.
        """
        return [*candidates(self.consolidated_versions(celex), today),
                Version(celex=celex, consolidated=False, as_of=None)]

    def fetch_xhtml(self, celex: str) -> bytes:
        resp = self._get(
            CELLAR.format(celex=celex),
            headers={"Accept": "application/xhtml+xml", "Accept-Language": "fra"},
        )
        if b"<html" not in resp.content[:2000]:
            raise ValueError(f"{celex}: unexpected content ({resp.headers.get('content-type')})")
        return resp.content

    def _get(self, url: str, **kwargs: object) -> httpx.Response:
        last: Exception | None = None
        for _ in range(3):
            try:
                resp = self._http.get(url, **kwargs)  # type: ignore[arg-type]
                resp.raise_for_status()
                return resp
            except httpx.HTTPError as exc:
                last = exc
        raise RuntimeError(f"GET {url} failed after 3 attempts: {last}") from last
