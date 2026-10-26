"""The newer drawn forms: parsed from an answer, kept apart from bullets, drawn inside the slide."""

import json
from io import BytesIO

import pytest
from pptx import Presentation

from outline2pptx import library, slides as sl, template
from outline2pptx.deck import build_deck
from outline2pptx.schemas import OutlineRow

FORMS = {
    "timeline": {"kind": "timeline", "events": [
        {"date": "1852", "title": "Hive frame", "text": "The movable frame hive is built."},
        {"date": "1914", "title": "Bee dances", "text": "The waggle dance is decoded."},
        {"date": "2006", "title": "Colony losses", "text": "Whole colonies disappear."}]},
    "cycle": {"kind": "cycle", "center": "Life cycle", "steps": [
        {"title": "Egg", "text": "One egg per cell."}, {"title": "Larva", "text": "Fed for six days."},
        {"title": "Pupa", "text": "The cell is capped."}, {"title": "Adult", "text": "It chews its way out."}]},
    "versus": {"kind": "versus", "tone": "good_bad",
               "a": {"title": "Myth", "items": ["Bees die after every sting", "All bees make honey"]},
               "b": {"title": "Fact", "items": ["Only stings into skin kill", "Few species store honey"]}},
    "matrix": {"kind": "matrix", "x": "Effort", "y": "Impact", "cells": [
        {"pos": "tl", "title": "Quick wins", "text": "Plant flowers."},
        {"pos": "tr", "title": "Big projects", "text": "Build meadows."},
        {"pos": "bl", "title": "Fill-ins", "text": "Bee hotels."},
        {"pos": "br", "title": "Avoid", "text": "Foreign species."}]},
    "quote": {"kind": "quote", "text": "Without bees a third of our food would not exist.",
              "emphasis": "a third of our food"},
    "checklist": {"kind": "checklist", "items": ["Wear a veil", "Light the smoker", "Check the queen",
                                                  "Look for brood"]},
    "definitions": {"kind": "definitions", "terms": [
        {"term": "Pollen", "text": "The fine powder that carries the male cells."},
        {"term": "Nectar", "text": "The sweet liquid flowers offer."}]},
    "mistakes": {"kind": "mistakes", "pairs": [
        {"wrong": "Mowing every week", "right": "Leave patches to flower"},
        {"wrong": "Spraying in bloom", "right": "Spray in the evening"}]},
    "scale": {"kind": "scale", "left": "Low risk", "right": "High risk", "marks": [
        {"label": "Bumblebee", "pos": 0.1}, {"label": "Wasp", "pos": 0.7}, {"label": "Hornet", "pos": 2}]},
    "venn": {"kind": "venn", "a": {"title": "Honeybee", "items": ["Stores honey"]},
             "b": {"title": "Bumblebee", "items": ["Flies in the cold"]}, "both": ["Pollinate"]},
    "tree": {"kind": "tree", "root": "A colony", "branches": [
        {"title": "Queen", "leaves": ["Lays eggs"]}, {"title": "Workers", "leaves": ["Collect food", "Defend"]},
        {"title": "Drones", "leaves": ["Mate"]}]},
    "example": {"kind": "example", "situation": "A garden gets no bee visits.",
                "steps": ["Count what flowers", "Add early bloomers"], "result": "Wild bees nest there in May."},
}
# Each form cut down to less than it needs, it then becomes bullets.
TOO_LITTLE = {
    "timeline": {"kind": "timeline", "events": FORMS["timeline"]["events"][:2]},
    "cycle": {"kind": "cycle", "steps": FORMS["cycle"]["steps"][:2]},
    "versus": {"kind": "versus", "a": FORMS["versus"]["a"]},
    "matrix": {"kind": "matrix", "x": "Effort", "y": "Impact", "cells": FORMS["matrix"]["cells"][:3]},
    "quote": {"kind": "quote", "text": ""},
    "checklist": {"kind": "checklist", "items": ["Only one"]},
    "definitions": {"kind": "definitions", "terms": FORMS["definitions"]["terms"][:1]},
    "mistakes": {"kind": "mistakes", "pairs": FORMS["mistakes"]["pairs"][:1]},
    "scale": {"kind": "scale", "left": "Low", "marks": FORMS["scale"]["marks"]},
    "venn": {"kind": "venn", "a": FORMS["venn"]["a"], "b": FORMS["venn"]["b"], "both": []},
    "tree": {"kind": "tree", "root": "A colony", "branches": FORMS["tree"]["branches"][:1]},
    "example": {"kind": "example", "situation": "A garden.", "steps": ["One", "Two"], "result": ""},
}


