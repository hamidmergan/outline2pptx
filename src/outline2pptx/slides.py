"""The content call per batch of slides, and the parsing of the answer into slides."""

from __future__ import annotations

import re

from . import icons
from .outline import LANGUAGE_NAMES, Unusable, json_object
from .grid import (
    MAX_BARS, MAX_CARDS, MAX_FIGURES, MAX_STEPS, MAX_LEVELS, MAX_SYMBOLS,
)
from .schemas import (
    CHART_TYPES, MAX_BAR_TEXT_CHARS, MAX_CHART_CATEGORIES, MAX_CHART_SERIES, MAX_GIST_CHARS, MAX_HEADING_CHARS,
    MAX_KEY_CHARS, MAX_NOTES_CHARS, MAX_PROMPT_CHARS, MAX_SERIES_NAME_CHARS, MAX_SUBTITLE_CHARS, MAX_TABLE_ROWS,
    MAX_TEXT_ITEMS, MAX_TITLE_CHARS, Bar, Body, Card, Column, Entry, Figure, ImageSpec, OutlineRow,
    DeckParams, Series, Slide, Symbol,
)

# A slide below these reads as empty, a small field asks for fewer, at about twelve words a point.
MIN_BULLET_POINTS = 4
MIN_PER_COLUMN = 3
WORDS_PER_BULLET = 12
# Cards on nearly every slide read as a template, every third slide that could carry them is enough.
CARDS_EVERY = 3
# Below these counts a drawing says less than a line of text.
MIN_FIGURES = 2
MIN_STEPS = 2
MIN_LEVELS = 3
MIN_SYMBOLS = 3
# A number in a bar's text, its thousands and decimal marks included.
_NUMBER_RE = re.compile(r"\d(?:[.,  ]?\d)*")
# The lists a drawn body keeps its entries in, in the order a broken answer is searched for them.
_LISTS = ("cards", "bars", "steps", "levels", "figures", "symbols")


