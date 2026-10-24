"""The cleaning every read text goes through.

Nothing here knows about documents or pages. It takes text and returns text.
"""

import re
import unicodedata

# Puts standalone accents from LaTeX PDFs back on their letter.
_ACCENT_SCAN_RANGE = range(0x00A0, 0x0300)

# The acute stays out, it is typed as an apostrophe.
_ACCENT_EXCLUDED = {"´"}

# Circumflex and caron added by hand, Unicode knows no decomposition for them.
_ACCENT_EXTRA = {
    "ˆ": "̂",  # MODIFIER LETTER CIRCUMFLEX ACCENT -> COMBINING CIRCUMFLEX
    "ˇ": "̌",  # CARON -> COMBINING CARON
}


def _spacing_accent_marks() -> dict[str, str]:
    """Standalone accent to combining accent, derived from the Unicode data."""
    marks: dict[str, str] = {}
    for code_point in _ACCENT_SCAN_RANGE:
        char = chr(code_point)
        if char in _ACCENT_EXCLUDED:
            continue
        parts = unicodedata.decomposition(char).split()
        if len(parts) == 3 and parts[0] == "<compat>" and parts[1] == "0020":
            marks[char] = chr(int(parts[2], 16))
    return marks | _ACCENT_EXTRA


_SPACING_ACCENTS = _spacing_accent_marks()
_SPACING_ACCENT_RE = re.compile(f"[{re.escape(''.join(_SPACING_ACCENTS))}]")


def _attach_spacing_accents(text: str) -> str:
    """Attach every standalone accent to the letter it belongs to."""
    out: list[str] = []
    index = 0
    end = len(text)
    while index < end:
        char = text[index]
        mark = _SPACING_ACCENTS.get(char)
        if mark:
            # The following letter takes precedence.
            if index + 1 < end and text[index + 1].isalpha():
                out.append(text[index + 1] + mark)
                index += 2
                continue
            # Otherwise the preceding one, as in "A¯" or "p(A¯)".
            if out and out[-1][-1:].isalpha():
                out[-1] += mark
                index += 1
                continue
            # No letter next to it means it cannot be assigned, then it stays.
        out.append(char)
        index += 1
    return "".join(out)


def clean(text: str) -> str:
    """Removes null bytes and reassembles separated accents."""
    if not text:
        return text
    text = text.replace("\x00", "")
    if _SPACING_ACCENT_RE.search(text):
        text = _attach_spacing_accents(text)
    return unicodedata.normalize("NFC", text)
