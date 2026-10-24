"""The outline: read from Markdown without a model, or planned from a topic by one."""

from __future__ import annotations

import json
import re

from .errors import ModelError, OutlineError
from .schemas import (
    SELECTABLE_ROLES, SLIDE_BOUNDS, Outline, OutlineRow, DeckParams,
)

_ROLE_TEXT = {
    "section": "a section divider with only a heading",
    "text": ("a heading with bullet points, or where the content has that shape a table, a chart, cards with "
             "icons for parallel topics, bars for durations or shares, or one highlighted key figure"),
    "two_columns": "a heading with two or more columns, each with its own subheading",
    "text_with_image": "a heading, bullet points and one or more illustrations",
}
LANGUAGE_NAMES = {"de": "German", "en": "English"}
_ID = re.compile(r"^s\d+$")

# Slides with an illustration cost minutes each to draw, at most one in this many carries one.
_IMAGE_EVERY = 5
_IMAGE_ROLES = ("text_with_image", "image_full")

# One slide per this many characters of material on top of the base.
_CHARS_PER_SLIDE = 60_000
_BASE_SLIDES = 8
# Cover, overview and closing draw on all files, the other slides are shared out among them.
FRAME_SLIDES = 3


def target_slides(chars: int) -> int:
    """How many slides the material carries, a target the planner may deviate from."""
    lo, hi = SLIDE_BOUNDS
    return max(lo, min(hi, _BASE_SLIDES + chars // _CHARS_PER_SLIDE))


def slides_per_file(weights: dict[str, int], count: int) -> dict[str, int]:
    """How many of ``count`` slides each file gets: at least two, more for longer files, never more than twice the smallest.

    Empty for a single file or when there are fewer slides than files.
    """
    if len(weights) < 2 or count < len(weights):
        return {}
    share = dict.fromkeys(weights, min(2, count // len(weights)))
    for _ in range(count - sum(share.values())):
        limit = 2 * min(share.values())
        name = max((n for n in weights if share[n] < limit), key=lambda n: weights[n] / share[n])
        share[name] += 1
    return share


class Unusable(ModelError):
    """The answer was not a usable outline, the caller may try once more."""


def build_messages(topic: str, params: DeckParams, roles: list[str],
                   slides: int | None = None) -> list[dict]:
    """The outline call, one entry per slide, planned over the topic."""
    lo, hi = SLIDE_BOUNDS
    roles_text = "\n".join(f"- {r}: {_ROLE_TEXT[r]}" for r in roles if r in _ROLE_TEXT)
    entry = '{"role": "...", "title": "...", "gist": "..."}'
    system = (
        "You plan slide decks for teaching and for talks. From the topic you pick what matters "
        "and lay it out as an outline, one entry per slide. Each title states the message of "
        "its slide, not only its topic.\n"
        f"Write every title and gist in {LANGUAGE_NAMES.get(params.language, 'English')}.\n"
        + (f"Plan around {slides} slides for this topic. " if slides else
           "Decide yourself how many slides the topic carries: one subject usually makes "
           "10 to 20 slides, a wider one makes more. ")
        + f"The deck has at least {lo} and at most {hi} slides in "
        "total. The first is the cover (role cover), the last is the closing slide (role "
        "closing). The closing slide's title is the one thought the audience takes home, "
        "never a thank-you. For every slide in between choose one of these roles:\n"
        f"{roles_text}\n"
        "Vary the roles: never the same role on two neighbouring slides except text, and use every "
        "role at least once when the topic allows. Roles with an illustration suit subjects a "
        "picture can explain, not definitions.\n"
        "The slides together cover what matters about the topic, each slide its own part of it.\n"
        'Answer with one JSON object only: {"title": "...", "subtitle": "...", "slides": '
        f'[{entry}]}}. The gist is one sentence saying what '
        "the slide shows."
    )
    task = f"/no_think\nTOPIC:\n{topic}\n"
    if params.instructions.strip():
        task += f"\nINSTRUCTION OF THE SPEAKER: {params.instructions.strip()}\n"
    return [{"role": "system", "content": system}, {"role": "user", "content": task}]


def build_material_messages(material: str, params: DeckParams, roles: list[str], *,
                            files: list[str] | None = None, slides: int | None = None,
                            shares: dict[str, int] | None = None) -> list[dict]:
    """The outline call over material: documents, not a topic the model knows by itself.

    A topic is something the model fills in from what it knows. Material is something it
    has to read: it picks what matters out of these pages, works through them to the last
    line, and gives every file slides of its own.
    """
    lo, hi = SLIDE_BOUNDS
    roles_text = "\n".join(f"- {r}: {_ROLE_TEXT[r]}" for r in roles if r in _ROLE_TEXT)
    entry = '{"role": "...", "title": "...", "gist": "..."}'
    system = (
        "You plan slide decks for teaching and for talks. From the material you pick what matters "
        "and lay it out as an outline, one entry per slide. Each title states the message of "
        "its slide, not only its topic.\n"
        f"Write every title and gist in {LANGUAGE_NAMES.get(params.language, 'English')}.\n"
        + (f"Plan around {slides} slides for this amount of material. " if slides else
           "Decide yourself how many slides the material carries: one chapter usually makes "
           "10 to 20 slides, more material makes more. ")
        + f"The deck has at least {lo} and at most {hi} slides in "
        "total. The first is the cover (role cover), the last is the closing slide (role "
        "closing). The closing slide's title is the one thought the audience takes home, "
        "never a thank-you. For every slide in between choose one of these roles:\n"
        f"{roles_text}\n"
        "Vary the roles: never the same role on two neighbouring slides except text, and use every "
        "role at least once when the material allows. Roles with an illustration suit topics a "
        "picture can explain, not definitions.\n"
        "Every slide rests on the material, the slides together cover what matters in the whole "
        "of it. Work through the material to its last line before you settle the slides. Nothing "
        "goes on a slide that the material does not say.\n"
        + (f"The material comes from {len(files)} files: {', '.join(files)}. EVERY one of "
           "them gets slides of its own. "
           + ("Give each file exactly this many slides besides cover, overview and closing: "
              + ", ".join(f"{name}: {n}" for name, n in shares.items())
              + ". A slide that brings several documents together counts for the file it draws "
              "on most. " if shares else
              "Balance the slides between the files: a large file gets more than a small one, "
              "but never more than twice the slides of the smallest. ")
           + "Where documents touch the same subject, bring them together. The slide before the "
           "closing one is an overview that compares the documents along the same points: what "
           "each requires, its deadlines, who is responsible and the consequences. It has "
           "role text and a gist that asks for a table.\n"
           if files and len(files) > 1 else "")
        + 'Answer with one JSON object only: {"title": "...", "subtitle": "...", "slides": '
        f'[{entry}]}}. The gist is one sentence saying what '
        "the slide shows, in the words of the material."
    )
    task = f"/no_think\nMATERIAL:\n{material}\n"
    if params.instructions.strip():
        task += f"\nINSTRUCTION OF THE SPEAKER: {params.instructions.strip()}\n"
    return [{"role": "system", "content": system}, {"role": "user", "content": task}]


def _merge_pairs(pairs: list[tuple[str, object]]) -> dict:
    """Concatenate duplicate keys whose values are lists and merge those whose values are dicts, so a model repeating a key never loses everything but the last value to plain json.loads."""
    obj: dict = {}
    for key, value in pairs:
        present = obj.get(key)
        if key in obj and isinstance(present, list) and isinstance(value, list):
            obj[key] = present + value
        elif key in obj and isinstance(present, dict) and isinstance(value, dict):
            obj[key] = {**present, **value}
        else:
            obj[key] = value
    return obj


def json_object(raw: str) -> dict:
    """The one JSON object in the answer, fences and chatter stripped."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text[3:]
        text = text.removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise Unusable("no JSON braces in the answer")
    try:
        data = json.loads(text[start:end + 1], object_pairs_hook=_merge_pairs)
    except json.JSONDecodeError as exc:
        raise Unusable(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise Unusable("the answer is not an object")
    return data


def parse_answer(raw: str, roles: list[str], bounds: tuple[int, int] | None = None) -> Outline:
    """The outline out of the answer."""
    data = json_object(raw)
    raw_rows = data.get("slides")
    if not isinstance(raw_rows, list) or not raw_rows:
        raise Unusable("the answer holds no slides")
    rows: list[OutlineRow] = []
    for entry in raw_rows:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or "").strip()
        if not title:
            continue
        rows.append(OutlineRow(role=str(entry.get("role") or "text").strip().lower(),
                               title=title[:120],
                               gist=str(entry.get("gist") or "").strip()[:300]))
    title = str(data.get("title") or (rows[0].title if rows else "")).strip()[:120]
    outline = Outline(title=title, subtitle=str(data.get("subtitle") or "").strip()[:160], rows=rows)
    return check(outline, roles, bounds)


def check(outline: Outline, roles: list[str], bounds: tuple[int, int] | None = None) -> Outline:
    """Cover first, closing last, no role twice in a row, count within the given bounds or the standard ones."""
    lo, hi = bounds or SLIDE_BOUNDS
    rows = [r.model_copy() for r in outline.rows if r.title.strip()]
    if len(rows) < lo:
        raise Unusable(f"only {len(rows)} slides, at least {lo} are required")
    rows = rows[:hi]
    allowed = [r for r in SELECTABLE_ROLES if r in roles] or ["text"]
    for r in rows:
        if r.role not in allowed:
            r.role = "text"
    rows[0].role = "cover"
    rows[-1].role = "closing"
    for i in range(1, len(rows) - 1):
        previous = rows[i - 1].role
        if rows[i].role == previous and previous != "text":
            replacement = [r for r in ("text_with_image", "two_columns", "text", "section")
                           if r in allowed and r != previous]
            rows[i].role = replacement[0] if replacement else "text"
    # Pictures only where the cap allows, the rest of those slides keep their text.
    free = len(rows) // _IMAGE_EVERY
    for r in rows[1:-1]:
        if r.role in _IMAGE_ROLES:
            if free > 0:
                free -= 1
            else:
                r.role = "text"
    return Outline(title=outline.title or rows[0].title, subtitle=outline.subtitle, rows=with_ids(rows))


def with_ids(rows: list[OutlineRow]) -> list[OutlineRow]:
    """Fresh ids only where one is missing or repeated, so slides keep their content."""
    highest = max((int(r.id[1:]) for r in rows if _ID.match(r.id or "")), default=0)
    seen: set[str] = set()
    out: list[OutlineRow] = []
    for r in rows:
        rid = r.id if _ID.match(r.id or "") and r.id not in seen else ""
        if not rid:
            highest += 1
            rid = f"s{highest}"
        seen.add(rid)
        out.append(OutlineRow(id=rid, role=r.role, title=r.title, gist=r.gist))
    return out


# Markdown


_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_ROLE_TAG = re.compile(r"^\[(\w+)\]\s*", re.I)


def from_markdown(text: str, roles: list[str] | None = None,
                  bounds: tuple[int, int] | None = None) -> Outline:
    """An outline read from Markdown, no model involved.

    The first level one heading is the deck title and the line below it the subtitle. Every
    further heading is one slide, the lines under it are its gist. A heading may name its role
    in square brackets, otherwise the nesting decides: a heading with no text under it is a
    section divider, one with text is a text slide.

    The file is the author's own plan, so nothing in it is dropped or renamed. A file outside the
    slide bounds is refused with an error naming the limit, never cut down to fit.
    """
    title, subtitle = "", ""
    rows: list[OutlineRow] = []
    pending: list[str] = []
    forced: list[str] = []
    for line in text.splitlines():
        match = _HEADING.match(line.strip())
        if match is None:
            stripped = line.strip()
            bullet = _BULLET.match(line)
            if bullet:
                stripped = bullet.group(1).strip()
            if stripped:
                pending.append(stripped)
            continue
        text_of_heading = match.group(2).strip()
        if not title and len(match.group(1)) == 1:
            title = text_of_heading[:120]
            subtitle = " ".join(pending)[:160] if not rows else subtitle
            pending = []
            continue
        if rows:
            rows[-1].gist = " ".join(pending)[:300]
        elif pending and not subtitle:
            subtitle = " ".join(pending)[:160]
        pending = []
        role_tag = _ROLE_TAG.match(text_of_heading)
        role = "text"
        if role_tag:
            role = role_tag.group(1).lower()
            text_of_heading = text_of_heading[role_tag.end():].strip()
        forced.append(role if role_tag else "")
        rows.append(OutlineRow(role=role, title=text_of_heading[:120]))
    if rows:
        rows[-1].gist = " ".join(pending)[:300]
    if not rows:
        raise OutlineError("The outline holds no headings. Every slide is one heading.")
    # A heading without a gist is a divider, unless the Markdown named its role itself.
    for r, tag in zip(rows, forced):
        if not tag and not r.gist:
            r.role = "section"
    if title:
        # The level one heading is the deck title, so it becomes the cover slide of its own.
        rows.insert(0, OutlineRow(role="cover", title=title, gist=subtitle))
        forced.insert(0, "cover")
    # A heading that is only a role tag has no title, and a slide without a title cannot be built.
    empty = [i for i, r in enumerate(rows) if not r.title.strip()]
    if empty:
        raise OutlineError(f"Heading {empty[0] + 1} of the outline has no title, only a role tag. "
                           "Every heading needs a title of its own.")
    lo, hi = bounds or SLIDE_BOUNDS
    if not lo <= len(rows) <= hi:
        raise OutlineError(f"The outline has {len(rows)} slides, a deck holds {lo} to {hi}. "
                           "Nothing of the outline is dropped, so split the file or shorten it.")
    # The tag travels with the row's id, so a row the check moves keeps the role its author wrote.
    rows = with_ids(rows)
    tags = {r.id: tag for r, tag in zip(rows, forced)}
    outline = Outline(title=title or rows[0].title, subtitle=subtitle, rows=rows)
    kept = check(outline, roles if roles is not None else list(SELECTABLE_ROLES), bounds)
    # The Markdown is the author's own plan, so a role it names stays whatever the roles allow.
    for row in kept.rows[1:-1]:
        tag = tags.get(row.id, "")
        if tag in SELECTABLE_ROLES and (roles is None or tag in roles):
            row.role = tag
    return kept


def to_markdown(outline: Outline) -> str:
    """The outline written back as Markdown, the form ``from_markdown`` reads."""
    parts = [f"# {outline.title}"]
    if outline.subtitle:
        parts.append(outline.subtitle)
    for row in outline.rows[1:]:
        parts.append(f"## [{row.role}] {row.title}")
        if row.gist:
            parts.append(row.gist)
    return "\n\n".join(parts) + "\n"
