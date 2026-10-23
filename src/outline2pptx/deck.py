"""Builds the deck from the template: one slide per entry, only placeholders the layout has."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date
from io import BytesIO

import logging

from PIL import Image
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt

from . import bullets, colors, diagrams, elements, shapes, space, template
from .colors import Palette
from .schemas import Body, Slide
from .split import font_size, lines
from .template import EMU_PER_PT, Analysis, Field, Layout
from .fonts import load_font

log = logging.getLogger(__name__)

_NO_MARGIN_TEXT = ("cover", "closing")
# The notice in the bottom right corner: a fixed size, in dark grey.
NOTICE_PT = 10.0
NOTICE_GREY = RGBColor(0x59, 0x59, 0x59)
_NOTICE_WIDTH = Emu(3 * 914400)
_NOTICE_HEIGHT = Emu(int(0.25 * 914400))
_NOTICE_MARGIN = Emu(int(0.3 * 914400))
IMAGE_QUALITY = 90
# A heading may lose at most this much of its size, a longer title is the only cure below that.
_MIN_RATIO = 0.6
# A text field starting further right than this from the heading is indented on purpose, not by rounding.
_INDENT = 12 * EMU_PER_PT


def image_key(slide_id: str, slot: int | str) -> str:
    return f"{slide_id}_{slot}"


def layout_index(a: Analysis, s: Slide, counter: dict[str, int]) -> int:
    """The stored layout of a slide, or the next one of its role."""
    if s.layout is not None and any(l.index == s.layout for l in a.layouts):
        return s.layout
    return template.layout_for(a, s.role, counter).index


def build_deck(template_bytes: bytes, a: Analysis, slides: list[Slide], images: dict[str, bytes],
         title: str, notes: bool, notice: str = "", numbers: list[int] | None = None,
         date: str = "", presenter: str = "") -> bytes:
    """The deck, ``numbers`` gives each slide its number when only part of the deck is built."""
    prs = Presentation(BytesIO(template_bytes))
    _clear(prs)
    f = colors.from_template(prs, a)
    counter: dict[str, int] = {}
    for i, s in enumerate(slides):
        layout = a.layout(layout_index(a, s, counter))
        _slide(prs, layout, s, images, title, notes, f, notice, a.typeface)
        if s.role == "cover" and presenter:
            _fixed(prs.slides[-1], PP_PLACEHOLDER.FOOTER, presenter)
        if s.role != "cover":
            _slide_number(prs.slides[-1], numbers[i] if numbers else i + 1)
            if date:
                _fixed(prs.slides[-1], PP_PLACEHOLDER.DATE, date)
    out = BytesIO()
    prs.save(out)
    return out.getvalue()


def _clear(prs) -> None:
    liste = prs.slides._sldIdLst
    for sld in list(liste):
        prs.part.drop_rel(sld.rId)
        liste.remove(sld)


def _ph(slide, idx: int):
    try:
        return slide.placeholders[idx]
    except KeyError:
        return None


def _remove(shape) -> None:
    el = shape._element
    el.getparent().remove(el)


def _set_text(ph, paragraphs: list[str]) -> None:
    tf = ph.text_frame
    tf.text = paragraphs[0] if paragraphs else ""
    for z in paragraphs[1:]:
        p = tf.add_paragraph()
        p.text = z
        p.level = 0


def _set_bullets(ph, field: Field, items: list[str], typeface: str) -> None:
    """Bullet points, shrunk just enough to stay inside their field when they would run over."""
    _set_text(ph, items)
    bullets.add(ph)
    size = font_size(items, field, typeface) if typeface and field.size_pt > 0 else None
    if size is None:
        return
    for paragraph in ph.text_frame.paragraphs:
        for run in paragraph.runs:
            run.font.size = Pt(size)


def _fitting_size(text: str, field: Field, typeface: str) -> float | None:
    """The largest size up to the template's at which the text still fits, None when it already does.

    The template sizes its title for the words it expects. A longer one wraps into the
    line below, and on a cover that line is the subtitle.
    """
    if not text or not typeface or field.size_pt <= 0:
        return None
    width = (field.width - field.inset_h) / EMU_PER_PT
    height = (field.height - field.inset_v) / EMU_PER_PT
    if width <= 0 or height <= 0:
        return None
    # Caps and bold are what the layout really renders, the plain string measures far too narrow.
    measured = text.upper() if field.caps else text
    name = f"{typeface}:bold" if field.bold else typeface
    floor = max(8.0, field.size_pt * _MIN_RATIO)
    size = field.size_pt
    while True:
        try:
            font = load_font(name, round(size))
        except OSError as e:
            log.warning("Font measuring skipped, %s cannot be loaded: %s", name, e)
            return None
        if lines([measured], font, width) * space.line_height(field, size) <= height or size <= floor:
            break
        size = max(floor, size - 1.0)
    return None if size >= field.size_pt else size


def _set_heading(ph, field: Field, text: str, typeface: str) -> float:
    """A heading, shrunk just enough that it never reaches what sits below it, returns its size."""
    _set_text(ph, [text])
    size = _fitting_size(text, field, typeface)
    if size is None:
        return field.size_pt
    for paragraph in ph.text_frame.paragraphs:
        # A fixed line pitch would keep the lines as far apart as before and the shrinking would gain nothing.
        if field.line_pt:
            paragraph.line_spacing = Pt(space.line_height(field, size))
        for run in paragraph.runs:
            run.font.size = Pt(size)
    return size


def _crop(data: bytes, aspect: float) -> BytesIO:
    """Centre crop to the field's aspect, so a banner field never squeezes a square picture."""
    im = Image.open(BytesIO(data)).convert("RGB")
    w, h = im.size
    if w / h > aspect:
        nw = max(1, int(h * aspect))
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = max(1, int(w / aspect))
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    out = BytesIO()
    # JPEG, not PNG: eight painterly illustrations as PNG push a deck past 25 MB for no visible gain.
    im.save(out, format="JPEG", quality=IMAGE_QUALITY, optimize=True, progressive=True)
    out.seek(0)
    return out


