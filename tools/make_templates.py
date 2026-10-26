"""Builds the templates that ship with the package.

Run it from the repository root with ``python tools/make_templates.py``. It starts from the
neutral master of python-pptx, turns it into a widescreen deck, replaces its layouts with the
51 layouts below, gives it the Poppins typeface and one accent colour per template, and writes
the pptx and its json into the package.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

import pptx
from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.parts.slide import SlideLayoutPart
from pptx.util import Emu

OUT = Path(__file__).resolve().parents[1] / "src" / "outline2pptx" / "templates"
SOURCE = Path(pptx.__file__).parent / "templates" / "default.pptx"
TYPEFACE = "Poppins"

WIDE, HIGH = 12192000, 6858000
MARGIN = 640080
FULL = WIDE - 2 * MARGIN
HALF = (FULL - 304800) // 2
RIGHT = MARGIN + HALF + 304800
HEAD_TOP, HEAD_HIGH = 457200, 1000000
BODY_TOP, BODY_HIGH = 1700000, 4300000

TITLE_PT, HEAD_PT, SUB_PT, BODY_PT, SMALL_PT = 4000, 3200, 2000, 1800, 1600

# Date, footer and slide number sit in the bottom strip of every layout.
FOOT_TOP, FOOT_HIGH = 6200000, 400050
FOOT_WIDE = 3500000
KEEP = {
    10: (MARGIN, FOOT_TOP, FOOT_WIDE, FOOT_HIGH),
    11: ((WIDE - FOOT_WIDE) // 2, FOOT_TOP, FOOT_WIDE, FOOT_HIGH),
    12: (WIDE - MARGIN - FOOT_WIDE, FOOT_TOP, FOOT_WIDE, FOOT_HIGH),
}
COVER = {
    0: (MARGIN, 2200000, FULL, 1500000, TITLE_PT),
    1: (MARGIN, 3800000, FULL, 800000, SUB_PT),
}

# The content area below the heading is laid out in shares of its width and height. Fields sit
# this far apart, a subheading takes the top strip of its column and its text starts below it.
GAP_X, GAP_Y = 0.016, 0.043
SUB_HIGH, UNDER_SUB = 0.085, 0.104


def col(n: int, i: int, span: int = 1) -> tuple[float, float]:
    """Left edge and width of column ``i`` of ``n``, spanning ``span`` columns."""
    w = (1 - (n - 1) * GAP_X) / n
    return i * (w + GAP_X), w * span + GAP_X * (span - 1)


def row(n: int, i: int) -> tuple[float, float]:
    """Top edge and height of row ``i`` of ``n``."""
    h = (1 - (n - 1) * GAP_Y) / n
    return i * (h + GAP_Y), h


def cell(kind: str, c: tuple[float, float], r: tuple[float, float] = (0.0, 1.0)) -> tuple:
    return (kind, c[0], r[0], c[1], r[1])


def headed(c: tuple[float, float], r: tuple[float, float] = (0.0, 1.0)) -> list[tuple]:
    """A column with its own heading on top and its text below, the heading as tall in every row."""
    return [cell("sub", c, (r[0], SUB_HIGH)),
            cell("body", c, (r[0] + UNDER_SUB, r[1] - UNDER_SUB))]


FULL_COL = (0.0, 1.0)
C2 = [col(2, i) for i in range(2)]
C3 = [col(3, i) for i in range(3)]
C4 = [col(4, i) for i in range(4)]
R2 = [row(2, i) for i in range(2)]
R3 = [row(3, i) for i in range(3)]

# Pictures that run to the edge of the slide, beside a heading that keeps to its half.
BLEED_TOP, BLEED_BOTTOM = 0, FOOT_TOP - 100000
BLEED_RIGHT = (MARGIN + HALF + 304800 // 2, BLEED_TOP, WIDE - (MARGIN + HALF + 304800 // 2), BLEED_BOTTOM)
BLEED_LEFT = (0, BLEED_TOP, MARGIN + HALF + 304800 // 2, BLEED_BOTTOM)

# Every content layout: its name and its fields in the content area. "title" only on section
# slides, the others get the heading on top. A field given as a tuple of four EMU values is
# placed on the slide as it is.
LAYOUTS: list[tuple[str, list, dict]] = [
    ("Title and Content", [cell("body", FULL_COL)], {}),
    ("Text Narrow", [("body", 0.15, 0.0, 0.7, 1.0)], {}),
    ("Text with Strip", [("body", 0.0, 0.0, 0.885, 1.0)], {"strip": True}),
    ("Two Content", headed(C2[0]) + headed(C2[1]), {}),
    ("Two Content Plain", [cell("body", c) for c in C2], {}),
    ("Two Content Wide and Narrow", headed(col(3, 0, 2)) + headed(C3[2]), {}),
    ("Two Content Narrow and Wide", headed(C3[0]) + headed(col(3, 1, 2)), {}),
    ("Three Content", [f for c in C3 for f in headed(c)], {}),
    ("Three Content Plain", [cell("body", c) for c in C3], {}),
    ("Four Content", [f for c in C4 for f in headed(c)], {}),
    ("Four Fields", [f for r in R2 for c in C2 for f in headed(c, r)], {}),
    ("Six Fields", [f for r in R2 for c in C3 for f in headed(c, r)], {}),
    ("Two Rows", [f for r in R2 for f in headed(FULL_COL, r)], {}),
    ("Three Rows", [cell("body", FULL_COL, r) for r in R3], {}),
    ("Section Header", [("title", 0.0, 0.165, 1.0, 0.356), ("sub", 0.0, 0.549, 1.0, 0.119)], {}),
    ("Section with Picture Right", [("pic", 0.508, -0.12, 0.492, 1.12), ("title", 0.0, 0.117, 0.492, 0.427),
                                    ("sub", 0.0, 0.568, 0.492, 0.119)], {}),
    ("Section with Picture Left", [("pic", 0.0, -0.12, 0.492, 1.12), ("title", 0.508, 0.117, 0.492, 0.427),
                                   ("sub", 0.508, 0.568, 0.492, 0.119)], {}),
    ("Section with Picture Band", [("pic", 0.0, -0.12, 1.0, 0.69), ("title", 0.0, 0.63, 1.0, 0.237),
                                   ("sub", 0.0, 0.866, 1.0, 0.119)], {}),
    ("Section with Two Pictures", [("pic", 0.508, -0.12, 0.492, 0.54), ("pic", 0.508, 0.465, 0.492, 0.535),
                                   ("title", 0.0, 0.117, 0.492, 0.427), ("sub", 0.0, 0.568, 0.492, 0.119)], {}),
    ("Text and Picture", [cell("body", C2[0]), cell("pic", C2[1])], {}),
    ("Picture and Text", [cell("pic", C2[0]), cell("body", C2[1])], {}),
    ("Text and Picture Bleed", [cell("body", C2[0]), ("pic", BLEED_RIGHT)], {"head": "left"}),
    ("Picture and Text Bleed", [("pic", BLEED_LEFT), cell("body", C2[1])], {"head": "right"}),
    ("Picture Above Text", [("pic", 0.0, 0.0, 1.0, 0.555), ("body", 0.0, 0.598, 1.0, 0.402)], {}),
    ("Text Above Picture", [("body", 0.0, 0.0, 1.0, 0.38), ("pic", 0.0, 0.422, 1.0, 0.578)], {}),
    ("Text and Picture Strip", [("body", 0.0, 0.0, 0.755, 1.0), ("pic", 0.771, 0.0, 0.229, 1.0)], {}),
    ("Picture Strip and Text", [("pic", 0.0, 0.0, 0.229, 1.0), ("body", 0.245, 0.0, 0.755, 1.0)], {}),
    ("Text and Pictures", [("body", 0.0, 0.0, 0.718, 1.0), cell("pic", (0.734, 0.266), R2[0]),
                           cell("pic", (0.734, 0.266), R2[1])], {}),
    ("Pictures with Text", [cell("pic", C2[0], (0.0, 0.64)), cell("pic", C2[1], (0.0, 0.64)),
                            cell("body", C2[0], (0.68, 0.32)), cell("body", C2[1], (0.68, 0.32))], {}),
    ("Picture and Two Content", [cell("pic", C3[0])] + headed(C3[1]) + headed(C3[2]), {}),
    ("Two Content and Picture", headed(C3[0]) + headed(C3[1]) + [cell("pic", C3[2])], {}),
    ("Text, Picture, Text", [("body", 0.0, 0.0, 0.262, 1.0), ("pic", 0.278, 0.0, 0.444, 1.0),
                             ("body", 0.738, 0.0, 0.262, 1.0)], {}),
    ("Pictures and Text", [cell("pic", C3[0], R2[0]), cell("pic", C3[0], R2[1]),
                           cell("body", col(3, 1, 2))], {}),
    ("Text and Two Pictures", [("body", 0.0, 0.0, 0.4, 1.0), ("pic", 0.416, 0.0, 0.284, 1.0),
                               ("pic", 0.716, 0.0, 0.284, 1.0)], {}),
    ("Tiles with Text", [cell("body", C3[0], R2[0]), cell("pic", C3[0], R2[1]),
                         cell("pic", col(3, 1, 2))], {}),
    ("Large Tiles with Text", [cell("pic", C2[0]), cell("body", C2[1], R2[0]),
                               cell("pic", C4[2], R2[1]), cell("pic", C4[3], R2[1])], {}),
    ("Three Pictures with Text", [cell("pic", c, (0.0, 0.5)) for c in C3]
     + [cell("body", c, (0.54, 0.46)) for c in C3], {}),
    ("Text and Three Pictures", [("body", 0.0, 0.0, 1.0, 0.356)] + [cell("pic", c, (0.4, 0.6)) for c in C3], {}),
    ("Picture Above Three Content", [("pic", 0.0, 0.0, 1.0, 0.45)]
     + [cell("body", c, (0.494, 0.506)) for c in C3], {}),
    ("Two Content Above Picture", [cell("body", c, (0.0, 0.403)) for c in C2]
     + [("pic", 0.0, 0.446, 1.0, 0.554)], {}),
    ("Three Pictures Above Text", [cell("pic", c, (0.0, 0.475)) for c in C3]
     + [("body", 0.0, 0.517, 1.0, 0.483)], {}),
    ("Text and Four Pictures", [("body", 0.0, 0.0, 0.4, 1.0)]
     + [cell("pic", (x, 0.284), r) for r in R2 for x in (0.416, 0.716)], {}),
    ("Four Pictures with Text", [cell("pic", c, (0.0, 0.451)) for c in C4]
     + [cell("body", c, (0.494, 0.506)) for c in C4], {}),
    ("Large Picture", [cell("pic", FULL_COL)], {}),
    ("Two Large Pictures", [cell("pic", c) for c in C2], {}),
    ("Picture Narrow and Wide", [cell("pic", C3[0]), cell("pic", col(3, 1, 2))], {}),
    ("Picture Tiles", [cell("pic", col(3, 0, 2)), cell("pic", C3[2], R2[0]), cell("pic", C3[2], R2[1])], {}),
    ("Three Pictures", [cell("pic", c) for c in C3], {}),
    ("Four Pictures", [cell("pic", c, r) for r in R2 for c in C2], {}),
]

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
       'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
# The bullet elements of a first level paragraph, kept when a placeholder is resized.
BULLET_TAGS = ("buClrTx", "buClr", "buSzTx", "buSzPct", "buSzPts", "buFontTx", "buFont",
               "buNone", "buAutoNum", "buChar", "buBlip")

TEMPLATES = {
    "clean": {
        "name": "Clean",
        "accent": "2563EB",
        "style_text": ("A clear, modern vector illustration with flat shapes, a light background "
                       "and a calm blue palette."),
    },
    "warm": {
        "name": "Warm",
        "accent": "C2410C",
        "style_text": ("A warm, hand-painted editorial illustration with soft shapes, a light "
                       "background and an amber palette."),
    },
    "forest": {
        "name": "Forest",
        "accent": "15803D",
        "style_text": ("A calm, textured illustration with organic shapes, a light background "
                       "and a green palette."),
    },
}


def _set_size(shape, hundredths: int, bullets: bool, align: str = "") -> None:
    """One explicit first level size on the placeholder, the size the analyser reads.

    ``bullets`` says whether this placeholder holds a list. A title, a subtitle and a
    subheading hold one line, so they switch the master's bullet off: the stock placeholders
    carry that rule as ``buNone``, and a placeholder that drops it shows a bullet dot in front
    of the cover's own line.
    """
    body = shape.text_frame._txBody
    old_level = None
    for old in body.findall(f"{_A}lstStyle"):
        if old_level is None:
            old_level = old.find(f"{_A}lvl1pPr")
        body.remove(old)
    style = etree.SubElement(body, f"{_A}lstStyle")
    level = etree.SubElement(style, f"{_A}lvl1pPr")
    carried = [kind for kind in (old_level if old_level is not None else [])
               if etree.QName(kind).localname in BULLET_TAGS]
    if bullets:
        if old_level is not None:
            for name in ("marL", "indent"):
                if old_level.get(name) is not None:
                    level.set(name, old_level.get(name))
        for kind in carried:
            level.append(deepcopy(kind))
    else:
        level.set("marL", "0")
        level.set("indent", "0")
        etree.SubElement(level, f"{_A}buNone")
    if align:
        level.set("algn", align)
    etree.SubElement(level, f"{_A}defRPr", sz=str(hundredths))
    # The list style belongs right after the body properties, before the paragraphs.
    body.remove(style)
    body.insert(1, style)
    frame = body.find(f"{_A}bodyPr")
    if frame is not None:
        frame.attrib.pop("vert", None)
        for auto in list(frame):
            if auto.tag.endswith("normAutofit"):
                frame.remove(auto)


def _place(shape, box) -> None:
    """A placeholder gets its whole box, otherwise it inherits only part of it."""
    if box is None:
        return
    left, top, width, height = box
    shape.left, shape.top, shape.width, shape.height = Emu(left), Emu(top), Emu(width), Emu(height)


def _box(field: tuple) -> tuple[int, int, int, int]:
    """A field's place on the slide in EMU, from its shares of the content area."""
    if len(field) == 2:
        return field[1]
    _, x, y, w, h = field
    return (MARGIN + round(x * FULL), BODY_TOP + round(y * BODY_HIGH), round(w * FULL), round(h * BODY_HIGH))


