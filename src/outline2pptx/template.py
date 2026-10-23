"""Reads a template's first master and sorts its layouts into roles the model can pick."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from io import BytesIO

from lxml import etree
from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT

from . import grid
from .schemas import SELECTABLE_ROLES

EMU_PER_INCH = 914400
EMU_PER_PT = 12700
MARGIN_TEXT_PT = 12.0
BODY_MIN_HEIGHT = EMU_PER_INCH
MAX_WORDS = {"heading": 10, "subheading": 8, "body": 120}
_NOT_FILLED = {"DATE", "FOOTER", "SLIDE_NUMBER"}
# The names a template gives its closing and its divider layout, in English and in German.
# "end" carries its word boundaries: as a bare substring it also matches Agenda, Appendix,
# Calendar, Trends and Legend, which are ordinary content layouts.
_CLOSING_RE = re.compile(r"abschluss|danke|closing|thank|\bend(?:e|ing)?\b", re.I)
_SECTION_RE = re.compile(r"abschnitt|section", re.I)
_LVL1 = re.compile(r"<a:lvl1pPr(?:\s[^>]*[^/])?>(.*?)</a:lvl1pPr>", re.S)
_SZ = re.compile(r"\ssz=\"(\d+)\"")
_ANY_SZ = re.compile(r"<a:(?:defRPr|rPr|endParaRPr)[^>]*?\ssz=\"(\d+)\"")
_CAPS = re.compile(r"<a:(?:defRPr|rPr)[^>]*?\scap=\"all\"")
_BOLD = re.compile(r"<a:(?:defRPr|rPr)[^>]*?\sb=\"1\"")
_BODY_PR = re.compile(r"<a:bodyPr[^>]*>")
_INS = {"l": "lIns", "r": "rIns", "t": "tIns", "b": "bIns"}
# What PowerPoint uses when the shape names no inset of its own.
_INSET_H_STD = 91440
_INSET_V_STD = 45720


@dataclass
class Field:
    idx: int
    kind: str
    ph_type: str
    left: int
    top: int
    width: int
    height: int
    size_pt: float = 0.0
    is_object: bool = False
    words: int = 0
    # Long words overrun a word budget, a heading gets a character cap on top.
    chars: int = 0
    caps: bool = False
    bold: bool = False
    # Left plus right inset, and the one on the side the text is anchored to.
    inset_h: int = 2 * _INSET_H_STD
    inset_v: int = _INSET_V_STD
    # Where the text sits and how far it keeps from top and bottom, to find where a heading really ends.
    anchor: str = "t"
    inset_top: int = _INSET_V_STD
    inset_bottom: int = _INSET_V_STD
    # A fixed line pitch the template sets, 0 when lines follow the font size.
    line_pt: float = 0.0

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height else 1.0


@dataclass
class Layout:
    index: int
    name: str
    role: str | None
    fields: list[Field] = field(default_factory=list)

    def of_kind(self, kind: str) -> list[Field]:
        """Fields of one kind, left to right, then top to bottom."""
        return sorted((f for f in self.fields if f.kind == kind), key=lambda f: (f.left, f.top))


@dataclass
class Analysis:
    width: int
    height: int
    typeface: str
    layouts: list[Layout] = field(default_factory=list)
    roles: dict[str, list[int]] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)

    def layout(self, index: int) -> Layout:
        return next(l for l in self.layouts if l.index == index)

    def has_image_fields(self) -> bool:
        return any(f.kind == "picture" for l in self.layouts for f in l.fields)


def to_dict(a: Analysis) -> dict:
    return asdict(a)


def from_dict(d: dict) -> Analysis:
    layouts = [Layout(index=l["index"], name=l["name"], role=l["role"],
                      fields=[Field(**f) for f in l["fields"]]) for l in d["layouts"]]
    return Analysis(width=d["width"], height=d["height"], typeface=d["typeface"], layouts=layouts,
                   roles={k: list(v) for k, v in d["roles"].items()},
                   skipped=list(d.get("skipped", [])))


def analyse(source: bytes | str) -> Analysis:
    prs = Presentation(BytesIO(source) if isinstance(source, bytes) else source)
    master = prs.slide_masters[0]
    title_pt, text_pt = _master_sizes(master)
    a = Analysis(width=prs.slide_width, height=prs.slide_height, typeface=_typeface(master))
    for i, layout in enumerate(master.slide_layouts):
        a.layouts.append(Layout(index=i, name=layout.name, role=None,
                                fields=_fields(layout, title_pt, text_pt)))
    _assign_roles(a)
    return a


def selectable_roles(a: Analysis) -> list[str]:
    return sorted(r for r in a.roles if r in SELECTABLE_ROLES)


def layout_for(a: Analysis, role: str, counter: dict[str, int]) -> Layout:
    """The next layout of the role, rotating so neighbours of one role look different."""
    candidates = a.roles.get(role) or a.roles.get("text") or [a.layouts[0].index]
    n = counter.get(role, 0)
    counter[role] = n + 1
    return a.layout(candidates[n % len(candidates)])


def spec_for(l: Layout, a: Analysis) -> dict:
    """What the model has to fill for this layout, with the word limit of every field."""
    body_fields = l.of_kind("body")
    kinds = ["bullets"]
    room: dict = {}
    # A table, chart or drawn element needs the whole slide, beside pictures it would be squeezed.
    if body_fields and body_fields[0].is_object and not l.of_kind("picture"):
        kinds += ["table", "chart", "cards", "bars", "highlight", "steps", "figures", "levels", "symbols"]
        if not a.has_image_fields():
            kinds.append("image")
        f = body_fields[0]
        room = {"cards": grid.card_space(f.width, f.height, f.size_pt),
                 "bars": grid.bar_space(f.height, f.size_pt),
                 "steps": grid.step_space(f.width, f.size_pt),
                 "figures": grid.figure_space(f.width, f.size_pt),
                 "levels": grid.level_space(f.width, f.height, f.size_pt),
                 "symbols": grid.symbol_space(f.width, f.height, f.size_pt)}
    return {
        **room,
        "heading": next((f.words for f in l.of_kind("heading")), 8),
        "heading_chars": next((f.chars for f in l.of_kind("heading")), 0),
        "subheading": [f.words for f in l.of_kind("subheading")],
        "bodies": [f.words for f in body_fields],
        "images": len(l.of_kind("picture")),
        "body_kinds": kinds,
    }


def _xml(el) -> str:
    return etree.tostring(el).decode("utf8", "ignore")


def _own_font_size(xml: str) -> float | None:
    lvl1 = _LVL1.search(xml)
    if lvl1:
        m = _SZ.search(lvl1.group(1))
        if m:
            return int(m.group(1)) / 100
    m = _ANY_SZ.search(xml)
    return int(m.group(1)) / 100 if m else None


def _weight(xml: str) -> tuple[bool, bool]:
    """Small caps and bold, both widen the text far beyond what its plain form measures."""
    return bool(_CAPS.search(xml)), bool(_BOLD.search(xml))


def _frame(xml: str) -> tuple[str, int, int]:
    """Anchor, top inset and bottom inset of the shape's text body."""
    tag = _BODY_PR.search(xml)
    if not tag:
        return "t", _INSET_V_STD, _INSET_V_STD
    anchor = re.search(r'\sanchor="(\w+)"', tag.group(0))

    def value(side: str) -> int:
        m = re.search(rf'\s{_INS[side]}="(\d+)"', tag.group(0))
        return int(m.group(1)) if m else _INSET_V_STD

    return (anchor.group(1) if anchor else "t"), value("t"), value("b")


