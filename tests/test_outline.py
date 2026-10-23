import pytest

from conftest import outline_answer
from outline2pptx import outline as ol
from outline2pptx.schemas import SELECTABLE_ROLES, Outline, OutlineRow, DeckParams

ROLES = list(SELECTABLE_ROLES)


def rows(*roles):
    return [OutlineRow(role=r, title=f"Title {i}", gist="A gist.") for i, r in enumerate(roles)]


def test_parse_answer_takes_cover_and_closing():
    result = ol.parse_answer(__import__("json").dumps(outline_answer(6)), ROLES)
    assert len(result.rows) == 6
    assert result.rows[0].role == "cover"
    assert result.rows[-1].role == "closing"
    assert [r.id for r in result.rows] == [f"s{i}" for i in range(1, 7)]


def test_parse_answer_strips_fences_and_chatter():
    raw = "Sure!\n```json\n" + __import__("json").dumps(outline_answer(4)) + "\n```\nDone."
    assert len(ol.parse_answer(raw, ROLES).rows) == 4


def test_parse_answer_without_slides_is_unusable():
    with pytest.raises(ol.Unusable):
        ol.parse_answer('{"title": "x"}', ROLES)


def test_parse_answer_on_broken_json_is_unusable():
    with pytest.raises(ol.Unusable):
        ol.parse_answer("no braces here", ROLES)


def test_merge_pairs_keeps_a_repeated_slides_key():
    raw = '{"slides": [{"role": "text", "title": "A"}], "slides": [{"role": "text", "title": "B"}]}'
    data = ol.json_object(raw)
    assert [s["title"] for s in data["slides"]] == ["A", "B"]


def test_check_rejects_a_short_deck():
    with pytest.raises(ol.Unusable):
        ol.check(Outline(rows=rows("text", "text")), ROLES)


def test_check_breaks_a_repeated_role():
    out = ol.check(Outline(rows=rows("text", "section", "section", "text", "text")), ROLES)
    assert out.rows[1].role != out.rows[2].role


def test_check_caps_the_picture_slides():
    plan = rows(*(["text_with_image"] * 10))
    out = ol.check(Outline(rows=plan), ROLES)
    assert sum(1 for r in out.rows if r.role == "text_with_image") == 10 // 5


def test_check_replaces_a_role_the_template_lacks():
    out = ol.check(Outline(rows=rows("text", "two_columns", "text", "text")), ["text"])
    assert all(r.role in ("cover", "text", "closing") for r in out.rows)


def test_with_ids_keeps_existing_ones():
    plan = [OutlineRow(id="s4", title="A"), OutlineRow(title="B"), OutlineRow(id="s4", title="C")]
    assert [r.id for r in ol.with_ids(plan)] == ["s4", "s5", "s6"]


MARKDOWN = """
# Machine Learning in Practice
From data to a working model

## What the course covers

## Supervised learning
Labels guide the model towards the right answer.

## [two_columns] Strengths and limits
Where it works and where it does not.

## Take it home
Start small and measure everything.
"""


def test_from_markdown_reads_title_and_rows():
    out = ol.from_markdown(MARKDOWN, ROLES)
    assert out.title == "Machine Learning in Practice"
    assert out.subtitle == "From data to a working model"
    assert len(out.rows) == 5
    assert out.rows[0].role == "cover"
    assert out.rows[-1].role == "closing"
    assert out.rows[1].role == "section"  # no gist below it
    assert out.rows[3].role == "two_columns"  # named in the heading
    assert out.rows[2].gist == "Labels guide the model towards the right answer."


def test_from_markdown_without_headings_is_unusable():
    with pytest.raises(ol.Unusable):
        ol.from_markdown("just a paragraph")


def test_markdown_round_trip():
    out = ol.from_markdown(MARKDOWN, ROLES)
    again = ol.from_markdown(ol.to_markdown(out), ROLES)
    assert [r.title for r in again.rows] == [r.title for r in out.rows]
    assert [r.role for r in again.rows] == [r.role for r in out.rows]


def test_build_messages_names_the_language_and_the_roles():
    messages = ol.build_messages("Bees", DeckParams(language="de"), ROLES, slides=12)
    system = messages[0]["content"]
    assert "German" in system
    assert "two_columns" in system
    assert "around 12 slides" in system
    assert "Bees" in messages[1]["content"]
