"""Finding the font file a typeface really renders with, so a measurement matches the result."""

from __future__ import annotations

import logging
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

log = logging.getLogger(__name__)

FOLDER = Path(__file__).parent / "fonts" / "poppins"
# The faces shipped with the package, the ones the built-in templates ask for.
BUNDLED = {"poppins": "Poppins-Regular.ttf", "poppins:bold": "Poppins-SemiBold.ttf"}
FALLBACK = "Poppins-Regular.ttf"


@lru_cache(maxsize=64)
def resolve_font_path(typeface: str) -> str:
    """The file for this typeface: a bundled one, else what fontconfig would substitute, else the bundled fallback.

    The same resolution the renderer itself uses, so a measurement made with it matches what
    will really be drawn.
    """
    bundled = BUNDLED.get(typeface.strip().lower())
    if bundled and (FOLDER / bundled).exists():
        return str(FOLDER / bundled)
    try:
        result = subprocess.run(["fc-match", "-f", "%{file}", typeface.split(":")[0]],
                                capture_output=True, text=True, timeout=10)
        path = result.stdout.strip()
        if path and Path(path).exists():
            return path
    except (OSError, subprocess.SubprocessError) as exc:
        log.debug("fc-match is not available, the bundled font steps in: %s", exc)
    return str(FOLDER / FALLBACK)


@lru_cache(maxsize=256)
def load_font(typeface: str, size_pt: int):
    return ImageFont.truetype(resolve_font_path(typeface), max(size_pt, 1))
