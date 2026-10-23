"""Bullets for a list in a field whose layout switches them off, taken from the master's own body style."""

from __future__ import annotations

from copy import deepcopy

from lxml import etree

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_BU = ("buClrTx", "buClr", "buSzTx", "buSzPct", "buSzPts", "buFontTx", "buFont", "buNone", "buAutoNum",
       "buChar", "buBlip")
# What the stock Office master uses, for a master that names no bullet of its own.
_DEFAULT_INDENT = 228600


def add(ph) -> None:
    """Gives every paragraph of a list of two or more the master's bullet, when the layout shows none."""
    paragraphs = ph.text_frame.paragraphs
    if len(paragraphs) < 2 or not _without_marker(ph):
        return
    model_level = _model(ph)
    for paragraph in paragraphs:
        ppr = paragraph._p.get_or_add_pPr()
        for kind in list(ppr):
            if etree.QName(kind).localname in _BU:
                ppr.remove(kind)
        ppr.set("marL", model_level.get("marL", str(_DEFAULT_INDENT)))
        ppr.set("indent", model_level.get("indent", str(-_DEFAULT_INDENT)))
        # Bullet elements come after spacing and before tabs and run defaults in the scheme's order.
        pos = next((i for i, k in enumerate(ppr) if etree.QName(k).localname in ("tabLst", "defRPr", "extLst")),
                      len(ppr))
        for i, kind in enumerate(k for k in model_level if etree.QName(k).localname in _BU):
            ppr.insert(pos + i, deepcopy(kind))


def _without_marker(ph) -> bool:
    layout_ph = next((p for p in ph.part.slide_layout.placeholders
                      if p.placeholder_format.idx == ph.placeholder_format.idx), None)
    if layout_ph is None:
        return False
    level = layout_ph._element.find(f".//{_A}lstStyle/{_A}lvl1pPr")
    return level is not None and level.find(f"{_A}buNone") is not None


def _model(ph):
    """The master's first body level, or a plain round bullet when the master has none."""
    master = ph.part.slide_layout.slide_master._element
    level = master.find(f".//{_P}bodyStyle/{_A}lvl1pPr")
    if level is not None and level.find(f"{_A}buChar") is not None:
        return level
    ersatz = etree.Element(f"{_A}lvl1pPr", marL=str(_DEFAULT_INDENT), indent=str(-_DEFAULT_INDENT))
    etree.SubElement(ersatz, f"{_A}buFont", typeface="Arial")
    etree.SubElement(ersatz, f"{_A}buChar", char="•")
    return ersatz