def _line_spacing(xml: str) -> float:
    """A fixed line pitch in points from the first level's spacing, 0 when it is relative."""
    lvl1 = _LVL1.search(xml)
    m = re.search(r"<a:lnSpc>\s*<a:spcPts val=\"(\d+)\"", lvl1.group(1)) if lvl1 else None
    return int(m.group(1)) / 100 if m else 0.0


def _insets(xml: str) -> tuple[int, int]:
    """Left plus right inset, and the one the text is pushed away from by its anchor."""
    tag = _BODY_PR.search(xml)
    if not tag:
        return 2 * _INSET_H_STD, _INSET_V_STD

    def value(side: str, standard: int) -> int:
        m = re.search(rf'\s{_INS[side]}="(\d+)"', tag.group(0))
        return int(m.group(1)) if m else standard

    anchor = re.search(r'\sanchor="(\w+)"', tag.group(0))
    top, bottom = value("t", _INSET_V_STD), value("b", _INSET_V_STD)
    name = anchor.group(1) if anchor else "t"
    vertical = bottom if name == "b" else top + bottom if name == "ctr" else top
    return value("l", _INSET_H_STD) + value("r", _INSET_H_STD), vertical


def _master_sizes(master) -> tuple[float, float]:
    xml = _xml(master._element)

    def style(tag: str) -> float:
        m = re.search(rf"<p:{tag}>.*?<a:lvl1pPr[^>]*>.*?\ssz=\"(\d+)\"", xml, re.S)
        return int(m.group(1)) / 100 if m else 18.0

    return style("titleStyle"), style("bodyStyle")