def _slide(prs, layout: Layout, s: Slide, images: dict[str, bytes], title: str, notes: bool,
           f: Palette, notice: str = "", typeface: str = "") -> None:
    slide = prs.slides.add_slide(prs.slide_masters[0].slide_layouts[layout.index])
    used: set[int] = set()

    head_fields = layout.of_kind("heading")
    moved_fields: dict[int, Field] = {}
    if head_fields and s.title and (ph := _ph(slide, head_fields[0].idx)) is not None:
        size = _set_heading(ph, head_fields[0], s.title, typeface)
        used.add(head_fields[0].idx)
        if typeface:
            moved_fields = _space_below_heading(prs, slide, layout, head_fields[0], s, size, typeface)

    def placed(field: Field) -> Field:
        return moved_fields.get(field.idx, field)

    subheads = [placed(f) for f in layout.of_kind("subheading")]
    if s.role in _NO_MARGIN_TEXT:
        if subheads and s.subtitle and (ph := _ph(slide, subheads[0].idx)) is not None:
            _set_heading(ph, subheads[0], s.subtitle, typeface)
            used.add(subheads[0].idx)
    else:
        for field, col in zip(subheads, s.columns):
            if col.heading and (ph := _ph(slide, field.idx)) is not None:
                _set_heading(ph, field, col.heading, typeface)
                used.add(field.idx)

    body_fields = [placed(f) for f in layout.of_kind("body")]
    # A picture keeps its field, it was drawn for that field's shape.
    if len(body_fields) == 1 and s.body is not None and s.body.kind != "image" and head_fields and not layout.of_kind("picture"):
        body_fields = [_full_width(slide, body_fields[0], head_fields[0])]
    if len(body_fields) == 1 and s.body is not None:
        if _body(slide, body_fields[0], s.body, images.get(image_key(s.id, "body")), f, typeface):
            used.add(body_fields[0].idx)
    elif len(body_fields) > 1:
        for field, col in zip(body_fields, s.columns):
            if col.items and (ph := _ph(slide, field.idx)) is not None:
                _set_bullets(ph, field, col.items, typeface)
                used.add(field.idx)

    for k, field in enumerate(placed(f) for f in layout.of_kind("picture")):
        data = images.get(image_key(s.id, k))
        ph = _ph(slide, field.idx)
        if data and ph is not None:
            picture = ph.insert_picture(_crop(data, field.aspect))
            if field.idx in moved_fields:
                # Cropped to the moved field already, the placeholder's own crop was for the old one.
                picture.crop_left = picture.crop_right = picture.crop_top = picture.crop_bottom = 0
                _place(picture, field)
            used.add(field.idx)

    pad = sorted(layout.of_kind("margin_text"), key=lambda f: f.top)
    if pad and s.role not in _NO_MARGIN_TEXT and (ph := _ph(slide, pad[0].idx)) is not None:
        _set_text(ph, [title])
        used.add(pad[0].idx)

    for ph in list(slide.placeholders):
        if ph.placeholder_format.idx not in used:
            _remove(ph)

    if notice:
        _notice(prs, slide, notice, typeface)

    if notes and s.notes:
        slide.notes_slide.notes_text_frame.text = s.notes


