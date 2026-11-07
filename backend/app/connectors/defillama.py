"""DefiLlama stablecoins API (public, no key): supply, chains, peg mechanism, price."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

URL = "https://stablecoins.llama.fi/stablecoins?includePrices=true"
PAGE = "https://defillama.com/stablecoin/{slug}"


@dataclass(frozen=True)
class Stablecoin:
    id: str
    symbol: str
    name: str
    peg: str  # peggedEUR, peggedUSD…
    mechanism: str
    circulating: float
    circulating_prev_month: float | None
    chains: list[str]  # sorted by supply on chain, largest first
    price: float | None
    gecko_id: str | None

    @property
    def change_30d(self) -> float | None:
        if not self.circulating_prev_month:
            return None
        return (self.circulating - self.circulating_prev_month) / self.circulating_prev_month

    @property
    def page_url(self) -> str:
        return PAGE.format(slug=(self.gecko_id or self.name.lower().replace(" ", "-")))


def _amount(value: Any, peg: str) -> float:
    if isinstance(value, dict):
        return float(value.get(peg) or 0)
    return 0.0


def parse(payload: dict[str, Any]) -> list[Stablecoin]:
    coins = []
    for a in payload.get("peggedAssets", []):
        peg = a.get("pegType") or ""
        chain_supply = {c: _amount(v.get("current"), peg) for c, v in (a.get("chainCirculating") or {}).items()}
        chains = sorted(a.get("chains") or [], key=lambda c: -chain_supply.get(c, 0))
        prev = _amount(a.get("circulatingPrevMonth"), peg)
        coins.append(Stablecoin(
            id=str(a["id"]), symbol=a.get("symbol", ""), name=a.get("name", ""), peg=peg,
            mechanism=a.get("pegMechanism") or "", circulating=_amount(a.get("circulating"), peg),
            circulating_prev_month=prev or None, chains=chains,
            price=float(a["price"]) if isinstance(a.get("price"), int | float) else None,
            gecko_id=a.get("gecko_id"),
        ))
    return coins


def fetch(http: httpx.Client | None = None) -> list[Stablecoin]:
    client = http or httpx.Client(timeout=60, headers={"User-Agent": "compass-benchmark/0.1"})
    resp = client.get(URL)
    resp.raise_for_status()
    return parse(resp.json())
