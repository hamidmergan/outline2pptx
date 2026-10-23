"""Builds the templates that ship with the package.

Run it from the repository root with ``python tools/make_templates.py``. It starts from the
neutral master of python-pptx, turns it into a widescreen deck, lays out every layout the
builder looks for, gives it the Poppins typeface and one accent colour per template, and writes
the pptx and its json into the package.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pptx
from pptx import Presentation
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

TITLE_PT, HEAD_PT, SUB_PT, BODY_PT = 4000, 3200, 2000, 1800

# Per layout: its new name and what every placeholder index becomes. A placeholder the plan does
# not name is dropped, except the date, footer and slide number, which every layout keeps.
KEEP = (10, 11, 12)
PLAN = {
    "Title Slide": ("Title Slide", {
        0: (MARGIN, 2200000, FULL, 1500000, TITLE_PT),
        1: (MARGIN, 3800000, FULL, 800000, SUB_PT),
    }),
    "Title and Content": ("Title and Content", {
        0: (MARGIN, HEAD_TOP, FULL, HEAD_HIGH, HEAD_PT),
        1: (MARGIN, BODY_TOP, FULL, BODY_HIGH, BODY_PT),
    }),
    "Section Header": ("Section Header", {
        0: (MARGIN, 2600000, FULL, 1500000, TITLE_PT),
    }),
    "Two Content": ("Two Content", {
        0: (MARGIN, HEAD_TOP, FULL, HEAD_HIGH, HEAD_PT),
        1: (MARGIN, BODY_TOP, HALF, BODY_HIGH, BODY_PT),
        2: (RIGHT, BODY_TOP, HALF, BODY_HIGH, BODY_PT),
    }),
    "Comparison": ("Comparison", {
        0: (MARGIN, HEAD_TOP, FULL, HEAD_HIGH, HEAD_PT),
        1: (MARGIN, 1650000, HALF, 650000, SUB_PT),
        2: (MARGIN, 2400000, HALF, 3600000, BODY_PT),
        3: (RIGHT, 1650000, HALF, 650000, SUB_PT),
        4: (RIGHT, 2400000, HALF, 3600000, BODY_PT),
    }),
    "Title Only": ("Divider", {
        0: (MARGIN, 2600000, FULL, 1500000, TITLE_PT),
    }),
    "Content with Caption": ("Content Wide", {
        0: (MARGIN, HEAD_TOP, FULL, HEAD_HIGH, HEAD_PT),
        1: (MARGIN, BODY_TOP, FULL, BODY_HIGH, BODY_PT),
    }),
    "Picture with Caption": ("Text with Picture", {
        0: (MARGIN, HEAD_TOP, FULL, HEAD_HIGH, HEAD_PT),
        1: (RIGHT, BODY_TOP, HALF, BODY_HIGH, None),
        2: (MARGIN, BODY_TOP, HALF, BODY_HIGH, BODY_PT),
    }),
    "Title and Vertical Text": ("Closing", {
        0: (MARGIN, 2400000, FULL, 1500000, TITLE_PT),
        1: (MARGIN, 4000000, FULL, 700000, SUB_PT),
    }),
}
DROP = ("Blank", "Vertical Title and Text")

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

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


def _set_size(shape, hundredths: int) -> None:
    """One explicit first level size on the placeholder, the size the analyser reads."""
    body = shape.text_frame._txBody
    for old in body.findall(f"{_A}lstStyle"):
        body.remove(old)
    from lxml import etree

    style = etree.SubElement(body, f"{_A}lstStyle")
    level = etree.SubElement(style, f"{_A}lvl1pPr")
    etree.SubElement(level, f"{_A}defRPr", sz=str(hundredths))
    # The list style belongs right after the body properties, before the paragraphs.
    body.remove(style)
    body.insert(1, style)
    frame = body.find(f"{_A}bodyPr")
    if frame is not None:
        frame.attrib.pop("vert", None)
        for auto in list(frame):
            if frame is not None and auto.tag.endswith("normAutofit"):
                frame.remove(auto)


def _lay_out(layout, plan: dict) -> None:
    for shape in list(layout.placeholders):
        idx = shape.placeholder_format.idx
        if idx in KEEP:
            continue
        if idx not in plan:
            shape._element.getparent().remove(shape._element)
            continue
        left, top, width, height, size = plan[idx]
        shape.left, shape.top, shape.width, shape.height = Emu(left), Emu(top), Emu(width), Emu(height)
        if size is not None:
            _set_size(shape, size)


_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def restyle_master(prs) -> None:
    """The master's own title and body sizes, the fallback for a placeholder without one."""
    root = prs.slide_masters[0]._element
    for style, size in ((f"{_P}titleStyle", TITLE_PT), (f"{_P}bodyStyle", BODY_PT)):
        level = root.find(f"{_P}txStyles/{style}/{_A}lvl1pPr")
        if level is None:
            continue
        run = level.find(f"{_A}defRPr")
        if run is None:
            from lxml import etree

            run = etree.SubElement(level, f"{_A}defRPr")
        run.set("sz", str(size))


def restyle_theme(prs, accent: str) -> None:
    """The accent colour, the second dark colour and both typefaces of the theme."""
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT

    part = prs.slide_masters[0].part.part_related_by(RT.THEME)
    xml = part.blob.decode("utf8")
    for name in ("accent1", "dk2"):
        xml = re.sub(rf"<a:{name}>.*?</a:{name}>",
                     f'<a:{name}><a:srgbClr val="{accent}"/></a:{name}>', xml, count=1, flags=re.S)
    xml = re.sub(r'(<a:(?:majorFont|minorFont)>\s*<a:latin typeface=")[^"]*(")',
                 lambda m: m.group(1) + TYPEFACE + m.group(2), xml)
    part._blob = xml.encode("utf8")


def build(key: str, meta: dict) -> None:
    prs = Presentation(str(SOURCE))
    master = prs.slide_masters[0]
    for layout in list(master.slide_layouts):
        if layout.name in DROP:
            master.slide_layouts.remove(layout)
    prs.slide_width, prs.slide_height = Emu(WIDE), Emu(HIGH)
    for shape in master.shapes:
        if shape.left is not None and shape.width is not None:
            shape.left = Emu(int(shape.left * WIDE / 9144000))
            shape.width = Emu(int(shape.width * WIDE / 9144000))
    for layout in list(master.slide_layouts):
        name, plan = PLAN[layout.name]
        for shape in layout.placeholders:
            if shape.placeholder_format.idx in KEEP and shape.left is not None:
                shape.left = Emu(int(shape.left * WIDE / 9144000))
                shape.width = Emu(int(shape.width * WIDE / 9144000))
        _lay_out(layout, plan)
        layout.name = name
    restyle_master(prs)
    restyle_theme(prs, meta["accent"])
    OUT.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT / f"{key}.pptx"))
    (OUT / f"{key}.json").write_text(
        json.dumps({"name": meta["name"], "style_text": meta["style_text"]},
                   ensure_ascii=False, indent=2) + "\n", "utf8")
    print(f"wrote {key}.pptx and {key}.json")


if __name__ == "__main__":
    for key, meta in TEMPLATES.items():
        build(key, meta)