def _typeface(master) -> str:
    try:
        theme = master.part.part_related_by(RT.THEME).blob.decode("utf8", "ignore")
    except Exception:
        return "Calibri"
    m = re.search(r"<a:minorFont>\s*<a:latin typeface=\"([^\"]+)\"", theme)
    return m.group(1) if m and not m.group(1).startswith("+") else "Calibri"


def _char_budget(f: Field) -> int:
    width_pt = f.width / EMU_PER_PT - 36
    height_pt = f.height / EMU_PER_PT - 7
    # Measured on Carlito: caps cost 17 percent width, bold another 2, and a budget
    # that ignores them lets the model write a title that wraps into the line below.
    char_width = 0.5 * (1.17 if f.caps else 1.0) * (1.02 if f.bold else 1.0)
    chars_per_line = max(10.0, width_pt / (f.size_pt * char_width))
    lines = max(1, int(height_pt / (f.size_pt * 1.2)))
    return int(chars_per_line * lines)


def _word_budget(f: Field) -> int:
    return max(2, min(MAX_WORDS.get(f.kind, 120), int(_char_budget(f) / 6.5)))


def _fields(layout, title_pt: float, text_pt: float) -> list[Field]:
    raw: list[Field] = []
    for sh in layout.placeholders:
        pf = sh.placeholder_format
        ph_type = str(pf.type).split(" ")[0]
        if ph_type in _NOT_FILLED:
            continue
        if ph_type == "PICTURE":
            raw.append(Field(pf.idx, "picture", ph_type, sh.left, sh.top, sh.width, sh.height))
            continue
        xml = _xml(sh._element)
        size = _own_font_size(xml)
        if size is None:
            size = title_pt if ph_type in ("TITLE", "CENTER_TITLE") else text_pt
        caps, bold = _weight(xml)
        inset_h, inset_v = _insets(xml)
        anchor, inset_top, inset_bottom = _frame(xml)
        raw.append(Field(pf.idx, "", ph_type, sh.left, sh.top, sh.width, sh.height,
                        size_pt=size, is_object=ph_type == "OBJECT", caps=caps, bold=bold,
                        inset_h=inset_h, inset_v=inset_v, anchor=anchor, inset_top=inset_top,
                        inset_bottom=inset_bottom, line_pt=_line_spacing(xml)))
    texts = [f for f in raw if f.kind == ""]
    if texts:
        largest = max(f.size_pt for f in texts)
        taken = False
        for f in texts:
            if not taken and f.size_pt == largest:
                f.kind, taken = "heading", True
            elif f.size_pt <= MARGIN_TEXT_PT or f.size_pt <= text_pt * 0.75:
                f.kind = "margin_text"
            elif f.ph_type == "SUBTITLE":
                # A subtitle is as tall as a body in the stock Office master, only its type tells them apart.
                f.kind = "subheading"
            elif f.height >= BODY_MIN_HEIGHT:
                f.kind = "body"
            else:
                f.kind = "subheading"
            f.words = _word_budget(f) if f.kind != "margin_text" else 0
            f.chars = _char_budget(f) if f.kind == "heading" else 0
    return raw


def _signature(l: Layout) -> tuple:
    return tuple(sorted(f.kind for f in l.fields))


def _role(l: Layout, first: Layout) -> str | None:
    kinds = [f.kind for f in l.fields]
    if l is first:
        return "cover"
    if "heading" not in kinds:
        return None
    if _CLOSING_RE.search(l.name):
        return "closing"
    if _SECTION_RE.search(l.name):
        return "section"
    if _signature(l) == _signature(first):
        return "cover"
    f, b = kinds.count("body"), kinds.count("picture")
    if f == 0 and b == 0:
        return "section"
    if b == 0:
        return "text" if f == 1 else "two_columns"
    return "text_with_image" if f else "image_full"


def _assign_roles(a: Analysis) -> None:
    if not a.layouts:
        return
    first = a.layouts[0]
    for l in a.layouts:
        l.role = _role(l, first)
        if l.role is None:
            a.skipped.append(l.name)
        else:
            a.roles.setdefault(l.role, []).append(l.index)
    # The rotation meets the layouts with fewer pictures first, a short deck waits on fewer images.
    for role in SELECTABLE_ROLES:
        if role in a.roles:
            a.roles[role].sort(key=lambda i: len(a.layout(i).of_kind("picture")))
    # A section divider with a picture is a slide of picture and title alone, the plain ones win where the template has them.
    plain = [i for i in a.roles.get("section", []) if not a.layout(i).of_kind("picture")]
    if plain:
        a.roles["section"] = plain
    if "closing" not in a.roles:
        covers = a.roles.get("cover", [first.index])
        a.roles["closing"] = [covers[1] if len(covers) > 1 else covers[0]]