_MONTHS = {
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "de": ("Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez."),
}


def date_text(language: str, day: date | None = None) -> str:
    """The day the deck is built, written the way its language writes dates."""
    day = day or date.today()
    months = _MONTHS.get(language, _MONTHS["en"])
    if language == "de":
        return f"{day.day:02d}.{day.month:02d}.{day.year}"
    return f"{months[day.month - 1]} {day.day}, {day.year}"


_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def _from_layout(slide, ph_type):
    """A copy of the layout's field of this type for the slide, python-pptx leaves these out."""
    model_level = next((ph for ph in slide.slide_layout.placeholders if ph.placeholder_format.type == ph_type), None)
    if model_level is None:
        return None
    el = deepcopy(model_level._element)
    el.nvSpPr.cNvPr.id = max((sh.shape_id for sh in slide.shapes), default=1) + 1
    slide.shapes._spTree.append(el)
    return el


def _space_below_heading(prs, slide, layout: Layout, head: Field, s: Slide, size: float,
                      typeface: str) -> dict[int, Field]:
    """Moves what sits below the heading clear of its real text, with a line of air on content slides."""
    bottom = space.head_bottom(head, s.title, typeface, size)
    air = 0 if s.role in _NO_MARGIN_TEXT else space.air(space.below(layout.fields, head))
    moved_fields = space.moved(layout.fields, head, bottom, air, prs.slide_height)
    for idx, field in moved_fields.items():
        if (ph := _ph(slide, idx)) is not None:
            _place(ph, field)
    return moved_fields


def _full_width(slide, field: Field, head: Field) -> Field:
    """A text field the template indents gets the heading's whole width, so nothing sits squeezed in the middle."""
    if field.left - head.left <= _INDENT:
        return field
    right = max(field.left + field.width, head.left + head.width)
    field = replace(field, left=head.left, width=right - head.left)
    if (ph := _ph(slide, field.idx)) is not None:
        _place(ph, field)
    return field


def _place(shape, field: Field) -> None:
    shape.left, shape.top, shape.width, shape.height = (Emu(field.left), Emu(field.top),
                                                        Emu(field.width), Emu(field.height))


def _slide_number(slide, number: int) -> None:
    """The layout's slide number field, still a field so PowerPoint renumbers moved slides."""
    el = _from_layout(slide, PP_PLACEHOLDER.SLIDE_NUMBER)
    if el is None:
        return
    texts = list(el.iter(f"{_A}t"))
    if not texts:
        # A placeholder with an empty paragraph and no field of its own still gets the number.
        texts = [t for t in (_fresh_text(el),) if t is not None]
    for t in texts:
        t.text = str(number)


def _fresh_text(el):
    """A new empty ``a:t`` in this placeholder's first paragraph, for a body that holds no run at all."""
    body = el.find(f"{_P}txBody")
    if body is None:
        return None
    paragraph = body.find(f"{_A}p")
    if paragraph is None:
        paragraph = etree.SubElement(body, f"{_A}p")
    run = etree.Element(f"{_A}r")
    end = paragraph.find(f"{_A}endParaRPr")
    if end is not None:
        # The run takes the formatting of the empty paragraph and goes before its end marker.
        run.append(deepcopy(end))
        run[0].tag = f"{_A}rPr"
        end.addprevious(run)
    else:
        paragraph.append(run)
    return etree.SubElement(run, f"{_A}t")