def _placeholder(shape_id: int, kind: str, idx: int, box: tuple[int, int, int, int]) -> etree._Element:
    """A bare placeholder of the given kind, sized by the caller."""
    ph = {"title": '<p:ph type="title"/>', "sub": f'<p:ph type="body" sz="quarter" idx="{idx}"/>',
          "body": f'<p:ph sz="half" idx="{idx}"/>', "pic": f'<p:ph type="pic" idx="{idx}"/>'}[kind]
    names = {"title": "Title", "sub": "Text Placeholder", "body": "Content Placeholder", "pic": "Picture Placeholder"}
    left, top, width, height = box
    return etree.fromstring(
        f'<p:sp {_NS}><p:nvSpPr><p:cNvPr id="{shape_id}" name="{names[kind]} {shape_id}"/>'
        f'<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr>{ph}</p:nvPr></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{left}" y="{top}"/><a:ext cx="{width}" cy="{height}"/></a:xfrm></p:spPr>'
        f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="en-US"/><a:t>{names[kind]}</a:t></a:r></a:p>'
        f'</p:txBody></p:sp>')


def _strip(shape_id: int) -> etree._Element:
    """A light band in the accent colour along the right edge of the content area."""
    left = MARGIN + round(0.915 * FULL)
    return etree.fromstring(
        f'<p:sp {_NS}><p:nvSpPr><p:cNvPr id="{shape_id}" name="Strip {shape_id}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{left}" y="{BODY_TOP}"/><a:ext cx="{WIDE - left}" cy="{BODY_HIGH}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:schemeClr val="accent1">'
        '<a:lumMod val="20000"/><a:lumOff val="80000"/></a:schemeClr></a:solidFill><a:ln><a:noFill/></a:ln>'
        '</p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="en-US"/></a:p></p:txBody></p:sp>')


