"""Image size from a placeholder, the prompt for it, and the picture a field gets without a model."""

from __future__ import annotations

import re
from io import BytesIO

# The pixels follow the field at print resolution, a floor so a stamp-sized field still gets a usable
# picture, a ceiling so a full-width banner does not cost minutes of generation time.
EMU_PER_INCH = 914400
TARGET_DPI = 300
LONG_SIDE_MIN = 768
LONG_SIDE_MAX = 1920
_MINIMUM = 256
_FALLBACK_SIZE = "1024x1024"


def image_size(width: int, height: int) -> str:
    """The field at 300 dpi, the long side capped both ways, both sides multiples of 16."""
    ratio = (width / height) if height else 1.0
    long = max(width, height) / EMU_PER_INCH * TARGET_DPI
    long = min(LONG_SIDE_MAX, max(LONG_SIDE_MIN, long))
    if ratio >= 1:
        w, h = long, long / ratio
    else:
        w, h = long * ratio, long

    def rounded(v: float) -> int:
        return max(_MINIMUM, int(round(v / 16)) * 16)

    return f"{rounded(w)}x{rounded(h)}"


# Quoted words and their translation right behind are what a prompt wants painted as lettering, unchecked for spelling.
_QUOTE = re.compile(r"(?:(?<!\w)'[^'\n]*'(?!\w)|\"[^\"\n]*\"|„[^“”\n]*[“”]|“[^”\n]*”|«[^»\n]*»)(?:\s*\([^()\n]{0,40}\))?")
NO_LETTERING = "The picture shows no writing of any kind, only shapes, people and objects."


def without_quotes(description: str) -> str:
    text = re.sub(r"\s+([,.;:])", r"\1", re.sub(r"\s{2,}", " ", _QUOTE.sub("", description)))
    return re.sub(r"([,.;:])(?:\s*[,;:])+", r"\1", text).strip()


def prompt_for(style_text: str, description: str) -> str:
    return f"{style_text.strip()} Subject: {without_quotes(description)} {NO_LETTERING}".strip()


def generate(client, settings, prompt: str, size: str) -> bytes:
    """One picture as bytes, drawn by the image model."""
    from .llm import call_image

    return call_image(client, settings, prompt, size)


# Placeholder


_PLACEHOLDER_TINT = 0.12


def placeholder(width: int, height: int, color: str) -> bytes:
    """A plain tinted rectangle, what a picture field gets when no image model is set."""
    from PIL import Image

    from .colors import mix

    pixels = image_size(width, height).split("x")
    out = BytesIO()
    Image.new("RGB", (int(pixels[0]), int(pixels[1])),
              "#" + mix(color, _PLACEHOLDER_TINT)).save(out, format="PNG", optimize=True)
    return out.getvalue()
