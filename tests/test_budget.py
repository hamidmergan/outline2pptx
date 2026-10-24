"""The size budget: what one call may carry, and what happens when the material is larger.

Material that does not fit the window is never cut off silently. It is boiled down to the
topics it covers, one call per piece, and the deck is planned from those. The inputs here
are deliberately larger than the window, because a short string never reaches any of it.
"""

import json

import pytest

from outline2pptx import budget as bd
from outline2pptx import config
from outline2pptx.errors import ConfigError, ModelError


def test_the_window_decides_how_much_one_call_may_carry():
    limit = bd.window_chars(131_072)
    reserved = config.PROMPT_TOKENS + config.OUTPUT_TOKENS
    assert limit == int((131_072 - reserved) * config.CHARS_PER_TOKEN)
    # A larger window carries more, a smaller one less.
    assert bd.window_chars(262_144) > limit > bd.window_chars(32_768)


def test_a_window_too_small_for_a_deck_is_refused_by_name():
    with pytest.raises(ConfigError) as exc:
        bd.window_chars(config.MIN_WINDOW_TOKENS - 1)
    assert "--context-window" in str(exc.value)
    assert str(config.MIN_WINDOW_TOKENS) in str(exc.value)


def test_material_is_cut_into_pieces_at_block_boundaries():
    blocks = [f"Block {n} " + "x" * 300 for n in range(1, 11)]
    parts = bd.pieces("\n\n".join(blocks), 1000)
    assert len(parts) > 1
    assert all(len(p) <= 1000 for p in parts)
    # No block is lost and none is torn apart where a boundary was available.
    rejoined = "".join(parts)
    for n in range(1, 11):
        assert f"Block {n}" in rejoined


def test_one_block_longer_than_the_window_is_cut_where_it_has_to_be():
    parts = bd.pieces("y" * 2500, 1000)
    assert [len(p) for p in parts] == [1000, 1000, 500]


def test_material_that_fits_goes_in_untouched():
    plan = bd.Budget(_never_asked, "en", config.MIN_WINDOW_TOKENS)
    material = "A sentence about heat pumps. " * 10
    assert plan.fit(material) == material
    assert plan.shortened is False


def test_material_larger_than_the_window_is_planned_through_its_topics():
    asked = []

    def ask(messages):
        asked.append(messages)
        number = len(asked)
        return json.dumps({"topics": [
            {"title": f"Topic {number}", "gist": f"What part {number} says."}]})

    plan = bd.Budget(ask, "de", config.MIN_WINDOW_TOKENS)
    material = "\n\n".join(f"Abschnitt {n}: " + "w" * 2000 for n in range(1, 60))
    assert len(material) > plan.limit     # the test input really is too large
    short = plan.fit(material)
    assert plan.shortened is True
    assert len(short) <= plan.limit
    assert len(asked) == len(bd.pieces(material, plan.limit)) > 1
    assert "1. Topic 1: What part 1 says." in short
    # Every part of the material was mapped, and the parts know their place.
    first = asked[0][0]["content"]
    assert f"part 1 of {len(asked)}" in first
    assert "in German" in first
    assert "slide deck" in first
    # The topics are paid for once, a second call reads the same shortened material.
    assert plan.fit(material) == short
    assert len(asked) == len(bd.pieces(material, plan.limit))


def test_a_lost_piece_costs_its_topics_and_not_the_run():
    calls = []

    def ask(messages):
        calls.append(messages)
        if len(calls) == 1:
            raise RuntimeError("the server dropped the request")
        return json.dumps({"topics": [{"title": "Still here", "gist": "What it says."}]})

    plan = bd.Budget(ask, "en", config.MIN_WINDOW_TOKENS)
    material = "\n\n".join(f"Section {n}: " + "w" * 2000 for n in range(1, 60))
    short = plan.fit(material)
    assert "Still here" in short
    assert len(calls) > 1


def test_material_that_yields_no_topics_at_all_is_refused_with_what_to_do():
    plan = bd.Budget(lambda messages: "no json here", "en", config.MIN_WINDOW_TOKENS)
    material = "\n\n".join(f"Section {n}: " + "w" * 2000 for n in range(1, 60))
    with pytest.raises(ModelError) as exc:
        plan.fit(material)
    message = str(exc.value)
    assert "longer than the model window" in message
    assert "--context-window" in message


def test_the_topic_cap_shares_itself_out_over_the_parts():
    counts = []

    def ask(messages):
        system = messages[0]["content"]
        counts.append(int(system.split("at most ")[1].split(",")[0]))
        return json.dumps({"topics": []})

    plan = bd.Budget(ask, "en", config.MIN_WINDOW_TOKENS)
    material = "\n\n".join(f"Section {n}: " + "w" * 2000 for n in range(1, 200))
    with pytest.raises(ModelError):
        plan.fit(material)
    parts = len(bd.pieces(material, plan.limit))
    assert counts and all(c == max(1, min(config.MAX_TOPICS_PER_PART,
                                          config.MAX_TOPICS_TOTAL // parts)) for c in counts)


def test_more_topics_than_asked_for_are_cut_back_to_the_cap():
    many = {"topics": [{"title": f"T{n}", "gist": "g"} for n in range(1, 40)]}
    assert len(bd.parse_topics(json.dumps(many), 5)) == 5
    # A nameless topic is no topic.
    assert bd.parse_topics(json.dumps({"topics": [{"gist": "no title"}]}), 5) == []
    # Thinking around the answer does not stop it from being read.
    wrapped = "<think>hmm</think>\n" + json.dumps({"topics": [{"title": "A", "gist": "b"}]})
    assert bd.parse_topics(wrapped, 5) == [("A", "b")]
    assert bd.parse_topics(None, 5) == []
    assert bd.parse_topics("{not json}", 5) == []


def _never_asked(messages):
    raise AssertionError("material that fits must not cost a model call")
