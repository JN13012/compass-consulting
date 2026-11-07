from app.eval.metrics import Item, Outcome, contains_all, matches, split, summarize, wilson


def item(i: int, answerable: bool = True) -> Item:
    return Item(f"q{i:02d}", "?", answerable, ["MICA-ART-3-1"] if answerable else [], ["30 décembre"], "crypto")


def test_wilson_known_value() -> None:
    lo, hi = wilson(24, 27)  # the LinkedIn example: 24/27 -> ~72 % to ~96 %
    assert round(lo, 2) == 0.72 and round(hi, 2) == 0.96
    assert wilson(0, 0) == (0.0, 0.0)


def test_prefix_matching_on_segment_boundary() -> None:
    assert matches("MICA-ART-3-1-5", ["MICA-ART-3-1"])
    assert matches("MICA-ART-3-1", ["MICA-ART-3-1"])
    assert not matches("MICA-ART-3-10", ["MICA-ART-3-1"])


def test_contains_all_normalizes() -> None:
    assert contains_all("Applicable à partir du 30 décembre 2024.", ["30 décembre"])
    assert not contains_all("Applicable en 2024.", ["30 décembre"])


def test_split_is_stratified_and_deterministic() -> None:
    items = [item(i) for i in range(10)] + [item(i, False) for i in range(10, 15)]
    dev, test = split(items)
    assert (sum(i.answerable for i in dev), sum(not i.answerable for i in dev)) == (4, 2)
    assert split(items) == (dev, test)
    assert not {i.id for i in dev} & {i.id for i in test}


def test_labels_and_summary() -> None:
    def out(it: Item, status: str, cited: list[str], answer: str = "le 30 décembre") -> Outcome:
        return Outcome(it, status, cited, cited, answer, None, 0.7, 1.0)

    outcomes = [
        out(item(1), "answered", ["MICA-ART-3-1-5"]),            # correct
        out(item(2), "answered", ["MICA-ART-3-1-5"], "bientôt"),  # good source, fact missing
        out(item(3), "answered", ["MICA-ART-9"]),                 # wrong source
        out(item(4), "refused", []),                              # false refusal
        out(item(5, False), "refused", []),                       # correct refusal
        out(item(6, False), "answered", ["X-1"]),                 # answered out of corpus
    ]
    assert [o.label for o in outcomes] == [
        "correct", "bonne_source_fait_absent", "mauvaise_source", "faux_refus", "refus_correct",
        "reponse_hors_corpus",
    ]
    s = summarize(outcomes)
    assert s["bonne_source"]["k"] == 2 and s["refus_corrects"]["k"] == 1  # type: ignore[index]
    assert s["global"]["k"] == 3 and s["global"]["n"] == 6  # type: ignore[index]
