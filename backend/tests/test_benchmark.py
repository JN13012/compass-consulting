from datetime import datetime

from app.benchmark.collect import IssuerMapping, Template, build
from app.connectors import defillama, esma


def asset(id_: str, symbol: str, name: str, now: float, prev: float, chains: dict[str, float]) -> dict:  # type: ignore[type-arg]
    return {
        "id": id_, "symbol": symbol, "name": name, "pegType": "peggedEUR", "pegMechanism": "fiat-backed",
        "circulating": {"peggedEUR": now}, "circulatingPrevMonth": {"peggedEUR": prev},
        "chains": list(chains), "chainCirculating": {c: {"current": {"peggedEUR": v}} for c, v in chains.items()},
        "price": 1.17, "gecko_id": name.lower().replace(" ", "-"),
    }


PAYLOAD = {"peggedAssets": [
    asset("50", "EURC", "EURC", 500e6, 400e6, {"Solana": 100e6, "Ethereum": 400e6}),
    asset("239", "EURR", "StablR Euro", 14e6, 14e6, {"Ethereum": 14e6}),
    asset("436", "EURR", "Revolut Euro", 2e6, 0, {"Polygon": 2e6}),
    asset("1", "TINY", "Tiny Euro", 10_000, 10_000, {"Ethereum": 10_000}),
    {**asset("2", "USDT", "Tether", 1e11, 1e11, {"Tron": 1e11}), "pegType": "peggedUSD"},
]}

CSV = (
    "﻿ae_competentAuthority,ae_homeMemberState,ae_lei_name,ae_lei,ac_authorisationNotificationDate\n"
    "Autorité de Contrôle Prudentiel et de Résolution (ACPR),FR,Circle Internet Financial Europe SAS,"
    "969500OYUDADGZKCR583,01/07/2024\n"
    "Autorité de Contrôle Prudentiel et de Résolution (ACPR),FR,Circle Internet Financial Europe SAS,"
    "969500OYUDADGZKCR583,01/07/2024\n"
).encode()

TEMPLATE = Template(
    title="Stablecoins euro", description="d", peg="peggedEUR", min_circulating=1e6, limit=10,
    issuers={
        "EURC": IssuerMapping(lei="969500OYUDADGZKCR583", label="Circle Europe"),
        "EURR": IssuerMapping(lei="984500AA0OCA9CE0D796", label="StablR Ltd", name_contains="StablR"),
    },
)


def table() -> dict[str, dict]:  # type: ignore[type-arg]
    data = build("eur", TEMPLATE, defillama.parse(PAYLOAD), esma.parse(CSV), datetime(2026, 11, 7))
    return {r.key: {k: c.model_dump() for k, c in r.cells.items()} for r in data.rows}


def test_filters_by_peg_and_minimum_and_sorts_by_supply() -> None:
    assert list(table()) == ["EURC-50", "EURR-239", "EURR-436"]


def test_every_cell_has_a_source() -> None:
    for cells in table().values():
        for cell in cells.values():
            assert cell["source"] and cell["method"]


def test_derived_values() -> None:
    eurc = table()["EURC-50"]
    assert eurc["offre"]["display"] == "500,0 M€"
    assert eurc["variation_30j"]["display"] == "+25,0%"
    assert eurc["blockchains"]["display"].startswith("2 : Ethereum, Solana")  # largest supply first


def test_mica_register_status() -> None:
    t = table()
    assert t["EURC-50"]["statut_mica"]["value"] == "inscrit"
    assert "ACPR" in t["EURC-50"]["statut_mica"]["display"]
    assert t["EURR-239"]["statut_mica"]["value"] == "absent"        # mapped, LEI not in this register extract
    assert t["EURR-436"]["statut_mica"]["value"] == "non_rapproche"  # same symbol, other token: not mapped
