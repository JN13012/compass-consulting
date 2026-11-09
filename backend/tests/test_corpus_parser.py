from datetime import date
from pathlib import Path

from app.corpus.cellar import consolidated_prefix, pick_latest
from app.corpus.parser import parse_articles_and_annexes, parse_recitals

FIX = Path(__file__).parent / "fixtures"
OJ = (FIX / "oj_act.xhtml").read_text(encoding="utf-8")
CONS = (FIX / "consolidated_act.xhtml").read_text(encoding="utf-8")


def by_ref(passages):  # type: ignore[no-untyped-def]
    return {p.ref: p for p in passages}


def test_oj_articles_paragraphs_and_annex() -> None:
    refs = by_ref(parse_articles_and_annexes(OJ, "T"))
    assert refs["T-ART-1"].kind == "article"
    assert refs["T-ART-1"].heading == "Article premier - Objet"
    assert refs["T-ART-1"].text.endswith("modifie le règlement (CE) nº 300/2008.")  # superscript + footnote
    assert refs["T-ART-3-1"].text.startswith("1. Aux fins du présent règlement")
    assert "2) «crypto-actif»" in refs["T-ART-3-1"].text
    assert "a) sous-point imbriqué;" in refs["T-ART-3-1"].text
    assert refs["T-ART-3-2"].heading == "Article 3 - Définitions, paragraphe 2"
    annex = refs["T-ANX-I-1"]
    assert annex.heading == "ANNEXE I" and "1. Le nom." in annex.text


def test_long_paragraph_is_split_into_points() -> None:
    refs = by_ref(parse_articles_and_annexes(OJ, "T", max_chars=50))
    assert "T-ART-3-1-intro" in refs
    point = refs["T-ART-3-1-2"]
    assert point.kind == "point"
    assert point.text.startswith("2) «crypto-actif»")
    assert "a) sous-point imbriqué;" in point.text  # nested points stay with their parent
    assert point.heading.startswith("Article 3 - Définitions, paragraphe 1, point 2 : 1. Aux fins")


def test_recitals_and_footnotes_removed() -> None:
    recitals = parse_recitals(OJ, "T")
    assert [p.ref for p in recitals] == ["T-RCT-1", "T-RCT-2"]
    assert recitals[0].text == "(1) Il importe d’adapter le droit à l’ère numérique."
    all_text = " ".join(p.text for p in parse_articles_and_annexes(OJ, "T"))
    assert "Note de bas de page" not in all_text


def test_consolidated_format() -> None:
    refs = by_ref(parse_articles_and_annexes(CONS, "C"))
    para = refs["C-ART-4-1"]
    assert para.text.startswith("Aux fins de la présente directive")
    assert "44) «valeurs mobilières»" in para.text
    assert "▼M6" not in para.text  # amendment markers removed
    assert refs["C-ART-4-2"].text == "Paragraphe deux."
    assert refs["C-ART-4a"].heading == "Article 4 bis"
    assert "Applicable jusqu’au 1er juillet 2026 au plus tard." in refs["C-ART-4a"].text  # inline sup glued


def test_consolidated_point_split() -> None:
    refs = by_ref(parse_articles_and_annexes(CONS, "C", max_chars=50))
    assert refs["C-ART-4-1-44"].text.startswith("44) «valeurs mobilières»")
    assert "a) les actions de sociétés;" in refs["C-ART-4-1-44"].text


def test_points_directly_in_article_are_split() -> None:
    refs = by_ref(parse_articles_and_annexes(CONS, "C", max_chars=50))
    assert refs["C-ART-3-intro"].text == "Aux fins du présent règlement, on entend par:"
    assert refs["C-ART-3-2"].text.startswith("2) «réseau et système d’information»")
    assert refs["C-ART-3-2"].heading.startswith("Article 3 - Définitions, point 2 : Aux fins")


def test_refs_are_stable() -> None:
    first = [p.ref for p in parse_articles_and_annexes(OJ, "T")]
    assert first == [p.ref for p in parse_articles_and_annexes(OJ, "T")]
    assert len(first) == len(set(first))


def test_pick_latest_consolidated_ignores_future_versions() -> None:
    versions = ["02014L0065-20250117", "02014L0065-20260606", "02014L0065-20270101", "02014L0065-20140917"]
    latest = pick_latest(versions, today=date(2026, 11, 7))
    assert latest is not None and latest.celex == "02014L0065-20260606"
    assert pick_latest([], today=date(2026, 11, 7)) is None


def test_consolidated_prefix() -> None:
    assert consolidated_prefix("32014L0065") == "02014L0065"
