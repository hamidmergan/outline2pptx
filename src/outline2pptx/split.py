"""Splits an overfull slide in two when both halves keep enough points, else the text shrinks."""

from __future__ import annotations

import re

from .schemas import Body, Column, Slide
from .template import EMU_PER_PT, Analysis, Field
from .fonts import load_font

_INSET_PT = 36.0
_BULLET_PT = 22.0
_ZEILE = 1.2
# A slide with fewer points is not worth showing, a field beside another needs fewer.
MIN_BULLETS = 5
MIN_BULLETS_PER_COLUMN = 3
# Shrinking stops here, below this a room at the back can no longer read the text.
MIN_FONT_PT = 12


_ID = re.compile(r"^s(\d+)$")


def new_id(ids: set[str]) -> str:
    """The next free slide id, counting past the highest one ever used."""
    highest = max((int(m.group(1)) for i in ids if (m := _ID.match(i))), default=0)
    return f"s{highest + 1}"


def lines(items: list[str], font, width_pt: float) -> int:
    """Greedy word wrap over every point, the same way PowerPoint breaks lines."""
    n = 0
    for item in items:
        n += 1
        current = 0.0
        for word in item.split():
            w = font.getlength(word)
            leer = font.getlength(" ") if current else 0.0
            if current and current + leer + w > width_pt:
                n += 1
                current = w
            else:
                current += leer + w
    return n


def fits(items: list[str], field: Field, typeface: str, size: float | None = None) -> bool:
    if not items:
        return True
    size = size or field.size_pt
    font = load_font(typeface, round(size))
    width = field.width / EMU_PER_PT - _INSET_PT - _BULLET_PT
    height = field.height / EMU_PER_PT - 7.0
    return lines(items, font, width) * size * _ZEILE <= height


def font_size(items: list[str], field: Field, typeface: str) -> float | None:
    """The largest size at which the points fit, None when the field's own size already does."""
    if fits(items, field, typeface):
        return None
    size = float(round(field.size_pt)) - 1
    while size > MIN_FONT_PT and not fits(items, field, typeface, size):
        size -= 1
    return max(size, MIN_FONT_PT)


def _narrowest(a: Analysis, role: str, n: int) -> list[Field] | None:
    """Per position the smallest text field across the layouts of the role, the safe measure."""
    candidates = [a.layout(i).of_kind("body") for i in a.roles.get(role, [])]
    candidates = [k for k in candidates if len(k) >= n]
    if not candidates:
        return None
    return [min((k[i] for k in candidates), key=lambda f: f.width * f.height) for i in range(n)]


def _fields(s: Slide, a: Analysis, n: int) -> list[Field] | None:
    """The slide's own text fields once its layout is fixed, else the narrowest of its role."""
    if s.layout is not None:
        layout = next((l for l in a.layouts if l.index == s.layout), None)
        own = layout.of_kind("body") if layout else []
        if len(own) >= n:
            return own[:n]
    return _narrowest(a, s.role, n)


_IMAGE_ROLES = ("text_with_image", "image_full")
# A sentence ends behind a word of three or more characters, so abbreviations stay whole.
_SENTENCE_END = re.compile(r"(?<=\w{3}[.!?])\s+")


def split_notes(notes: str, ratio: float) -> tuple[str, str]:
    """The notes cut at the sentence end nearest the share of points the first half keeps, each half keeps at least one sentence."""
    sentences = _SENTENCE_END.split(notes.strip())
    if len(sentences) < 2:
        return notes, notes
    target = ratio * len(notes)
    stand, schnitt, gap = 0, 1, float("inf")
    for i, satz in enumerate(sentences[:-1], 1):
        stand += len(satz) + 1
        if abs(stand - target) < gap:
            schnitt, gap = i, abs(stand - target)
    return " ".join(sentences[:schnitt]), " ".join(sentences[schnitt:])


def _rest_shape(s: Slide, a: Analysis) -> tuple[str, int | None]:
    """Role and layout of a split-off part, a picture slide's rest carries text only."""
    if s.role not in _IMAGE_ROLES:
        return s.role, s.layout
    role = "two_columns" if s.columns else "text"
    candidates = a.roles.get(role) or []
    return role, (candidates[0] if candidates else None)


def _cut_off(s: Slide, a: Analysis) -> Slide | None:
    """Moves the second half of the points to a new slide, None when everything fits."""
    if s.body and s.body.kind == "bullets" and len(s.body.items) >= 2 * MIN_BULLETS:
        fields = _fields(s, a, 1)
        if fields and not fits(s.body.items, fields[0], a.typeface):
            middle = (len(s.body.items) + 1) // 2
            # Each half speaks about its own points, no slide may end up without speaker text.
            s.notes, rest_notes = split_notes(s.notes, middle / len(s.body.items))
            role, layout = _rest_shape(s, a)
            rest = Slide(role=role, layout=layout, title=s.title, notes=rest_notes,
                         body=Body(kind="bullets", items=s.body.items[middle:]))
            s.body.items = s.body.items[:middle]
            return rest
    if s.columns and all(len(c.items) >= 2 * MIN_BULLETS_PER_COLUMN for c in s.columns):
        fields = _fields(s, a, len(s.columns))
        if fields and any(not fits(c.items, f, a.typeface) for c, f in zip(s.columns, fields)):
            total = sum(len(c.items) for c in s.columns)
            s.notes, rest_notes = split_notes(
                s.notes, sum((len(c.items) + 1) // 2 for c in s.columns) / total)
            role, layout = _rest_shape(s, a)
            rest = Slide(role=role, layout=layout, title=s.title, notes=rest_notes, columns=[
                Column(heading=c.heading, items=c.items[(len(c.items) + 1) // 2:]) for c in s.columns])
            for c in s.columns:
                c.items = c.items[:(len(c.items) + 1) // 2]
            return rest
    return None


def split_overflow(slides: list[Slide], a: Analysis) -> list[Slide]:
    """Every slide is split until each part fits, the parts keep their order."""
    out: list[Slide] = []
    ids = {s.id for s in slides}
    for s in slides:
        stack = [s]
        while stack:
            current = stack.pop()
            rest = _cut_off(current, a)
            if rest is None:
                out.append(current)
                continue
            rest.id = new_id(ids)
            ids.add(rest.id)
            # The rest waits below the first half, so the first half is checked (and placed) first.
            stack.append(rest)
            stack.append(current)
    return out
