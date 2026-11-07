"""ESMA interim MiCA register — e-money token (EMT) issuers (CSV, public)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

import httpx

EMT_URL = "https://www.esma.europa.eu/sites/default/files/2024-12/EMTWP.csv"
REGISTER_PAGE = (
    "https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/markets-crypto-assets-regulation-mica"
)


@dataclass(frozen=True)
class EmtIssuer:
    lei: str
    name: str
    authority: str
    country: str
    date: str  # authorisation / notification date as published (dd/mm/yyyy)


def parse(raw: bytes) -> dict[str, EmtIssuer]:
    """LEI -> issuer (the CSV repeats one row per white paper; first occurrence kept)."""
    text = raw.decode("utf-8-sig", errors="replace")
    issuers: dict[str, EmtIssuer] = {}
    for row in csv.DictReader(io.StringIO(text)):
        lei = (row.get("ae_lei") or "").strip()
        if lei and lei not in issuers:
            issuers[lei] = EmtIssuer(
                lei=lei,
                name=(row.get("ae_lei_name") or "").strip(),
                authority=(row.get("ae_competentAuthority") or "").strip(),
                country=(row.get("ae_homeMemberState") or "").strip(),
                date=(row.get("ac_authorisationNotificationDate") or "").strip(),
            )
    return issuers


def fetch(http: httpx.Client | None = None) -> dict[str, EmtIssuer]:
    client = http or httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 compass"})
    resp = client.get(EMT_URL)
    resp.raise_for_status()
    return parse(resp.content)