def _body_size(field: tuple) -> int:
    """Smaller text in narrow or short fields, so a list still fits."""
    _, _, width, height = _box(field)
    return BODY_PT if width >= 0.45 * FULL and height >= 0.5 * BODY_HIGH else SMALL_PT


def _add_layout(prs, model, name: str, fields: list, options: dict):
    """A new layout after the last one, the footer fields of ``model`` and the given fields."""
    master = prs.slide_masters[0]
    element = deepcopy(model._element)
    element.attrib.pop("type", None)
    tree = element.cSld.spTree
    for sp in list(tree.iterchildren(f"{_P}sp")):
        ph = sp.find(f".//{_P}ph")
        if ph is None or int(ph.get("idx", "0")) not in KEEP:
            tree.remove(sp)
    package = prs.part.package
    partname = package.next_partname("/ppt/slideLayouts/slideLayout%d.xml")
    part = SlideLayoutPart(partname, model.part.content_type, package, element)
    part.relate_to(master.part, RT.SLIDE_MASTER)
    rid = master.part.relate_to(part, RT.SLIDE_LAYOUT)
    ids = master._element.get_or_add_sldLayoutIdLst()
    taken = [int(e.get("id")) for e in ids] + [int(e.get("id")) for e in prs.part._element.sldMasterIdLst]
    entry = ids._add_sldLayoutId()
    entry.set("id", str(max(taken) + 1))
    entry.set("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id", rid)
    layout = master.slide_layouts[-1]
    layout.name = name

    shape_id = max(int(e.get("id")) for e in tree.iter(f"{_P}cNvPr")) + 1
    sized = []
    if "title" not in [f[0] for f in fields]:
        head = {"left": (MARGIN, HEAD_TOP, HALF, HEAD_HIGH), "right": (RIGHT, HEAD_TOP, HALF, HEAD_HIGH)}.get(
            options.get("head"), (MARGIN, HEAD_TOP, FULL, HEAD_HIGH))
        tree.append(_placeholder(shape_id, "title", 0, head))
        sized.append((0, HEAD_PT, False))
        shape_id += 1
    if options.get("strip"):
        tree.append(_strip(shape_id))
        shape_id += 1
    idx = 13
    for field in fields:
        kind = field[0]
        number = 0 if kind == "title" else idx
        tree.append(_placeholder(shape_id, kind, number, _box(field)))
        if kind == "title":
            sized.append((0, TITLE_PT, False))
        elif kind == "sub":
            sized.append((number, SUB_PT, False))
        elif kind == "body":
            sized.append((number, _body_size(field), True))
        shape_id += 1
        idx += 0 if kind == "title" else 1
    by_idx = {shape.placeholder_format.idx: shape for shape in layout.placeholders}
    for number, size, bullets in sized:
        _set_size(by_idx[number], size, bullets)
    return layout


