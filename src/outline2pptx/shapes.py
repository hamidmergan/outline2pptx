"""Cards, bars and the highlight box, drawn from shapes and laid out for whatever count they hold."""

from __future__ import annotations

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu

from . import colors as fb
from . import icons, grid
from .elements import _SLACK, MIN_PT, LINE_RATIO, font_for, style_run, hard_lines
from .colors import Palette
from .schemas import Bar, Body, Card
from .template import EMU_PER_PT, Field

# Corner radius of a card as a share of its shorter side, as in the example deck.
_CORNER = 0.06
# A card's height against its width when the field has room, as in the example deck.
_MIN_ASPECT = 0.5
# Icon edge in multiples of the title size, and the paddings in multiples of the base size.
_ICON = 1.7
_PAD = 1.2
_STEP = 0.05
# A bar's label column never takes more than this share of the field.
_MAX_LABEL_SHARE = 0.4
# Bar rows at their roomiest: pitch and bar height in multiples of the label size.
_MAX_ROW_PITCH = 3.2
_BAR_RATIO = 0.62
# The highlight box beside its sentence, and the size of that sentence against the body text.
_BOX_WIDTH = 0.3
_BOX_ASPECT = 0.86
_STATEMENT_RATIO = 1.9
_MAX_STATEMENT_PT = 36.0
_BLACK = RGBColor(0, 0, 0)
# Whole numbers in this range are read as years, the unit deadlines and durations arrive in.
_YEARS = (1900, 2200)


def _emu(pt: float) -> Emu:
    return Emu(int(pt * EMU_PER_PT))