def build_messages(source: str, params: DeckParams, rows: list[OutlineRow],
                   specs: dict[str, dict]) -> list[dict]:
    """The content call for one batch of slides."""
    lang = LANGUAGE_NAMES.get(params.language, "English")
    system = (
        "You write the content of slides for teaching and for talks, on the deck's subject only.\n"
        f"Write all slide text in {lang}. Write image prompts in English.\n"
        "For every slide you get its role, title, gist and the fields of its layout with a word "
        "limit each. Fill exactly these fields:\n"
        "- title: the heading, within its word limit\n"
        "- subtitle: only when asked, one line\n"
        "- body: when the slide has one text field. kind is one of the allowed kinds.\n"
        '  bullets: {"kind": "bullets", "items": [...]} with 5 to 7 short points, all together within the word limit. Fewer points are not worth a slide.\n'
        '  table: {"kind": "table", "header": [...], "rows": [[...]]} for real value pairs or things compared along the same attributes, at most 6 rows. A table stands alone: no bullet points beside it.\n'
        '  chart: {"kind": "chart", "chart_type": "bar|line|pie", "categories": [...], "series": [{"name": "...", "values": [numbers]}]} only for numbers with a shared unit, at most 6 categories.\n'
        '  cards: {"kind": "cards", "cards": [{"icon": "...", "title": "...", "text": "..."}]} for two or more '
        "ideas of equal weight, each a short title and one sentence. icon is one name from this list: "
        f"{', '.join(icons.names())}.\n"
        '  bars: {"kind": "bars", "bars": [{"label": "...", "value": number, "text": "..."}]} a bar chart, only to compare '
        "one measure across named things, where a longer bar means more of the same, such as shares per group or the "
        'length of several periods. text is the number with its unit, such as "45 %" or "until 2028". Never for a list '
        "without numbers, never when all values are equal, never for limits of different kinds, those are figures.\n"
        '  figures: {"kind": "figures", "figures": [{"value": "...", "label": "..."}]} for two to four numbers that '
        "carry the slide, such as limits, deadlines, amounts or durations: value is the number with its unit, at most "
        '10 characters, such as "8 h" or "25,000 €", label says in a few words what it counts. Numbers of different '
        "kinds, such as a time limit beside a deadline, are figures, never bars or levels.\n"
        '  steps: {"kind": "steps", "steps": [{"title": "...", "text": "..."}]} only for a real sequence in which each '
        "step follows the one before, such as a procedure, a lab protocol or the phases of a project, in that order: "
        "title names the step in one to three words, text is one short sentence. Never for topics of one field that "
        "stand side by side.\n"
        '  levels: {"kind": "levels", "levels": [{"title": "...", "text": "..."}]} only for a true rank order in which '
        "each level stands above the next, the highest first, such as a hierarchy of norms or of needs: title names the "
        "level, text is one short sentence. Never for limits, rules or a list whose order means nothing.\n"
        '  symbols: {"kind": "symbols", "symbols": [{"icon": "...", "label": "..."}]} for three or more terms of one '
        "set that are recognised by their name alone, such as protected characteristics or fields of work: label is "
        "the bare term in one to three words, no sentence and no reference in parentheses, icon a name from the list "
        "of cards that fits the term. Never for the parts or components of one thing, such as the sections of a "
        "document or the reasons behind a decision: those carry a sentence of their own and belong in cards, or in "
        "bullets where cards are not offered for this slide.\n"
        '  highlight: {"kind": "highlight", "key": "...", "text": "...", "emphasis": "..."} for one number or word '
        "that carries the slide: key is that number or word, at most 12 characters, text one sentence "
        "about it, emphasis a term that stands word for word in that sentence and gets marked in colour. Rare, only for a central figure.\n"
        "  cards, bars, figures, steps, levels, symbols and highlight only where the content has that shape, "
        "bullets stay the usual kind. In one answer each of these forms goes to one slide at most, so no two slides "
        "look alike.\n"
        "  The numbers of a table, chart, bars, figures or highlight belong to the slide's own title and gist, "
        "never to a neighbouring passage about something else.\n"
        '  image: {"kind": "image", "prompt": "..."} only when allowed, at most on every fourth slide.\n'
        '- columns: when the slide has two or more text fields, one entry per field: {"heading": "...", "items": [...]}\n'
        '- images: one entry per image field: {"prompt": "..."}, an English description of a scene, object or visual '
        "metaphor. Never a diagram, chart, curve, formula, map, sign, screen, timeline, schedule or calendar, and never "
        "words, labels, numbers, dates or letters in the picture: whatever needs labelling belongs in the slide text. "
        "The same holds for an image body.\n"
        "- notes: speaker notes in the slide language, only when asked, else an empty string. They speak about "
        "what stands on this slide and nothing else: every point, column, card, step, row or figure of it, in the "
        "order it stands there, each in one or two sentences, about 60 to 180 words in all. Never what a later "
        "slide shows, and never an announcement that the points follow. A section divider gets one or two "
        "sentences naming the topic that comes next, without its content.\n"
        'Answer with one JSON object only: {"slides": [{"id": "...", "title": "...", "subtitle": "...", '
        '"body": {...}, "columns": [...], "images": [...], "notes": "..."}]}.\n'
        'Every slide object goes inside that one "slides" array, nothing else at the top level.'
    )
    parts = []
    for r in rows:
        f = specs[r.id]
        # A slide asked for by instruction alone arrives without a heading, the model writes it.
        title_part = f'title "{r.title}"' if r.title else "no title yet, write one"
        lines = [f"SLIDE {r.id} (role {r.role}): {title_part}, gist: {r.gist}",
                  f"  title limit: {f['heading']} words"
                  + (f", at most {f['heading_chars']} characters" if f.get("heading_chars") else "")]
        if r.role in ("cover", "closing") and f["subheading"]:
            lines.append(f"  subtitle: yes, up to {f['subheading'][0]} words")
        if len(f["bodies"]) == 1:
            lines.append(f"  body: up to {f['bodies'][0]} words, allowed kinds: {', '.join(f['body_kinds'])}")
            if "cards" in f["body_kinds"] and f.get("cards"):
                k = f["cards"]
                lines.append(f"  cards: 2 to {k['max']}, each title up to {k['title_words']} words, "
                              f"each text up to {k['text_words']} words")
            if "bars" in f["body_kinds"] and f.get("bars"):
                lines.append(f"  bars: 2 to {f['bars']}")
            if "figures" in f["body_kinds"] and f.get("figures", 0) >= MIN_FIGURES:
                lines.append(f"  figures: {MIN_FIGURES} to {f['figures']}")
            for kind, name, minimum in (("steps", "steps", MIN_STEPS), ("levels", "levels", MIN_LEVELS)):
                if kind in f["body_kinds"] and f.get(name, {}).get("max", 0) >= minimum:
                    p = f[name]
                    lines.append(f"  {kind}: {minimum} to {p['max']}, each title up to {p['title_words']} words, "
                                  f"each text up to {p['text_words']} words")
            if "symbols" in f["body_kinds"] and f.get("symbols", 0) >= MIN_SYMBOLS:
                lines.append(f"  symbols: {MIN_SYMBOLS} to {f['symbols']}")
        elif len(f["bodies"]) > 1:
            limits = ", ".join(str(w) for w in f["bodies"])
            head = f", each with a heading of up to {f['subheading'][0]} words" if f["subheading"] else ""
            lines.append(f"  columns: {len(f['bodies'])} fields with word limits {limits}{head}, "
                          "at least 3 points in each")
        if f["images"]:
            lines.append(f"  images: {f['images']}")
        lines.append(f"  notes: {'yes' if params.notes else 'no'}")
        parts.append("\n".join(lines))
    head = f"SUBJECT OF THE DECK:\n{source}\n\n" if source.strip() else ""
    user = f"{head}SLIDES TO WRITE:\n" + "\n".join(parts)
    if params.instructions.strip():
        user += f"\n\nINSTRUCTION OF THE SPEAKER: {params.instructions.strip()}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def card_slides(rows: list[OutlineRow], specs: dict[str, dict]) -> set[str]:
    """The slides that may carry cards, every third one of those whose layout allows them, in deck order."""
    possible = [r.id for r in rows if "cards" in specs.get(r.id, {}).get("body_kinds", [])]
    return set(possible[::CARDS_EVERY])