def restyle_master(prs) -> None:
    """The master's own title and body sizes, the fallback for a placeholder without one."""
    root = prs.slide_masters[0]._element
    for style, size in ((f"{_P}titleStyle", TITLE_PT), (f"{_P}bodyStyle", BODY_PT)):
        level = root.find(f"{_P}txStyles/{style}/{_A}lvl1pPr")
        if level is None:
            continue
        run = level.find(f"{_A}defRPr")
        if run is None:
            run = etree.SubElement(level, f"{_A}defRPr")
        run.set("sz", str(size))


def restyle_theme(prs, accent: str) -> None:
    """The accent colour, the second dark colour and both typefaces of the theme."""
    part = prs.slide_masters[0].part.part_related_by(RT.THEME)
    xml = part.blob.decode("utf8")
    for name in ("accent1", "dk2"):
        xml = re.sub(rf"<a:{name}>.*?</a:{name}>",
                     f'<a:{name}><a:srgbClr val="{accent}"/></a:{name}>', xml, count=1, flags=re.S)
    xml = re.sub(r'(<a:(?:majorFont|minorFont)>\s*<a:latin typeface=")[^"]*(")',
                 lambda m: m.group(1) + TYPEFACE + m.group(2), xml)
    part._blob = xml.encode("utf8")