def _textbox(slide, x: float, y: float, w: float, h: float, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT):
    """A bare text box in points: no margins, no autofit, so the measured layout is what renders."""
    box = slide.shapes.add_textbox(_emu(x), _emu(y), _emu(w), _emu(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    tf.paragraphs[0].alignment = align
    return tf


def _shape(slide, kind, x: float, y: float, w: float, h: float, color, ecke: float | None = None):
    form = _fill(slide.shapes.add_shape(kind, _emu(x), _emu(y), _emu(w), _emu(h)), color)
    if ecke is not None:
        form.adjustments[0] = ecke
    return form


def _fill(form, color):
    form.fill.solid()
    form.fill.fore_color.rgb = color
    form.line.fill.background()
    # The theme's shape style brings shadows LibreOffice draws despite an empty effect list, fill and line are set here.
    style = form._element.find(qn("p:style"))
    if style is not None:
        form._element.remove(style)
    return form


def _lines(text: str, typeface: str, size: float, width: float, bold: bool = False) -> int:
    return hard_lines(text, font_for(typeface, size, bold), width * _SLACK) if text else 0


# Cards


def cards(slide, field: Field, cards_: list[Card], f: Palette, typeface: str) -> None:
    """Rows of equal cards in the grid that keeps the text largest, the last row centred."""
    typeface = typeface or "Calibri"
    g = grid.base_pt(field.size_pt)
    width = field.width / EMU_PER_PT
    gap = grid.GAP * g
    rows, card_w, (title_pt, text_pt, pad, icon, card_h) = _card_grid(cards_, field, g, typeface)
    color_hex = str(f.tint(fb.FULL))
    y = field.top / EMU_PER_PT
    k = 0
    for count in rows:
        x = field.left / EMU_PER_PT + (width - count * card_w - (count - 1) * gap) / 2
        for card in cards_[k:k + count]:
            _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, card_w, card_h, f.tint(fb.AREA), _CORNER)
            slide.shapes.add_picture(icons.picture(card.icon, color_hex), _emu(x + pad), _emu(y + pad),
                                     _emu(icon), _emu(icon))
            inner = card_w - 2 * pad
            top = y + pad + icon + 0.5 * title_pt
            title_h = _lines(card.title, typeface, title_pt, inner, True) * title_pt * LINE_RATIO
            tf = _textbox(slide, x + pad, top, inner, title_h)
            run = tf.paragraphs[0].add_run()
            run.text = card.title
            style_run(run, title_pt, f.text_color(), True, typeface)
            if card.text:
                top += title_h + 0.3 * text_pt
                tf = _textbox(slide, x + pad, top, inner, y + card_h - pad - top)
                run = tf.paragraphs[0].add_run()
                run.text = card.text
                style_run(run, text_pt, _BLACK, False, typeface)
            x += card_w + gap
        k += count
        y += card_h + gap


def _card_grid(cards_: list[Card], field: Field, g: float, typeface: str) -> tuple[list[int], float, tuple]:
    """Cards per row, card width and measures, for the column count at which the text stays largest.

    The widest grid the field offers comes first, a grid with more columns wins only with larger
    text. When no grid fits, the one that overflows least is taken.
    """
    width, height = field.width / EMU_PER_PT, field.height / EMU_PER_PT
    gap = grid.GAP * g
    columns_max, _ = grid.card_grid(field.width, field.height, field.size_pt)
    best, fallback = None, None
    for columns in range(min(columns_max, len(cards_)), len(cards_) + 1):
        rows = grid.distribution(len(cards_), columns)
        card_w = (width - gap * (max(rows) - 1)) / max(rows)
        fits, factor, mass = _card_metrics(cards_, card_w, height, len(rows), gap, g, typeface)
        candidate = (rows, card_w, mass)
        if fits and (best is None or factor > best[0] + 1e-9):
            best = (factor, candidate)
        overflow = len(rows) * mass[4] + (len(rows) - 1) * gap - height
        if fallback is None or overflow < fallback[0] - 1e-9:
            fallback = (overflow, candidate)
    return (best or fallback)[1]


def _card_metrics(cards_: list[Card], card_w: float, height: float, rows: int, gap: float, g: float,
                typeface: str) -> tuple[bool, float, tuple[float, float, float, float, float]]:
    """Whether the rows fit, at which scale, and title size, text size, padding, icon edge and card height.

    The text starts at the template's body size and shrinks until every card fits without a broken
    word. A card is at least half as tall as it is wide when the field has the room, so two cards do
    not sit as thin strips above an empty slide.
    """
    room = (height - (rows - 1) * gap) / rows
    factor = 1 / grid.TEXT_RATIO
    while True:
        title_pt = grid.TITLE_RATIO * g * factor
        text_pt = grid.TEXT_RATIO * g * factor
        pad = _PAD * g * factor
        icon = _ICON * title_pt
        inner = card_w - 2 * pad
        title_font, text_font = font_for(typeface, title_pt, True), font_for(typeface, text_pt)
        whole = all(title_font.getlength(w) <= inner * _SLACK for k in cards_ for w in k.title.split()) and all(
            text_font.getlength(w) <= inner * _SLACK for k in cards_ for w in k.text.split())
        card_h = 0.0
        for k in cards_:
            h = 2 * pad + icon + 0.5 * title_pt + _lines(k.title, typeface, title_pt, inner, True) * title_pt * LINE_RATIO
            if k.text:
                h += 0.3 * text_pt + _lines(k.text, typeface, text_pt, inner) * text_pt * LINE_RATIO
            card_h = max(card_h, h)
        if whole and card_h <= room:
            return True, factor, (title_pt, text_pt, pad, icon, max(card_h, min(room, card_w * _MIN_ASPECT)))
        if text_pt - _STEP * g < MIN_PT:
            return False, factor, (title_pt, text_pt, pad, icon, card_h)
        factor -= _STEP


# Bars


def _num(value: float) -> str:
    return f"{value:g}"


def _baseline(values: list[float]) -> float:
    """Zero for amounts, for years the one before the earliest, so 2028 against 2030 does not read as 99 percent."""
    if values and all(float(w).is_integer() and _YEARS[0] <= w <= _YEARS[1] for w in values):
        return min(values) - 1
    return 0.0


def bars(slide, field: Field, bars_: list[Bar], f: Palette, typeface: str) -> None:
    """Label left, a track in the light tint, the bar in full colour, its length measured on the largest value."""
    typeface = typeface or "Calibri"
    g = grid.base_pt(field.size_pt)
    width, height = field.width / EMU_PER_PT, field.height / EMU_PER_PT
    left, top = field.left / EMU_PER_PT, field.top / EMU_PER_PT
    n = len(bars_)
    size = g
    while True:
        column = min(width * _MAX_LABEL_SHARE,
                     max(font_for(typeface, size).getlength(b.label) for b in bars_) / _SLACK + size)
        step = min(height / n, _MAX_ROW_PITCH * size)
        lines = max(_lines(b.label, typeface, size, column - size) for b in bars_)
        if lines * size * LINE_RATIO <= step * 0.95 or size - 1 < MIN_PT:
            break
        size -= 1
    thickness = min(step * _BAR_RATIO, 2 * size)
    track_x = left + column
    track_w = width - column
    base = _baseline([b.value for b in bars_])
    largest = max((b.value for b in bars_), default=0.0) - base
    value_pt = max(MIN_PT, size * 0.85)
    for i, b in enumerate(bars_):
        middle = top + step * (i + 0.5)
        tf = _textbox(slide, left, middle - step / 2, column - size, step, MSO_ANCHOR.MIDDLE)
        run = tf.paragraphs[0].add_run()
        run.text = b.label
        style_run(run, size, _BLACK, False, typeface)
        y = middle - thickness / 2
        _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, track_x, y, track_w, thickness, f.tint(fb.LINE), 0.5)
        ratio = (b.value - base) / largest if largest > 0 else 0.0
        length = max(thickness, track_w * max(0.0, min(1.0, ratio)))
        _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, track_x, y, length, thickness, f.tint(fb.FULL), 0.5)
        text = b.text or _num(b.value)
        text_w = font_for(typeface, value_pt, True).getlength(text) + thickness
        if text_w <= length:
            tf = _textbox(slide, track_x, y, length, thickness, MSO_ANCHOR.MIDDLE, PP_ALIGN.CENTER)
            color = f.text_on()
        else:
            tf = _textbox(slide, track_x + length + thickness / 3, y, max(text_w, track_w - length - thickness / 3), thickness,
                           MSO_ANCHOR.MIDDLE)
            color = f.text_color()
        run = tf.paragraphs[0].add_run()
        run.text = text
        style_run(run, value_pt, color, True, typeface)


