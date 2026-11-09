"""Benchmark collection: public data -> table where EVERY cell carries its source (SPEC §3.7)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from app.connectors import defillama, esma
from app.connectors.defillama import Stablecoin
from app.connectors.esma import EmtIssuer

DEFILLAMA = "DefiLlama (API stablecoins)"
ESMA = "Registre intérimaire MiCA de l'ESMA (émetteurs EMT)"


class IssuerMapping(BaseModel):
    lei: str
    label: str
    name_contains: str | None = None


class Template(BaseModel):
    title: str
    description: str
    peg: str
    min_circulating: float = 0
    limit: int = 10
    issuers: dict[str, IssuerMapping] = {}


class Cell(BaseModel):
    value: Any
    display: str
    source: str
    url: str
    method: str


class Column(BaseModel):
    key: str
    label: str


class Row(BaseModel):
    key: str
    cells: dict[str, Cell]


class BenchmarkData(BaseModel):
    template: str
    title: str
    description: str
    collected_at: str
    columns: list[Column]
    rows: list[Row]
    sources: list[dict[str, str]]


COLUMNS = [
    Column(key="token", label="Token"),
    Column(key="mecanisme", label="Mécanisme"),
    Column(key="offre", label="Offre en circulation"),
    Column(key="variation_30j", label="Variation 30 j"),
    Column(key="blockchains", label="Blockchains"),
    Column(key="emetteur", label="Émetteur (rapprochement)"),
    Column(key="statut_mica", label="Registre MiCA (EMT)"),
]


AUTHORITY_SHORT = {
    "Autorité de Contrôle Prudentiel": "ACPR",
    "Federal Financial Supervisory Authority": "BaFin",
    "Malta Financial Services Authority": "MFSA",
    "Central Bank of Iceland": "Banque centrale d'Islande",
    "Commission de Surveillance du Secteur Financier": "CSSF",
    "De Nederlandsche Bank": "DNB",
    "Finanssivalvonta": "FIN-FSA",
}


def short_authority(name: str) -> str:
    return next((short for long, short in AUTHORITY_SHORT.items() if name.startswith(long)), name)


def load_templates(path: Path) -> dict[str, Template]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {k: Template.model_validate(v) for k, v in data["templates"].items()}


def _money(amount: float, peg: str) -> str:
    unit = {"peggedEUR": "€", "peggedUSD": "$"}.get(peg, "")
    if amount >= 1e9:
        return f"{amount / 1e9:.2f} Md{unit}".replace(".", ",")
    return f"{amount / 1e6:.1f} M{unit}".replace(".", ",")


def _mapping(coin: Stablecoin, template: Template) -> IssuerMapping | None:
    m = template.issuers.get(coin.symbol)
    if m and m.name_contains and m.name_contains.lower() not in coin.name.lower():
        return None  # same symbol, different token (e.g. two "EURR")
    return m


def build(name: str, template: Template, coins: list[Stablecoin], register: dict[str, EmtIssuer],
          collected_at: datetime) -> BenchmarkData:
    selected = sorted(
        (c for c in coins if c.peg == template.peg and c.circulating >= template.min_circulating),
        key=lambda c: -c.circulating,
    )[: template.limit]

    rows = []
    for c in selected:
        def dl(value: Any, display: str, method: str = "lecture directe", url: str = c.page_url) -> Cell:
            return Cell(value=value, display=display, source=DEFILLAMA, url=url, method=method)

        mapping = _mapping(c, template)
        if mapping is None:
            emetteur = Cell(value=None, display="Non rapproché", source="-", url="",
                            method="aucun rapprochement token → émetteur configuré")
            statut = Cell(value="non_rapproche", display="Émetteur non rapproché", source=ESMA, url=esma.REGISTER_PAGE,
                          method="non vérifiable sans rapprochement")
        else:
            emetteur = Cell(value=mapping.lei, display=mapping.label, source="Rapprochement manuel (config)",
                            url=f"https://search.gleif.org/#/record/{mapping.lei}",
                            method="rapprochement manuel token → LEI, à valider")
            issuer = register.get(mapping.lei)
            if issuer:
                label = f"Inscrit - {short_authority(issuer.authority)} ({issuer.country})"
                statut = Cell(value="inscrit", display=label, source=ESMA, url=esma.EMT_URL,
                              method=f"LEI trouvé dans le registre (date publiée : {issuer.date})")
            else:
                statut = Cell(value="absent", display="LEI absent du registre", source=ESMA, url=esma.EMT_URL,
                              method="LEI recherché, non trouvé")
        change = c.change_30d
        rows.append(Row(key=f"{c.symbol}-{c.id}", cells={
            "token": dl(c.symbol, f"{c.symbol} - {c.name}"),
            "mecanisme": dl(c.mechanism, {"fiat-backed": "Réserves fiat",
                                          "crypto-backed": "Réserves crypto",
                                          "algorithmic": "Algorithmique"}.get(c.mechanism, c.mechanism or "-")),
            "offre": dl(c.circulating, _money(c.circulating, c.peg)),
            "variation_30j": dl(change, "-" if change is None else f"{change:+.1%}".replace(".", ","),
                                "calcul : (offre actuelle − offre il y a 30 j) / offre il y a 30 j"),
            "blockchains": dl(
                c.chains, f"{len(c.chains)} : " + ", ".join(c.chains[:4]) + ("…" if len(c.chains) > 4 else "")
            ),
            "emetteur": emetteur,
            "statut_mica": statut,
        }))

    return BenchmarkData(
        template=name, title=template.title, description=template.description,
        collected_at=collected_at.isoformat(timespec="seconds"), columns=COLUMNS, rows=rows,
        sources=[{"name": DEFILLAMA, "url": defillama.URL}, {"name": ESMA, "url": esma.EMT_URL}],
    )


def collect(name: str, template: Template) -> BenchmarkData:
    return build(name, template, defillama.fetch(), esma.fetch(), datetime.now())
