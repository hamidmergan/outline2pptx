"""The Phosphor Regular icons a card may carry, tinted in the template's colour on the way in."""

from __future__ import annotations

import functools
import re
from io import BytesIO
from pathlib import Path

from PIL import Image

FOLDER = Path(__file__).parent / "icons"
# What a card shows when the model names an icon outside the list.
FALLBACK = "check-circle"


@functools.lru_cache(maxsize=1)
def names() -> tuple[str, ...]:
    return tuple(sorted(p.stem for p in FOLDER.glob("*.png")))


def valid(name: str) -> str:
    """The icon's name in the list's spelling, or the neutral one when it is not there."""
    key = re.sub(r"[\s_]+", "-", str(name or "").strip().lower())
    return key if key in names() else FALLBACK


@functools.lru_cache(maxsize=256)
def _tinted(name: str, color: str) -> bytes:
    mask = Image.open(FOLDER / f"{name}.png").getchannel("A")
    picture = Image.new("RGBA", mask.size, "#" + color)
    picture.putalpha(mask)
    out = BytesIO()
    picture.save(out, format="PNG", optimize=True)
    return out.getvalue()


def picture(name: str, color: str) -> BytesIO:
    """The icon as a PNG in the given hex colour, sharp enough for a full-screen projection."""
    return BytesIO(_tinted(valid(name), color.upper()))
