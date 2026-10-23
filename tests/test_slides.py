import json

import pytest

from outline2pptx import library, slides as sl, template
from outline2pptx.outline import Unusable
from outline2pptx.schemas import OutlineRow, DeckParams


@pytest.fixture(scope="module")
def spec():
    _, analysis, _ = library.load("clean")
    return template.spec_for(analysis.layout(analysis.roles["text"][0]), analysis)


@pytest.fixture(scope="module")
def two_column_spec():
    _, analysis, _ = library.load("clean")
    index = next(i for i in analysis.roles["two_columns"]
                 if analysis.layout(i).of_kind("subheading"))
    return template.spec_for(analysis.layout(index), analysis)


def row(role="text"):
    return OutlineRow(id="s1", role=role, title="A title", gist="It shows something.")


def parse(body, spec, role="text"):
    answer = json.dumps({"slides": [{"id": "s1", "title": "Heading", "body": body}]})
    return sl.parse_answer(answer, [row(role)], {"s1": spec})[0]


def test_bullets_survive(spec):
    s = parse({"kind": "bullets", "items": ["One", "Two", "Three"]}, spec)
    assert s.body.kind == "bullets" and len(s.body.items) == 3
    assert s.title == "Heading"


def test_a_missing_slide_is_unusable(spec):
    with pytest.raises(Unusable):
        sl.parse_answer('{"slides": [{"id": "sX", "title": "x"}]}', [row()], {"s1": spec})


def test_notes_are_required_when_asked(spec):
    answer = json.dumps({"slides": [{"id": "s1", "title": "Heading", "notes": ""}]})
    with pytest.raises(Unusable):
        sl.parse_answer(answer, [row()], {"s1": spec}, notes=True)


def test_a_slide_outside_the_slides_array_is_still_found(spec):
    answer = json.dumps({"result": {"id": "s1", "title": "Found"}})
    assert sl.parse_answer(answer, [row()], {"s1": spec})[0].title == "Found"


def test_a_kind_the_layout_forbids_falls_back_to_bullets(two_column_spec):
    s = parse({"kind": "cards", "cards": [{"title": "A", "text": "x"}, {"title": "B", "text": "y"}]},
              two_column_spec)
    assert s.body is None  # a two column layout has no single body at all
    assert len(s.columns) == 2


def test_a_table_without_rows_becomes_bullets(spec):
    s = parse({"kind": "table", "header": ["A"], "rows": [], "items": ["One"]}, spec)
    assert s.body.kind == "bullets"


def test_a_chart_keeps_its_series(spec):
    s = parse({"kind": "chart", "chart_type": "pie", "categories": ["A", "B"],
               "series": [{"name": "n", "values": [1, 2]}]}, spec)
    assert s.body.kind == "chart" and s.body.chart_type == "pie"
    assert s.body.series[0].values == [1.0, 2.0]


def test_a_chart_without_categories_becomes_bullets(spec):
    s = parse({"kind": "chart", "categories": [], "series": []}, spec)
    assert s.body.kind == "bullets"


def test_one_card_is_not_a_card_grid(spec):
    s = parse({"kind": "cards", "cards": [{"icon": "clock", "title": "Only", "text": "one"}]}, spec)
    assert s.body.kind == "bullets" and s.body.items == ["Only: one"]


def test_an_unknown_icon_falls_back(spec):
    s = parse({"kind": "cards", "cards": [{"icon": "unicorn", "title": "A", "text": "x"},
                                          {"icon": "clock", "title": "B", "text": "y"}]}, spec)
    assert s.body.cards[0].icon == "check-circle"
    assert s.body.cards[1].icon == "clock"


def test_bars_all_of_one_value_become_bullets(spec):
    s = parse({"kind": "bars", "bars": [{"label": "A", "value": 5, "text": "5 %"},
                                        {"label": "B", "value": 5, "text": "5 %"}]}, spec)
    assert s.body.kind == "bullets"


def test_a_bar_text_without_its_number_gets_one(spec):
    s = parse({"kind": "bars", "bars": [{"label": "A", "value": 5, "text": "percent"},
                                        {"label": "B", "value": 9, "text": "9 percent"}]}, spec)
    assert s.body.bars[0].text == "5 percent"
    assert s.body.bars[1].text == "9 percent"


def test_figures_without_a_digit_are_dropped(spec):
    s = parse({"kind": "figures", "figures": [{"value": "many", "label": "x"},
                                              {"value": "8 h", "label": "y"}]}, spec)
    assert s.body.kind == "bullets"


def test_highlight_drops_an_emphasis_the_sentence_lacks(spec):
    s = parse({"kind": "highlight", "key": "42", "text": "The answer is here.",
               "emphasis": "elsewhere"}, spec)
    assert s.body.kind == "highlight" and s.body.emphasis == ""


def test_too_few_steps_become_bullets(spec):
    s = parse({"kind": "steps", "steps": [{"title": "Only", "text": "one"}]}, spec)
    assert s.body.kind == "bullets"


def test_card_slides_are_every_third_one(spec):
    rows = [OutlineRow(id=f"s{i}", role="text", title=f"T{i}") for i in range(1, 10)]
    picked = sl.card_slides(rows, {r.id: spec for r in rows})
    assert picked == {"s1", "s4", "s7"}


def test_without_cards_removes_the_kind(spec):
    assert "cards" not in sl.without_cards(spec)["body_kinds"]


def test_too_thin_names_the_slide(spec):
    s = parse({"kind": "bullets", "items": ["One"]}, spec)
    thin = sl.too_thin([s], {"s1": spec})
    assert "s1" in thin and "bullet points" in thin["s1"]


def test_build_messages_lists_the_allowed_kinds(spec):
    messages = sl.build_messages("Bees", DeckParams(language="en"), [row()], {"s1": spec})
    user = messages[1]["content"]
    assert "SLIDE s1 (role text)" in user
    assert "allowed kinds" in user
    assert "Bees" in user


def test_ask_again_repeats_the_call(spec):
    messages = sl.build_messages("Bees", DeckParams(), [row()], {"s1": spec})
    again = sl.ask_again(messages, '{"slides": []}', {"s1": "2 bullet points"})
    assert len(again) == len(messages) + 2
    assert again[-1]["role"] == "user" and "too thin" in again[-1]["content"]


def test_source_excerpt_picks_the_matching_stretch():
    source = "alpha " * 200 + "quantum entanglement " * 20 + "omega " * 200
    picked = sl.source_excerpt(source, ["quantum entanglement"], 400)
    assert "quantum" in picked and len(picked) == 400
