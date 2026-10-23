"""Slide previews, rendered through LibreOffice."""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import build
from .schemas import Slide
from .template import Analysis
from .errors import PreviewError
from .render import available, pptx_to_images

DPI = 80


def render(deck: bytes, dpi: int = DPI) -> list[bytes]:
    """One PNG per slide. Needs LibreOffice and poppler on the machine."""
    if not available():
        raise PreviewError("LibreOffice is not installed, so no preview can be rendered.")
    with tempfile.TemporaryDirectory(prefix="outline2pptx_preview_") as tmp:
        path = Path(tmp) / "deck.pptx"
        path.write_bytes(deck)
        target = Path(tmp) / "img"
        target.mkdir()
        return [p.read_bytes() for p in pptx_to_images(path, target, dpi=dpi)]


def single(template_bytes: bytes, a: Analysis, slide: Slide, images: dict[str, bytes],
            title: str, notes: bool, notice: str = "", number: int = 1, date: str = "",
            presenter: str = "") -> bytes:
    """One slide as a one-slide deck, so a single edit never renders the whole deck."""
    return several(template_bytes, a, [slide], images, title, notes, notice, numbers=[number], date=date,
                   presenter=presenter)[0]


def several(template_bytes: bytes, a: Analysis, slides: list[Slide], images: dict[str, bytes],
            title: str, notes: bool, notice: str = "", *, numbers: list[int],
            date: str = "", presenter: str = "") -> list[bytes]:
    """Some slides of the deck in one render, each under its own number."""
    deck = build.build_deck(template_bytes, a, slides, images, title, notes, notice, numbers=numbers, date=date,
                    presenter=presenter)
    pngs = render(deck)
    if len(pngs) < len(slides):
        raise PreviewError("LibreOffice returned no preview image.")
    return pngs[:len(slides)]
