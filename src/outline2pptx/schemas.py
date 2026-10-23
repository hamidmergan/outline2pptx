"""The data shapes the deck builder passes between outline, slides and build."""

from pydantic import BaseModel, Field, field_validator

from .grid import (
    MAX_BARS, MAX_CARDS, MAX_FIGURES, MAX_LEVELS, MAX_STEPS, MAX_SYMBOLS,
)

MIN_SLIDES = 3
MAX_SLIDES = 30

ROLES: tuple[str, ...] = (
    "cover", "section", "text", "two_columns", "text_with_image", "image_full", "closing",
)
# The model picks from these for the middle of the deck, first and last slide are forced, a slide of picture and title alone is never offered.
SELECTABLE_ROLES: tuple[str, ...] = ("section", "text", "two_columns", "text_with_image")
LANGUAGES: tuple[str, ...] = ("de", "en")
# How many slides an outline may hold, the model picks its own number inside this range.
SLIDE_BOUNDS: tuple[int, int] = (MIN_SLIDES, MAX_SLIDES)
BODY_KINDS: tuple[str, ...] = ("bullets", "table", "chart", "image", "cards", "bars", "highlight",
                               "steps", "figures", "levels", "symbols")
CHART_TYPES: tuple[str, ...] = ("bar", "line", "pie")
DEFAULT_TEMPLATE = "clean"

# The one cap per field, shared by the model answer parser in slides.py and this schema,
# so a hand-written slide cannot exceed what a model-written one is ever allowed to hold.
MAX_TITLE_CHARS = 120
MAX_SUBTITLE_CHARS = 160
MAX_NOTES_CHARS = 1500
MAX_PROMPT_CHARS = 600
MAX_HEADING_CHARS = 80
MAX_PRESENTER_CHARS = 80
# The picture style, the same cap as the style saved with a template.
MAX_STYLE_CHARS = 1000
# What a person may write into a row's gist.
MAX_GIST_CHARS = 300
MAX_SERIES_NAME_CHARS = 60
MAX_TEXT_ITEMS = 8
MAX_TABLE_ROWS = 6
MAX_CHART_CATEGORIES = 6
MAX_CHART_SERIES = 4
MAX_ICON_CHARS = 40
MAX_BAR_TEXT_CHARS = 40
# The word or number in the highlight box, it has to fit one line in large type.
MAX_KEY_CHARS = 24
# A generous ceiling: a real layout offers one or two picture fields, an uploaded one may offer more.


class OutlineRow(BaseModel):
    """One planned slide: what it is and what it shows."""

    id: str = ""
    role: str = "text"
    title: str = ""
    gist: str = ""


class Outline(BaseModel):
    title: str = ""
    subtitle: str = ""
    rows: list[OutlineRow] = Field(default_factory=list)


class Series(BaseModel):
    name: str = Field(default="", max_length=MAX_SERIES_NAME_CHARS)
    values: list[float] = Field(default_factory=list, max_length=MAX_CHART_CATEGORIES)


class Card(BaseModel):
    icon: str = Field(default="", max_length=MAX_ICON_CHARS)
    title: str = Field(default="", max_length=MAX_HEADING_CHARS)
    text: str = Field(default="", max_length=MAX_GIST_CHARS)


class Bar(BaseModel):
    """One labelled bar, its length set by value and its label by text, the number when that is empty."""

    label: str = Field(default="", max_length=MAX_HEADING_CHARS)
    value: float = 0.0
    text: str = Field(default="", max_length=MAX_BAR_TEXT_CHARS)


class Entry(BaseModel):
    """One step of a sequence or one level of a hierarchy: a short title and one sentence."""

    title: str = Field(default="", max_length=MAX_HEADING_CHARS)
    text: str = Field(default="", max_length=MAX_GIST_CHARS)


class Figure(BaseModel):
    """A key number written with its unit, and what it counts."""

    value: str = Field(default="", max_length=MAX_KEY_CHARS)
    label: str = Field(default="", max_length=MAX_HEADING_CHARS)


class Symbol(BaseModel):
    """A term of a set, shown as an icon with its name below."""

    icon: str = Field(default="", max_length=MAX_ICON_CHARS)
    label: str = Field(default="", max_length=MAX_HEADING_CHARS)


class Body(BaseModel):
    """The one content field of a slide, bullets unless the material asks for more."""

    kind: str = "bullets"
    items: list[str] = Field(default_factory=list, max_length=MAX_TEXT_ITEMS)
    header: list[str] = Field(default_factory=list, max_length=MAX_TEXT_ITEMS)
    rows: list[list[str]] = Field(default_factory=list, max_length=MAX_TABLE_ROWS)
    chart_type: str = "bar"
    categories: list[str] = Field(default_factory=list, max_length=MAX_CHART_CATEGORIES)
    series: list[Series] = Field(default_factory=list, max_length=MAX_CHART_SERIES)
    prompt: str = Field(default="", max_length=MAX_PROMPT_CHARS)
    cards: list[Card] = Field(default_factory=list, max_length=MAX_CARDS)
    bars: list[Bar] = Field(default_factory=list, max_length=MAX_BARS)
    # The highlight: one word or number in the coloured box, a sentence beside it, one term of it in colour.
    key: str = Field(default="", max_length=MAX_KEY_CHARS)
    text: str = Field(default="", max_length=MAX_GIST_CHARS)
    emphasis: str = Field(default="", max_length=MAX_HEADING_CHARS)
    steps: list[Entry] = Field(default_factory=list, max_length=MAX_STEPS)
    figures: list[Figure] = Field(default_factory=list, max_length=MAX_FIGURES)
    levels: list[Entry] = Field(default_factory=list, max_length=MAX_LEVELS)
    symbols: list[Symbol] = Field(default_factory=list, max_length=MAX_SYMBOLS)


class Column(BaseModel):
    heading: str = Field(default="", max_length=MAX_HEADING_CHARS)
    items: list[str] = Field(default_factory=list, max_length=MAX_TEXT_ITEMS)


class ImageSpec(BaseModel):
    prompt: str = Field(default="", max_length=MAX_PROMPT_CHARS)


class Slide(BaseModel):
    """The filled slide, the unit that gets built and previewed."""

    id: str = ""
    role: str = "text"
    # The layout index chosen once, so a rebuild never changes the picture count.
    layout: int | None = None
    title: str = Field(default="", max_length=MAX_TITLE_CHARS)
    subtitle: str = Field(default="", max_length=MAX_SUBTITLE_CHARS)
    body: Body | None = None
    # Not capped at MAX_TEXT_ITEMS: their count follows the uploaded template's own layout, not a bullet limit.
    columns: list[Column] = Field(default_factory=list)
    images: list[ImageSpec] = Field(default_factory=list)
    notes: str = Field(default="", max_length=MAX_NOTES_CHARS)


class DeckParams(BaseModel):
    """Everything the outline call and the content call need, written once at the start."""

    language: str = "en"
    instructions: str = ""
    # Who gives the talk, shown in the bottom left of the cover when set.
    presenter: str = Field(default="", max_length=MAX_PRESENTER_CHARS)
    # Whether speaker notes get written. Written notes always reach the file.
    notes: bool = False
    template_id: str = DEFAULT_TEMPLATE
    template_name: str = ""
    style_text: str = Field(default="", max_length=MAX_STYLE_CHARS)

    @field_validator("presenter", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v
