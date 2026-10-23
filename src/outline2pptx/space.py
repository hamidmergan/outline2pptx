"""Room below a slide's heading: measured on the heading's real text, so a long one pushes the content down."""

from __future__ import annotations

from dataclasses import replace

from .split import lines
from .template import EMU_PER_PT, Field
from .fonts import load_font

# Air between the heading's last line and the content, in lines of the content's own text.
AIR_LINES = 1.0
_ZEILE = 1.2
# A content area keeps at least this share of its height however far a long heading pushes it.
_MIN_REMAINING = 0.5
_BELOW_HEAD = ("body", "subheading", "picture")


def line_height(field: Field, size: float) -> float:
    """Line pitch in points: the template's fixed pitch scaled with the font, else the usual 1.2."""
    if field.line_pt and field.size_pt:
        return field.line_pt * size / field.size_pt
    return size * _ZEILE


def head_lines(text: str, field: Field, typeface: str, size: float) -> int:
    measured = text.upper() if field.caps else text
    font = load_font(f"{typeface}:bold" if field.bold else typeface, round(size))
    return lines([measured], font, (field.width - field.inset_h) / EMU_PER_PT)


def head_bottom(field: Field, text: str, typeface: str, size: float) -> int:
    """Where the heading's text ends on the slide, below its box when it runs over."""
    height = int(head_lines(text, field, typeface, size) * line_height(field, size) * EMU_PER_PT)
    if field.anchor == "b":
        return field.top + field.height - field.inset_bottom
    if field.anchor == "ctr":
        return field.top + (field.height + height) // 2
    return field.top + field.inset_top + height


def below(fields: list[Field], head: Field) -> list[Field]:
    return [f for f in fields if f.kind in _BELOW_HEAD and f.top >= head.top + head.height // 2]


def moved(fields: list[Field], head: Field, bottom: int, air: int, slide_height: int) -> dict[int, Field]:
    """The fields below the heading moved so they start ``air`` below its text, by placeholder index.

    The area keeps its bottom and gets shorter, down to half its height, beyond that it moves as a
    whole. A row of subheadings alone only ever moves, it has no height to give.
    """
    beneath = below(fields, head)
    if not beneath:
        return {}
    oben_alt = min(f.top for f in beneath)
    unten_alt = max(f.top + f.height for f in beneath)
    target = bottom + air
    if target <= oben_alt:
        return {}
    spanne = unten_alt - oben_alt
    ratio = 1.0 if all(f.kind == "subheading" for f in beneath) else _MIN_REMAINING
    moved_fields = max(unten_alt - target, int(spanne * ratio))
    moved_fields = max(0, min(moved_fields, slide_height - target))
    factor = moved_fields / spanne if spanne else 1.0
    return {f.idx: replace(f, top=target + int((f.top - oben_alt) * factor), height=int(f.height * factor))
            for f in beneath}


def air(fields: list[Field]) -> int:
    """One line of the content's own text, taken from the first text field below the heading."""
    size = next((f.size_pt for f in fields if f.kind == "body" and f.size_pt), 0.0) or next(
        (f.size_pt for f in fields if f.kind == "subheading" and f.size_pt), 16.0)
    return int(AIR_LINES * size * _ZEILE * EMU_PER_PT)
