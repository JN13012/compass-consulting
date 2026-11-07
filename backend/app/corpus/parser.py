"""Split EU legal acts (Publications Office XHTML) into citable passages.

Handles both formats served by the Publications Office:
- Official Journal ("oj-*" classes, points as 2-column tables, paragraphs as div id="003.001");
- consolidated versions ("norm" classes, points as div.grid-container, paragraphs as span.no-parag).

Rules (SPEC §4):
- one passage per numbered paragraph; an article without numbered paragraphs is one passage;
- a paragraph longer than `max_chars` is split into one passage per top-level point;
- one passage per recital; annexes are chunked on line boundaries.
Identifiers are stable: same input -> same refs.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, NavigableString, Tag, XMLParsedAsHTMLWarning

# The XHTML is parsed with the lenient HTML parser on purpose (robust to markup quirks).
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

MAX_CHARS = 2500
# Bump whenever splitting rules change: ingestion re-parses documents parsed with an older version.
PARSER_VERSION = 5

_PARAGRAPH_ID = re.compile(r"^\d{3}\.(\d{3})$")
_ARTICLE_ID = re.compile(r"^art_(\d+[a-z]*)$")
_RECITAL_ID = re.compile(r"^rct_(\d+[a-z]*)$")
_ANNEX_ID = re.compile(r"^anx_([^.]+)$")
_WS = re.compile(r"\s+")

_TITLE_CLASSES = {"oj-ti-art", "title-article-norm"}
_SUBTITLE_CLASSES = {"oj-sti-art", "stitle-article-norm"}
_DROP_CLASSES = {"modref", "arrow", "oj-note", "footnote", "note"}


@dataclass(frozen=True)
class ParsedPassage:
    ref: str
    kind: str  # article | paragraphe | point | considerant | annexe
    heading: str
    text: str

    def __post_init__(self) -> None:
        # Final cleanup across line breaks (footnote markers may sit on their own line).
        text = _EMPTY_PARENS.sub("", self.text)
        text = _NUMERO_SPACED.sub("nº", text)
        object.__setattr__(self, "text", "\n".join(line for line in text.split("\n") if line.strip()))


@dataclass
class _Point:
    label: str
    lines: list[str] = field(default_factory=list)


Item = str | _Point


_EMPTY_PARENS = re.compile(r"\s*\(\s*\)")  # left behind by removed footnote markers
_NUMERO = re.compile(r"\bno(?=\s*\d)")  # "no 300/2008" (n + superscript o) -> "nº 300/2008"
_NUMERO_SPACED = re.compile(r"\bn o(?=\s*\d)")  # same, when cells were joined with spaces


def _norm(text: str) -> str:
    text = _WS.sub(" ", text.replace("\xa0", " ")).strip()
    text = _EMPTY_PARENS.sub("", text)
    return _NUMERO.sub("nº", text)


def _classes(tag: Tag) -> set[str]:
    value = tag.get("class") or []
    return set(value if isinstance(value, list) else str(value).split())


def _label(text: str) -> str:
    return _norm(text).strip("().").rstrip(")").strip() or "x"


def _is_point(tag: Tag) -> bool:
    if tag.name == "div" and "grid-container" in _classes(tag):
        return True
    if tag.name == "table" and not ({"oj-table", "table"} & _classes(tag)):
        row = tag.find("tr")
        return isinstance(row, Tag) and len(row.find_all("td", recursive=False)) == 2
    return False


def _point_parts(tag: Tag) -> tuple[str, Tag | None]:
    if tag.name == "table":
        cells = tag.find("tr").find_all("td", recursive=False)  # type: ignore[union-attr]
        return _norm(cells[0].get_text(" ")), cells[1]
    first = tag.find(class_="grid-list-column-1")
    body = tag.find(class_="grid-list-column-2")
    return _norm(first.get_text(" ") if first else ""), body if isinstance(body, Tag) else None


_INLINE_TAGS = {"span", "sup", "sub", "a", "em", "i", "b", "strong", "abbr", "u", "q"}


def _items(el: Tag, keep_points: bool) -> list[Item]:
    """Render `el` as lines; top-level points become _Point items when keep_points is True.

    Consecutive inline content (text nodes, <span>, <sup>…) is glued into ONE line, so that
    "1<span>er</span> juillet" stays "1er juillet" when it sits directly in a <div>.
    """
    out: list[Item] = []
    inline: list[str] = []

    def flush() -> None:
        text = _norm("".join(inline))
        if text:
            out.append(text)
        inline.clear()

    for child in el.children:
        if isinstance(child, NavigableString):
            if el.name not in {"table", "tbody", "tr", "colgroup"}:
                inline.append(str(child))
            continue
        if not isinstance(child, Tag) or _classes(child) & _DROP_CLASSES or child.name in {"col", "colgroup"}:
            continue
        if "no-parag" in _classes(child):
            continue  # paragraph number, captured separately
        if child.name in _INLINE_TAGS and not child.find(["div", "table", "p"]) and not _is_point(child):
            inline.append(child.get_text(""))
            continue
        flush()
        if _is_point(child):
            label, body = _point_parts(child)
            lines = _flatten(_items(body, keep_points=False)) if body else []
            if keep_points:
                out.append(_Point(label=label, lines=lines))
            else:
                out.extend([f"{label} {lines[0]}" if lines else label, *lines[1:]])
        elif child.name == "table":  # real data table
            for row in child.find_all("tr"):
                cells = [_norm(c.get_text(" ")) for c in row.find_all(["td", "th"])]
                if any(cells):
                    out.append(" | ".join(cells))
        elif child.name == "p" and not child.find(["div", "table", "p"]):
            text = _norm(child.get_text(""))  # "" keeps inline tags glued (n<sup>o</sup> -> no)
            if text:
                out.append(text)
        else:
            out.extend(_items(child, keep_points))
    flush()
    return out


def _flatten(items: list[Item]) -> list[str]:
    lines: list[str] = []
    for item in items:
        if isinstance(item, _Point):
            lines.extend([f"{item.label} {item.lines[0]}" if item.lines else item.label, *item.lines[1:]])
        else:
            lines.append(item)
    return lines


def _text(items: list[Item]) -> str:
    return "\n".join(_flatten(items))


class _Refs:
    """Guarantees unique refs within a document (suffix -2, -3… on collision)."""

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def make(self, ref: str) -> str:
        count = self._seen.get(ref, 0) + 1
        self._seen[ref] = count
        return ref if count == 1 else f"{ref}-{count}"


def _clean(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(class_=lambda c: bool(c) and bool(set(str(c).split()) & _DROP_CLASSES)):
        tag.decompose()
    for a in soup.find_all("a", href=re.compile(r"^#(ntr|ntc|E)")):
        a.decompose()  # footnote markers


def _paragraphs(article: Tag) -> list[tuple[str | None, list[Item]]]:
    """Return (paragraph label | None, items) blocks of an article body."""
    blocks: list[tuple[str | None, list[Item]]] = []
    loose: list[Item] = []
    for child in article.children:
        if not isinstance(child, Tag):
            continue
        cls = _classes(child)
        if cls & (_TITLE_CLASSES | _SUBTITLE_CLASSES) or "eli-title" in cls:
            continue
        label: str | None = None
        match = _PARAGRAPH_ID.match(str(child.get("id", "")))
        if match:
            label = str(int(match.group(1)))
        else:
            span = child.find("span", class_="no-parag", recursive=False)
            if isinstance(span, Tag):
                label = _label(span.get_text())
        if _is_point(child):  # point placed directly in the article (no numbered paragraph)
            point_label, body = _point_parts(child)
            items: list[Item] = [
                _Point(point_label, _flatten(_items(body, keep_points=False)) if body else [])
            ]
        elif child.name == "p":
            items = [_norm(child.get_text(""))]
        else:
            items = _items(child, keep_points=True)
        items = [i for i in items if i]
        if label is None:
            if blocks:
                blocks[-1][1].extend(items)  # trailing sub-paragraph of the previous paragraph
            else:
                loose.extend(items)
        else:
            if loose:  # text before the first numbered paragraph
                items = loose + items
                loose = []
            blocks.append((label, items))
    if not blocks:
        return [(None, loose)]
    return blocks


def _split_points(
    base_ref: str, heading: str, items: list[Item], refs: _Refs, max_chars: int, kind: str
) -> list[ParsedPassage]:
    text = _text(items)
    points = [i for i in items if isinstance(i, _Point)]
    if len(text) <= max_chars or len(points) < 2:
        return [ParsedPassage(refs.make(base_ref), kind, heading, text)]
    chapeau = [i for i in items[: items.index(points[0])] if isinstance(i, str)]
    tail_start = items.index(points[-1]) + 1
    passages: list[ParsedPassage] = []
    if chapeau:
        passages.append(ParsedPassage(refs.make(f"{base_ref}-intro"), kind, heading, "\n".join(chapeau)))
    for point in points:
        lines = _flatten([point])
        if point is points[-1]:
            lines += _flatten(items[tail_start:])
        intro = f" : {chapeau[0]}" if chapeau else ""
        passages.append(
            ParsedPassage(
                refs.make(f"{base_ref}-{_label(point.label)}"),
                "point",
                f"{heading}, point {_label(point.label)}{intro}"[:500],
                "\n".join(lines),
            )
        )
    return passages


def parse_articles_and_annexes(xhtml: str, code: str, max_chars: int = MAX_CHARS) -> list[ParsedPassage]:
    soup = BeautifulSoup(xhtml, "lxml")
    _clean(soup)
    refs = _Refs()
    out: list[ParsedPassage] = []

    for art in soup.find_all("div", id=_ARTICLE_ID):
        number = _ARTICLE_ID.match(str(art["id"])).group(1)  # type: ignore[union-attr]
        title = art.find(class_=lambda c: bool(c) and bool(set(str(c).split()) & _TITLE_CLASSES))
        subtitle = art.find(class_=lambda c: bool(c) and bool(set(str(c).split()) & _SUBTITLE_CLASSES))
        heading = _norm(title.get_text(" ")) if title else f"Article {number}"
        if subtitle:
            heading += f" — {_norm(subtitle.get_text(' '))}"
        blocks = _paragraphs(art)
        if len(blocks) == 1 and blocks[0][0] is None:
            out += _split_points(f"{code}-ART-{number}", heading, blocks[0][1], refs, max_chars, "article")
            continue
        for label, items in blocks:
            out += _split_points(
                f"{code}-ART-{number}-{label}", f"{heading}, paragraphe {label}", items, refs, max_chars,
                "paragraphe",
            )

    for annex in soup.find_all("div", id=_ANNEX_ID):
        name = _ANNEX_ID.match(str(annex["id"])).group(1)  # type: ignore[union-attr]
        lines = _flatten(_items(annex, keep_points=False))
        if not lines:
            continue
        heading = lines[0] if lines[0].upper().startswith("ANNEXE") else f"ANNEXE {name}"
        chunk: list[str] = []
        index = 0
        for line in lines + [""]:
            if line and (not chunk or sum(len(x) for x in chunk) + len(line) <= max_chars):
                chunk.append(line)
                continue
            if chunk:
                index += 1
                out.append(ParsedPassage(refs.make(f"{code}-ANX-{name}-{index}"), "annexe", heading,
                                         "\n".join(chunk)))
            chunk = [line] if line else []
    return out


def parse_recitals(xhtml: str, code: str) -> list[ParsedPassage]:
    soup = BeautifulSoup(xhtml, "lxml")
    _clean(soup)
    refs = _Refs()
    out = []
    for rct in soup.find_all("div", id=_RECITAL_ID):
        number = _RECITAL_ID.match(str(rct["id"])).group(1)  # type: ignore[union-attr]
        text = _text(_items(rct, keep_points=False))
        if text:
            ref = refs.make(f"{code}-RCT-{number}")
            out.append(ParsedPassage(ref, "considerant", f"Considérant {number}", text))
    return out