def _lay_out_cover(layout) -> None:
    for shape in list(layout.placeholders):
        idx = shape.placeholder_format.idx
        if idx in KEEP:
            _place(shape, KEEP[idx])
            continue
        if idx not in COVER:
            shape._element.getparent().remove(shape._element)
            continue
        left, top, width, height, size = COVER[idx]
        _place(shape, (left, top, width, height))
        _set_size(shape, size, bullets=False, align="ctr")


def build(key: str, meta: dict) -> None:
    prs = Presentation(str(SOURCE))
    master = prs.slide_masters[0]
    prs.slide_width, prs.slide_height = Emu(WIDE), Emu(HIGH)
    # The master is addressed by type, its own indexes differ from the ones in the layouts.
    by_type = {PP_PLACEHOLDER.DATE: KEEP[10], PP_PLACEHOLDER.FOOTER: KEEP[11],
               PP_PLACEHOLDER.SLIDE_NUMBER: KEEP[12]}
    for shape in master.placeholders:
        box = by_type.get(shape.placeholder_format.type)
        if box is None:
            # The whole box, never only left and width: a placeholder that inherits half its
            # geometry comes out at the top edge of the slide with no height at all.
            _place(shape, (int(shape.left * WIDE / 9144000), shape.top,
                           int(shape.width * WIDE / 9144000), shape.height))
            continue
        _place(shape, box)
    cover = master.slide_layouts.get_by_name("Title Slide")
    for layout in list(master.slide_layouts):
        if layout is not cover:
            master.slide_layouts.remove(layout)
    _lay_out_cover(cover)
    for name, fields, options in LAYOUTS:
        _add_layout(prs, cover, name, fields, options)
    closing = _add_layout(prs, cover, "Closing", [], {})
    # The closing slide repeats the cover: its title and one line below.
    for shape in list(closing.placeholders):
        if shape.placeholder_format.idx == 0:
            shape._element.getparent().remove(shape._element)
    tree = closing._element.cSld.spTree
    shape_id = max(int(e.get("id")) for e in tree.iter(f"{_P}cNvPr")) + 1
    tree.append(_placeholder(shape_id, "title", 0, (MARGIN, 2400000, FULL, 1500000)))
    tree.append(_placeholder(shape_id + 1, "sub", 1, (MARGIN, 4000000, FULL, 700000)))
    by_idx = {shape.placeholder_format.idx: shape for shape in closing.placeholders}
    _set_size(by_idx[0], TITLE_PT, False, "ctr")
    _set_size(by_idx[1], SUB_PT, False, "ctr")
    restyle_master(prs)
    restyle_theme(prs, meta["accent"])
    OUT.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT / f"{key}.pptx"))
    (OUT / f"{key}.json").write_text(
        json.dumps({"name": meta["name"], "style_text": meta["style_text"]},
                   ensure_ascii=False, indent=2) + "\n", "utf8")
    print(f"wrote {key}.pptx and {key}.json with {len(master.slide_layouts)} layouts")


if __name__ == "__main__":
    for key, meta in TEMPLATES.items():
        build(key, meta)