def analysis_of(name="clean"):
    data, analysis, _ = library.load(name)
    return data, template.without_pictures(analysis)


@pytest.fixture(scope="module")
def spec():
    _, analysis = analysis_of()
    return template.spec_for(analysis.layout(analysis.roles["text"][0]), analysis)


def parse(body, spec):
    answer = json.dumps({"slides": [{"id": "s1", "title": "Heading", "body": body}]})
    row = OutlineRow(id="s1", role="text", title="A title", gist="It shows something.")
    return sl.parse_answer(answer, [row], {"s1": spec})[0]


@pytest.mark.parametrize("kind", sorted(FORMS))
def test_every_form_is_offered_and_parsed(kind, spec):
    assert kind in spec["body_kinds"]
    assert parse(FORMS[kind], spec).body.kind == kind


@pytest.mark.parametrize("kind", sorted(TOO_LITTLE))
def test_a_form_with_too_little_in_it_becomes_bullets(kind, spec):
    assert parse(TOO_LITTLE[kind], spec).body.kind == "bullets"


def test_scale_marks_stay_on_the_scale_and_in_order(spec):
    marks = parse(FORMS["scale"], spec).body.marks
    assert [m.pos for m in marks] == [0.1, 0.7, 1.0]


def test_a_quote_drops_an_emphasis_it_does_not_contain(spec):
    body = parse({"kind": "quote", "text": "Bees matter.", "emphasis": "honey"}, spec).body
    assert body.kind == "quote" and body.emphasis == ""


def test_the_prompt_names_the_limit_of_every_counted_form(spec):
    row = OutlineRow(id="s1", role="text", title="A title", gist="It shows something.")
    from outline2pptx.schemas import DeckParams

    user = sl.build_messages("Bees", DeckParams(), [row], {"s1": spec})[1]["content"]
    assert "timeline: 3 to" in user and "checklist: 3 to" in user


@pytest.mark.parametrize("name", ["clean", "warm", "forest"])
def test_every_form_is_drawn_inside_the_slide(name, spec):
    data, analysis = analysis_of(name)
    layouts = [analysis.layout(i) for i in analysis.roles["text"]]
    slides = []
    for layout in layouts:
        form = template.spec_for(layout, analysis)
        for kind, raw in FORMS.items():
            if kind not in form["body_kinds"]:
                continue
            row = OutlineRow(id=f"{layout.index}-{kind}", role="text", title=kind)
            s = sl._slide(row, {"title": kind, "body": raw}, form)
            assert s.body.kind == kind
            s.layout = layout.index
            slides.append(s)
    assert len(slides) >= len(FORMS)
    deck = Presentation(BytesIO(build_deck(data, analysis, slides, {}, "Forms", False)))
    width, height = deck.slide_width, deck.slide_height
    for s, built in zip(slides, deck.slides):
        drawn = [sh for sh in built.shapes if not sh.is_placeholder]
        assert len(drawn) >= 3, s.id
        field = analysis.layout(s.layout).of_kind("body")[0]
        # Nothing runs down into the footer below the content field.
        assert max(sh.top + sh.height for sh in drawn if not sh.rotation) <= field.top + field.height + 2 * 12700, s.id
        for sh in drawn:
            # The rotated axis label of the matrix is measured before its turn.
            if sh.rotation:
                continue
            assert sh.left >= 0 and sh.top >= 0, (s.id, sh.name)
            assert sh.left + sh.width <= width + 1 and sh.top + sh.height <= height + 1, (s.id, sh.name)