def without_cards(form: dict) -> dict:
    return {**form, "body_kinds": [k for k in form["body_kinds"] if k != "cards"]}


def bullet_count(s: Slide) -> int:
    if s.body is not None and s.body.kind == "bullets":
        return len(s.body.items)
    return sum(len(c.items) for c in s.columns)


def too_thin(slides: list[Slide], specs: dict[str, dict]) -> dict[str, str]:
    """Per thin slide what is missing, a table, chart or cards stand on their own and never count."""
    out: dict[str, str] = {}
    for s in slides:
        limits = specs[s.id]["bodies"]
        if s.body is not None and s.body.kind == "bullets" and limits:
            minimum = min(MIN_BULLET_POINTS, limits[0] // WORDS_PER_BULLET)
            if len(s.body.items) < minimum:
                out[s.id] = f"{len(s.body.items)} bullet points, it needs {minimum} to 7"
        elif s.columns and len(limits) == len(s.columns):
            minimum = [min(MIN_PER_COLUMN, g // WORDS_PER_BULLET) for g in limits]
            if any(len(c.items) < m for c, m in zip(s.columns, minimum)):
                numbers = ", ".join(str(len(c.items)) for c in s.columns)
                out[s.id] = f"columns with {numbers} points, each needs at least {max(minimum)}"
    return out


def ask_again(messages: list[dict], answer: str, thin: dict[str, str]) -> list[dict]:
    """The same call once more, with the thin slides named and asked for again."""
    lines = "\n".join(f"- {sid}: {base}" for sid, base in thin.items())
    return [*messages, {"role": "assistant", "content": answer}, {"role": "user", "content": (
        f"These slides came out too thin:\n{lines}\nTheir subject holds more statements. Write these "
        "slides again with more points on their own subject, each point within "
        "the word limit. Answer with the same JSON object, holding only these slides.")}]


def parse_answer(raw: str, rows: list[OutlineRow], specs: dict[str, dict],
                 notes: bool = False) -> list[Slide]:
    data = json_object(raw)
    by_id = _candidates(data)
    if not by_id:
        raise Unusable("the answer holds no slides")
    slides: list[Slide] = []
    for r in rows:
        e = by_id.get(r.id)
        if e is None:
            raise Unusable(f"slide {r.id} is missing from the answer")
        s = _slide(r, e, specs[r.id])
        # Speaker notes were asked for, so a slide without them is an unusable answer, not a slide.
        if notes and not s.notes:
            raise Unusable(f"slide {r.id} has no speaker notes")
        slides.append(s)
    return slides


def _candidates(data: dict) -> dict[str, dict]:
    """Every dict with an id anywhere in the parsed answer, so a slide the model placed outside the "slides" array is still found, with the "slides" array preferred whenever an id turns up in both."""
    elsewhere: dict[str, dict] = {}
    from_list: dict[str, dict] = {}

    def collect(node: object, target: dict[str, dict]) -> None:
        if isinstance(node, dict):
            if "id" in node:
                key = str(node.get("id"))
                if key not in target:
                    target[key] = node
                return  # accepted as a slide, its own fields are not searched for further ids
            for k, v in node.items():
                collect(v, from_list if k == "slides" else elsewhere)
        elif isinstance(node, list):
            for entry in node:
                collect(entry, target)

    collect(data, elsewhere)
    return {**elsewhere, **from_list}


def _text(v) -> str:
    return str(v).strip() if isinstance(v, (str, int, float)) else ""


def _items(v) -> list[str]:
    if isinstance(v, str):
        return [v.strip()] if v.strip() else []
    if not isinstance(v, list):
        return []
    return [_text(x) for x in v if _text(x)][:MAX_TEXT_ITEMS]


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _slide(row: OutlineRow, e: dict, form: dict) -> Slide:
    s = Slide(id=row.id, role=row.role, title=_text(e.get("title"))[:MAX_TITLE_CHARS] or row.title,
              subtitle=_text(e.get("subtitle"))[:MAX_SUBTITLE_CHARS], notes=_text(e.get("notes"))[:MAX_NOTES_CHARS])
    n = len(form["bodies"])
    if n == 1:
        s.body = _body(e.get("body"), form)
    elif n > 1:
        cols = e.get("columns") if isinstance(e.get("columns"), list) else []
        s.columns = [Column(heading=_text(c.get("heading"))[:MAX_HEADING_CHARS], items=_items(c.get("items")))
                     for c in cols[:n] if isinstance(c, dict)]
        while len(s.columns) < n:
            s.columns.append(Column())
    images = e.get("images") if isinstance(e.get("images"), list) else []
    s.images = [ImageSpec(prompt=_text(b.get("prompt"))[:MAX_PROMPT_CHARS]) for b in images[:form["images"]]
                if isinstance(b, dict) and _text(b.get("prompt"))]
    while len(s.images) < form["images"]:
        s.images.append(ImageSpec(prompt=s.title))
    return s


def _body(raw, form: dict) -> Body:
    """A body of an allowed kind, anything broken becomes bullets, every drawing capped at what its field holds."""
    kinds = form["body_kinds"]
    cards_max = (form.get("cards") or {}).get("max", MAX_CARDS)
    bars_max = form.get("bars") or MAX_BARS
    steps_max = (form.get("steps") or {}).get("max", MAX_STEPS)
    levels_max = (form.get("levels") or {}).get("max", MAX_LEVELS)
    figures_max = form.get("figures") or MAX_FIGURES
    symbols_max = form.get("symbols") or MAX_SYMBOLS
    if not isinstance(raw, dict):
        return Body(kind="bullets", items=_items(raw))
    kind = str(raw.get("kind") or "bullets")
    if kind not in kinds:
        # A drawing this slide may not carry keeps its content as points.
        return Body(kind="bullets", items=_items(raw.get("items")) or _as_bullets(raw))
    b = Body(kind=kind, items=_items(raw.get("items")))
    if kind == "table":
        b.header = _items(raw.get("header"))
        b.rows = [_items(z) for z in (raw.get("rows") or []) if isinstance(z, list)][:MAX_TABLE_ROWS]
        b.rows = [z for z in b.rows if z]
        if not b.rows:
            b.kind = "bullets"
        else:
            b.items = []
    elif kind == "chart":
        b.chart_type = str(raw.get("chart_type") or "bar")
        if b.chart_type not in CHART_TYPES:
            b.chart_type = "bar"
        b.categories = _items(raw.get("categories"))[:MAX_CHART_CATEGORIES]
        for series_entry in (raw.get("series") or [])[:MAX_CHART_SERIES]:
            if isinstance(series_entry, dict):
                values = [_num(v) for v in (series_entry.get("values") or [])][:len(b.categories)]
                values += [0.0] * (len(b.categories) - len(values))
                b.series.append(Series(name=_text(series_entry.get("name"))[:MAX_SERIES_NAME_CHARS], values=values))
        if not b.categories or not b.series:
            b.kind = "bullets"
    elif kind == "image":
        b.prompt = _text(raw.get("prompt"))[:MAX_PROMPT_CHARS]
        if not b.prompt:
            b.kind = "bullets"
    elif kind == "cards":
        raw_cards = raw.get("cards") if isinstance(raw.get("cards"), list) else []
        b.cards = [Card(icon=icons.valid(k.get("icon")), title=_text(k.get("title"))[:MAX_HEADING_CHARS],
                        text=_text(k.get("text"))[:MAX_GIST_CHARS])
                   for k in raw_cards if isinstance(k, dict) and _text(k.get("title"))][:cards_max]
        if len(b.cards) < 2:
            b.kind, b.items = "bullets", b.items or [_row_text(k.title, k.text) for k in b.cards]
            b.cards = []
    elif kind == "bars":
        raw_bars = raw.get("bars") if isinstance(raw.get("bars"), list) else []
        b.bars = [Bar(label=_text(z.get("label"))[:MAX_HEADING_CHARS], value=_num(z.get("value")),
                      text=_text(z.get("text"))[:MAX_BAR_TEXT_CHARS])
                  for z in raw_bars if isinstance(z, dict) and _text(z.get("label"))][:bars_max]
        # A bar chart compares amounts, with fewer than two different ones it only repeats a label.
        if len(b.bars) < 2 or len({z.value for z in b.bars}) < 2:
            texts = {z.text for z in b.bars}
            b.kind, b.items = "bullets", b.items or [z.label if len(texts) == 1 else _row_text(z.label, z.text)
                                                     for z in b.bars]
            b.bars = []
        for z in b.bars:
            z.text = _with_number(z.text, z.value)[:MAX_BAR_TEXT_CHARS]
    elif kind in ("steps", "levels"):
        entries = [Entry(title=_text(e.get("title"))[:MAX_HEADING_CHARS], text=_text(e.get("text"))[:MAX_GIST_CHARS])
                     for e in _list(raw, kind) if _text(e.get("title"))]
        limit, minimum = (steps_max, MIN_STEPS) if kind == "steps" else (levels_max, MIN_LEVELS)
        entries = entries[:limit]
        if len(entries) < minimum:
            b.kind, b.items = "bullets", b.items or [_row_text(e.title, e.text) for e in entries]
        else:
            setattr(b, kind, entries)
    elif kind == "figures":
        # A key figure is a number, a value without a digit was a word the model dressed up as one.
        b.figures = [Figure(value=_text(z.get("value"))[:MAX_KEY_CHARS], label=_text(z.get("label"))[:MAX_HEADING_CHARS])
                     for z in _list(raw, kind) if re.search(r"\d", _text(z.get("value")))][:figures_max]
        if len(b.figures) < MIN_FIGURES:
            b.kind, b.items = "bullets", b.items or [_row_text(z.value, z.label) for z in b.figures]
            b.figures = []
    elif kind == "symbols":
        b.symbols = [Symbol(icon=icons.valid(z.get("icon")), label=_text(z.get("label"))[:MAX_HEADING_CHARS])
                     for z in _list(raw, kind) if _text(z.get("label"))][:symbols_max]
        if len(b.symbols) < MIN_SYMBOLS:
            b.kind, b.items = "bullets", b.items or [z.label for z in b.symbols]
            b.symbols = []
    elif kind == "highlight":
        b.key = _text(raw.get("key"))[:MAX_KEY_CHARS]
        b.text = _text(raw.get("text"))[:MAX_GIST_CHARS]
        b.emphasis = _text(raw.get("emphasis"))[:MAX_HEADING_CHARS]
        # A term the sentence does not contain would mark nothing, so it is not kept.
        if b.emphasis.lower() not in b.text.lower():
            b.emphasis = ""
        if not b.key or not b.text:
            b.kind, b.items = "bullets", b.items or [t for t in (b.text or b.key,) if t]
            b.key = b.text = b.emphasis = ""
    return b


def _row_text(head: str, text: str) -> str:
    return f"{head}: {text}" if text else head


def _list(raw: dict, name: str) -> list[dict]:
    return [e for e in (raw.get(name) if isinstance(raw.get(name), list) else []) if isinstance(e, dict)]


def _as_bullets(raw: dict) -> list[str]:
    """The entries of the first drawing list the answer holds, each as one point."""
    for name in _LISTS:
        entries = _list(raw, name)
        if entries:
            points = [_row_text(_text(e.get("value")), _text(e.get("label"))) if name == "figures"
                      else _row_text(_text(e.get("title") or e.get("label")), _text(e.get("text"))) for e in entries]
            return [p for p in points if p][:MAX_TEXT_ITEMS]
    return []


def _with_number(text: str, value: float) -> str:
    """A bar's text always shows its number, a text naming only the unit gets the number put in front."""
    number = f"{value:g}"
    digits = re.sub(r"\D", "", number)
    if not text or any(re.sub(r"\D", "", z) == digits for z in _NUMBER_RE.findall(text)):
        return text
    return f"{number} {text}"
