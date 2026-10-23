"""Slide previews, rendered through LibreOffice."""

from __future__ import annotations

import tempfile
from pathlib import Path

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
