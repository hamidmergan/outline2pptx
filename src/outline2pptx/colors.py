"""The one colour of a template and the tints every drawn element takes from it."""

from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.opc.constants import RELATIONSHIP_TYPE as RT

from .template import Analysis

# The tints, as the share of the colour mixed onto white.
FULL = 1.0
LINE = 0.2
AREA = 0.1
BAND = 0.05
# Series and pie slices spread between these two shares, whatever their count.
STEP_TOP = 1.0
STEP_BOTTOM = 0.3
# Secondary text, the grey the corner notice already uses.
SECONDARY_TEXT = "595959"
GRIDLINE = "D9D9D9"
_FALLBACK = "404040"
# Below this saturation or outside these lightness bounds a colour reads as black, white or grey.
_MIN_SATURATION = 0.25
_MIN_LIGHT = 0.08
_MAX_LIGHT = 0.95
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_TITLE_TYPES = ("title", "ctrTitle")
# WCAG's floor for large text, what a card title in the colour needs against its light card.
_MIN_TEXT_CONTRAST = 3.0


@dataclass(frozen=True)
class Palette:
    """The template's colour in hex, and every tint the build asks for."""

    base: str

    def tint(self, ratio: float) -> RGBColor:
        return RGBColor.from_string(mix(self.base, ratio))

    def text_on(self, ratio: float = FULL) -> RGBColor:
        """Black or white, whichever stands out more on this tint."""
        return RGBColor.from_string(contrast_text(mix(self.base, ratio)))

    def levels(self, n: int) -> list[RGBColor]:
        return [self.tint(a) for a in levels(n)]

    def text_color(self) -> RGBColor:
        """The colour itself for text on white or a light tint, black when it is too light to read there."""
        return RGBColor.from_string(self.base if contrast(self.base, "FFFFFF") >= _MIN_TEXT_CONTRAST else "000000")


def mix(hex_value: str, ratio: float) -> str:
    """The colour laid onto white at the given share, as a solid hex value."""
    r, g, b = (int(hex_value[i:i + 2], 16) for i in (0, 2, 4))
    return "".join(f"{round(c * ratio + 255 * (1 - ratio)):02X}" for c in (r, g, b))


def levels(n: int) -> list[float]:
    """n shares evenly from full colour down to the lightest still readable one."""
    if n <= 1:
        return [STEP_TOP]
    step = (STEP_TOP - STEP_BOTTOM) / (n - 1)
    return [round(STEP_TOP - i * step, 4) for i in range(n)]


def _luminance(hex_value: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_value[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    light, dark = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def contrast_text(hex_value: str) -> str:
    """WCAG contrast of black and of white against the colour, the higher one wins."""
    return "FFFFFF" if contrast(hex_value, "FFFFFF") >= contrast(hex_value, "000000") else "000000"


def is_neutral(hex_value: str) -> bool:
    r, g, b = (int(hex_value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    _, light, saturation = colorsys.rgb_to_hls(r, g, b)
    return saturation < _MIN_SATURATION or light < _MIN_LIGHT or light > _MAX_LIGHT


def from_template(prs, a: Analysis) -> Palette:
    """The title colour of the content layout, else the second dark colour, else the first accent."""
    master = prs.slide_masters[0]
    scheme = _color_scheme(master)
    mapping = _color_map(master)
    candidates = [_title_color(master, _content_layout(prs, a), scheme, mapping),
                  scheme.get("dk2"), scheme.get("accent1")]
    for color in candidates:
        if color and not is_neutral(color):
            return Palette(color)
    return Palette(scheme.get("accent1") or _FALLBACK)


def _content_layout(prs, a: Analysis):
    for role in ("text", "two_columns", "text_with_image"):
        if a.roles.get(role):
            return prs.slide_masters[0].slide_layouts[a.roles[role][0]]
    return None


def _color_scheme(master) -> dict[str, str]:
    try:
        theme = etree.fromstring(master.part.part_related_by(RT.THEME).blob)
    except Exception:
        return {}
    scheme = theme.find(f".//{_A}clrScheme")
    if scheme is None:
        return {}
    values: dict[str, str] = {}
    for entry in scheme:
        name = etree.QName(entry).localname
        color = next(iter(entry), None)
        if color is None:
            continue
        value = color.get("lastClr") if etree.QName(color).localname == "sysClr" else color.get("val")
        if value and re.fullmatch(r"[0-9A-Fa-f]{6}", value):
            values[name] = value.upper()
    return values


def _color_map(master) -> dict[str, str]:
    """bg1, tx1 and the like as the master maps them onto the theme's dk1, lt1 and so on."""
    el = master._element.find(f"{_P}clrMap")
    standard = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}
    return {**standard, **dict(el.attrib)} if el is not None else standard


def _title_color(master, layout, scheme: dict[str, str], mapping: dict[str, str]) -> str | None:
    """The colour the title text really shows: the layout's own, else the master's title style."""
    if layout is not None:
        for sp in layout._element.iter(f"{_P}sp"):
            ph = sp.find(f".//{_P}ph")
            if ph is not None and ph.get("type") in _TITLE_TYPES:
                body_el = sp.find(f"{_P}txBody")
                fill = body_el.find(f".//{_A}solidFill") if body_el is not None else None
                if fill is not None:
                    return _color_value(fill, scheme, mapping)
    style = master._element.find(f".//{_P}titleStyle/{_A}lvl1pPr")
    fill = style.find(f".//{_A}solidFill") if style is not None else None
    return _color_value(fill, scheme, mapping) if fill is not None else None


def _color_value(fill, scheme: dict[str, str], mapping: dict[str, str]) -> str | None:
    color = next(iter(fill), None)
    if color is None:
        return None
    kind = etree.QName(color).localname
    if kind == "srgbClr":
        value = (color.get("val") or "").upper()
    elif kind == "sysClr":
        value = (color.get("lastClr") or "").upper()
    elif kind == "schemeClr":
        name = color.get("val") or ""
        value = scheme.get(mapping.get(name, name), "")
    else:
        return None
    if not re.fullmatch(r"[0-9A-F]{6}", value):
        return None
    return _luminance_mod(value, color)


def _luminance_mod(value: str, color) -> str:
    """lumMod and lumOff, the two changes a theme colour usually carries in a title style."""
    mod = color.find(f"{_A}lumMod")
    off = color.find(f"{_A}lumOff")
    if mod is None and off is None:
        return value
    r, g, b = (int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = l * (int(mod.get("val")) / 100000 if mod is not None else 1) + (
        int(off.get("val")) / 100000 if off is not None else 0)
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), s)
    return "".join(f"{round(c * 255):02X}" for c in (r, g, b))