# Highlight


def highlight(slide, field: Field, body: Body, f: Palette, typeface: str) -> None:
    """A box in full colour with the key word, beside it the sentence with its one term in colour."""
    typeface = typeface or "Calibri"
    g = grid.base_pt(field.size_pt)
    width, height = field.width / EMU_PER_PT, field.height / EMU_PER_PT
    left, top = field.left / EMU_PER_PT, field.top / EMU_PER_PT
    box_w = width * _BOX_WIDTH
    box_h = min(height, box_w * _BOX_ASPECT)
    box_x = left + width - box_w
    _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, box_x, top, box_w, box_h, f.tint(fb.FULL), _CORNER)
    key_pt = box_h * 0.6
    while key_pt > MIN_PT and (font_for(typeface, key_pt, True).getlength(body.key) > box_w * 0.85
                               or key_pt * LINE_RATIO > box_h * 0.9):
        key_pt -= 1
    tf = _textbox(slide, box_x, top, box_w, box_h, MSO_ANCHOR.MIDDLE, PP_ALIGN.CENTER)
    tf.word_wrap = False
    run = tf.paragraphs[0].add_run()
    run.text = body.key
    style_run(run, key_pt, f.text_on(), True, typeface)

    text_w = width - box_w - 1.5 * g
    size = min(_MAX_STATEMENT_PT, _STATEMENT_RATIO * g)
    while size > MIN_PT and _lines(body.text, typeface, size, text_w, True) * size * LINE_RATIO > box_h:
        size -= 1
    tf = _textbox(slide, left, top, text_w, box_h, MSO_ANCHOR.MIDDLE)
    for part, marked in _parts(body.text, body.emphasis):
        run = tf.paragraphs[0].add_run()
        run.text = part
        style_run(run, size, f.text_color() if marked else _BLACK, marked, typeface)


def _parts(text: str, marked: str) -> list[tuple[str, bool]]:
    """The sentence split around the first place the term occurs, ignoring case."""
    pos = text.lower().find(marked.lower()) if marked.strip() else -1
    if pos < 0:
        return [(text, False)]
    end = pos + len(marked)
    return [(t, b) for t, b in ((text[:pos], False), (text[pos:end], True), (text[end:], False)) if t]
