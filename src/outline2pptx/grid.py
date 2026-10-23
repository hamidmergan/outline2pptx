"""How many cards, bars, steps, figures, levels and symbols a content field holds, from its size and text size alone."""

from __future__ import annotations

import math

EMU_PER_PT = 12700
MAX_CARDS = 8
MAX_BARS = 8
MAX_STEPS = 6
MAX_FIGURES = 4
MAX_LEVELS = 5
MAX_SYMBOLS = 8
# Card text follows the template's body size, but a poster-sized body would leave room for one card.
MAX_BASE_PT = 18.0
DEFAULT_PT = 16.0
# Card measures in multiples of the base size, taken from the example deck: a card as wide as
# three to a row on a wide slide, tall enough for icon, title and two lines of text.
CARD_MIN_WIDTH = 16.0
CARD_MIN_HEIGHT = 8.2
GAP = 1.0
TITLE_RATIO = 1.05
TEXT_RATIO = 0.8
TEXT_LINES = 3
# A bar row needs its label on up to two lines.
BAR_MIN_HEIGHT = 2.2
_CHARS_PER_WORD = 6.5
# A step's column, a key figure's column and a symbol's column need this width, a level this height,
# all in multiples of the base size.
STEP_MIN_WIDTH = 8.5
FIGURE_MIN_WIDTH = 10.0
LEVEL_MIN_HEIGHT = 2.6
LEVEL_GAP = 0.25
SYMBOL_MIN_WIDTH = 7.0
SYMBOL_MIN_HEIGHT = 7.0
# A title of a step or level stays a few words, a text one sentence, however wide the field.
MAX_TITLE_WORDS = 4
MAX_TEXT_WORDS = 15
# The pyramid takes this share of the field's width, its levels' text the rest.
PYRAMID_RATIO = 0.4


def base_pt(size_pt: float) -> float:
    return min(MAX_BASE_PT, size_pt or DEFAULT_PT)


def _count(length_pt: float, min_pt: float, gap_pt: float) -> int:
    return max(1, int((length_pt + gap_pt) // (min_pt + gap_pt)))


def card_grid(width: int, height: int, size_pt: float) -> tuple[int, int]:
    """Columns and rows of cards the field holds at their smallest readable size."""
    g = base_pt(size_pt)
    return (_count(width / EMU_PER_PT, CARD_MIN_WIDTH * g, GAP * g),
            _count(height / EMU_PER_PT, CARD_MIN_HEIGHT * g, GAP * g))


def card_space(width: int, height: int, size_pt: float) -> dict:
    """The most cards the field takes, and the words a title and a text may have in the fullest grid."""
    columns, rows = card_grid(width, height, size_pt)
    g = base_pt(size_pt)
    card_pt = (width / EMU_PER_PT - GAP * g * (columns - 1)) / columns
    inner = card_pt - 2 * 1.2 * g
    title = inner / (TITLE_RATIO * g * 0.5)
    text = inner / (TEXT_RATIO * g * 0.5) * TEXT_LINES
    return {"max": min(MAX_CARDS, columns * rows),
            "title_words": max(2, int(title / _CHARS_PER_WORD)),
            "text_words": max(4, int(text / _CHARS_PER_WORD))}


def distribution(n: int, columns_max: int) -> list[int]:
    """Cards per row: as few rows as the width allows, rows as even as possible, the fuller ones first."""
    if n <= 0:
        return []
    rows = math.ceil(n / max(1, columns_max))
    breit = math.ceil(n / rows)
    out, rest = [], n
    for r in range(rows):
        k = min(breit, rest - (rows - r - 1))
        k = max(1, min(k, math.ceil(rest / (rows - r))))
        out.append(k)
        rest -= k
    return out


def bar_space(height: int, size_pt: float) -> int:
    g = base_pt(size_pt)
    return min(MAX_BARS, _count(height / EMU_PER_PT, BAR_MIN_HEIGHT * g, 0.0))


def _words(width_pt: float, size: float, lines: int) -> int:
    return int(width_pt / (size * 0.5) * lines / _CHARS_PER_WORD)


def step_space(width: int, size_pt: float) -> dict:
    """The most steps side by side, and the words a step's title and text may have in the fullest row."""
    g = base_pt(size_pt)
    n = min(MAX_STEPS, _count(width / EMU_PER_PT, STEP_MIN_WIDTH * g, 0.0))
    column = width / EMU_PER_PT / n - g
    return {"max": n, "title_words": max(2, min(MAX_TITLE_WORDS, _words(column, TITLE_RATIO * g, 2))),
            "text_words": max(4, _words(column, TEXT_RATIO * g, TEXT_LINES))}


def figure_space(width: int, size_pt: float) -> int:
    return min(MAX_FIGURES, _count(width / EMU_PER_PT, FIGURE_MIN_WIDTH * base_pt(size_pt), 0.0))


def level_space(width: int, height: int, size_pt: float) -> dict:
    """The most levels stacked, and the words a level's title and text may have beside the pyramid."""
    g = base_pt(size_pt)
    n = min(MAX_LEVELS, _count(height / EMU_PER_PT, LEVEL_MIN_HEIGHT * g, LEVEL_GAP * g))
    text = width / EMU_PER_PT * (1 - PYRAMID_RATIO) - 1.5 * g
    return {"max": n, "title_words": max(2, min(MAX_TITLE_WORDS, _words(text, TITLE_RATIO * g, 1))),
            "text_words": max(4, min(MAX_TEXT_WORDS, _words(text, TEXT_RATIO * g, 2)))}


def symbol_space(width: int, height: int, size_pt: float) -> int:
    g = base_pt(size_pt)
    return min(MAX_SYMBOLS, _count(width / EMU_PER_PT, SYMBOL_MIN_WIDTH * g, 0.0)
               * _count(height / EMU_PER_PT, SYMBOL_MIN_HEIGHT * g, GAP * g))