def _fixed(slide, ph_type, text: str) -> None:
    """The layout's field of this type holding fixed text, a date field would show the day the file is opened."""
    el = _from_layout(slide, ph_type)
    if el is None:
        return
    for fld in list(el.iter(f"{_A}fld")):
        run = etree.SubElement(fld.getparent(), f"{_A}r")
        fld.addnext(run)
        rpr = fld.find(f"{_A}rPr")
        if rpr is not None:
            rpr.attrib.pop("smtClean", None)
            run.append(rpr)
        etree.SubElement(run, f"{_A}t").text = ""
        fld.getparent().remove(fld)
    texts = list(el.iter(f"{_A}t"))
    for t in texts:
        t.text = ""
    if not texts:
        # A footer placeholder often ships as an empty paragraph without a run, it gets one here.
        fresh = _fresh_text(el)
        if fresh is None:
            return
        texts = [fresh]
    texts[0].text = text


def _notice(prs, slide, text: str, typeface: str) -> None:
    """A right-aligned note in the bottom corner, its own box so no layout has to offer a field for it."""
    left = Emu(prs.slide_width - _NOTICE_WIDTH - _NOTICE_MARGIN)
    top = Emu(prs.slide_height - _NOTICE_HEIGHT - _NOTICE_MARGIN)
    box = slide.shapes.add_textbox(left, top, _NOTICE_WIDTH, _NOTICE_HEIGHT)
    rahmen = box.text_frame
    rahmen.word_wrap = False
    rahmen.margin_left = rahmen.margin_right = rahmen.margin_top = rahmen.margin_bottom = 0
    paragraph = rahmen.paragraphs[0]
    paragraph.alignment = PP_ALIGN.RIGHT
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(NOTICE_PT)
    run.font.color.rgb = NOTICE_GREY
    if typeface:
        run.font.name = typeface


def text_area(field: Field) -> Field:
    """The field less its insets on the left, right and top, where its own text would start and wrap."""
    pad = field.inset_h // 2
    return replace(field, left=field.left + pad, width=field.width - 2 * pad,
                   top=field.top + field.inset_top, height=field.height - field.inset_top)


def _body(slide, field: Field, body: Body, picture: bytes | None, f: Palette, typeface: str = "") -> bool:
    """Fills the content field, True only when the placeholder itself holds the text."""
    ph = _ph(slide, field.idx)
    if ph is None:
        return False
    picture_field, field = field, text_area(field)
    if body.kind == "table" and body.rows:
        elements.table(slide, field, body, f, typeface)
        return False
    if body.kind == "chart" and body.categories and body.series:
        elements.chart(slide, field, body, f, typeface)
        return False
    if body.kind == "cards" and body.cards:
        shapes.cards(slide, field, body.cards, f, typeface)
        return False
    if body.kind == "bars" and body.bars:
        shapes.bars(slide, field, body.bars, f, typeface)
        return False
    if body.kind == "highlight" and body.key and body.text:
        shapes.highlight(slide, field, body, f, typeface)
        return False
    if body.kind == "steps" and body.steps:
        diagrams.steps_figure(slide, field, body.steps, f, typeface)
        return False
    if body.kind == "figures" and body.figures:
        diagrams.figures(slide, field, body.figures, f, typeface)
        return False
    if body.kind == "levels" and body.levels:
        diagrams.levels(slide, field, body.levels, f, typeface)
        return False
    if body.kind == "symbols" and body.symbols:
        diagrams.symbols(slide, field, body.symbols, f, typeface)
        return False
    if body.kind == "image" and picture:
        slide.shapes.add_picture(_crop(picture, picture_field.aspect), picture_field.left, picture_field.top,
                                 picture_field.width, picture_field.height)
        return False
    if body.items:
        _set_bullets(ph, picture_field, body.items, typeface)
        return True
    return False
