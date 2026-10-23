"""The arithmetic behind the drawn elements: the grid, the room below a heading and the grid search."""

import pytest

from outline2pptx import grid, space
from outline2pptx.diagrams import _better, _largest
from outline2pptx.template import EMU_PER_PT, Field

INCH = 914400


def field(idx=1, kind="body", left=0, top=0, width=8 * INCH, height=3 * INCH, **kwargs):
    return Field(idx=idx, kind=kind, ph_type="OBJECT", left=left, top=top, width=width,
                 height=height, **kwargs)


# The grid


@pytest.mark.parametrize("n, columns, expected", [
    (7, 3, [3, 2, 2]),
    (6, 3, [3, 3]),
    (5, 3, [3, 2]),
    (4, 3, [2, 2]),
    (3, 3, [3]),
    (1, 3, [1]),
    (0, 3, []),
    (3, 1, [1, 1, 1]),
    (8, 4, [4, 4]),
    (5, 4, [3, 2]),
])
def test_distribution_fills_the_fewest_rows_as_evenly_as_it_can(n, columns, expected):
    assert grid.distribution(n, columns) == expected


@pytest.mark.parametrize("n", range(1, 13))
@pytest.mark.parametrize("columns", range(1, 5))
def test_distribution_always_places_every_entry(n, columns):
    rows = grid.distribution(n, columns)
    assert sum(rows) == n
    assert all(k >= 1 for k in rows)
    assert max(rows) <= max(columns, 1)
    # The fuller rows come first, so the grid never grows towards the bottom.
    assert rows == sorted(rows, reverse=True)


def test_card_space_grows_with_the_field_and_stays_within_the_cap():
    small = grid.card_space(4 * INCH, 2 * INCH, 16.0)
    large = grid.card_space(12 * INCH, 5 * INCH, 16.0)
    assert small["max"] < large["max"] <= grid.MAX_CARDS
    assert small["title_words"] >= 2 and small["text_words"] >= 4


def test_the_word_budget_follows_the_card_width_not_the_field_width():
    # Both fields hold two columns, so the wider one gives each card more room.
    narrow = grid.card_space(540 * EMU_PER_PT, 5 * INCH, 16.0)
    wide = grid.card_space(700 * EMU_PER_PT, 5 * INCH, 16.0)
    assert grid.card_grid(540 * EMU_PER_PT, 5 * INCH, 16.0)[0] == 2
    assert grid.card_grid(700 * EMU_PER_PT, 5 * INCH, 16.0)[0] == 2
    assert wide["title_words"] > narrow["title_words"]
    assert wide["text_words"] > narrow["text_words"]


def test_a_larger_body_size_leaves_room_for_fewer_cards():
    assert grid.card_space(12 * INCH, 5 * INCH, 10.0)["max"] >= grid.card_space(
        12 * INCH, 5 * INCH, 18.0)["max"]


def test_card_grid_counts_columns_and_rows_apart():
    columns, rows = grid.card_grid(12 * INCH, 5 * INCH, 16.0)
    assert columns >= 2 and rows >= 1
    assert grid.card_grid(2 * INCH, 1 * INCH, 16.0) == (1, 1)


def test_every_space_function_stays_inside_its_own_cap():
    assert grid.bar_space(20 * INCH, 16.0) == grid.MAX_BARS
    assert grid.figure_space(40 * INCH, 16.0) == grid.MAX_FIGURES
    assert grid.symbol_space(40 * INCH, 40 * INCH, 16.0) == grid.MAX_SYMBOLS
    assert grid.step_space(40 * INCH, 16.0)["max"] == grid.MAX_STEPS
    assert grid.level_space(10 * INCH, 40 * INCH, 16.0)["max"] == grid.MAX_LEVELS
    # A field too small for even one entry still holds one.
    assert grid.bar_space(0, 16.0) == 1
    assert grid.figure_space(0, 16.0) == 1


def test_base_pt_caps_a_poster_sized_body_and_fills_in_a_missing_one():
    assert grid.base_pt(0.0) == grid.DEFAULT_PT
    assert grid.base_pt(40.0) == grid.MAX_BASE_PT
    assert grid.base_pt(14.0) == 14.0


# The room below a heading


def test_line_height_follows_the_template_pitch_where_it_sets_one():
    fixed = field(kind="heading", size_pt=20.0, line_pt=30.0)
    assert space.line_height(fixed, 10.0) == 15.0
    free = field(kind="heading", size_pt=20.0)
    assert space.line_height(free, 10.0) == pytest.approx(12.0)


def test_head_bottom_follows_the_anchor():
    top_anchored = field(kind="heading", top=INCH, height=INCH, size_pt=20.0, anchor="t",
                         inset_top=0, inset_v=0)
    one_line = int(1 * space.line_height(top_anchored, 20.0) * EMU_PER_PT)
    assert space.head_bottom(top_anchored, "Short", "Poppins", 20.0) == INCH + one_line
    bottom_anchored = field(kind="heading", top=INCH, height=INCH, size_pt=20.0, anchor="b",
                            inset_bottom=0)
    assert space.head_bottom(bottom_anchored, "Short", "Poppins", 20.0) == 2 * INCH


def test_a_heading_that_wraps_ends_further_down():
    head = field(kind="heading", top=0, width=3 * INCH, height=INCH, size_pt=28.0, inset_h=0,
                 inset_top=0)
    short = space.head_bottom(head, "Short", "Poppins", 28.0)
    long = space.head_bottom(head, "A heading long enough that it needs several lines of its own "
                                   "before the content below can start", "Poppins", 28.0)
    assert long > short


def test_only_the_fields_below_the_heading_count():
    head = field(idx=0, kind="heading", top=0, height=INCH)
    body = field(idx=1, kind="body", top=2 * INCH)
    beside = field(idx=2, kind="body", top=0)
    margin = field(idx=3, kind="margin_text", top=5 * INCH)
    assert [f.idx for f in space.below([head, body, beside, margin], head)] == [1]


def test_nothing_moves_while_the_heading_stays_in_its_own_box():
    head = field(idx=0, kind="heading", top=0, height=INCH)
    body = field(idx=1, kind="body", top=2 * INCH, height=3 * INCH)
    assert space.moved([head, body], head, bottom=INCH // 2, air=0, slide_height=7 * INCH) == {}


def test_a_long_heading_pushes_the_body_down_and_makes_it_shorter():
    head = field(idx=0, kind="heading", top=0, height=INCH)
    body = field(idx=1, kind="body", top=2 * INCH, height=3 * INCH)
    out = space.moved([head, body], head, bottom=3 * INCH, air=0, slide_height=7 * INCH)
    assert out[1].top == 3 * INCH
    assert out[1].height == 2 * INCH
    # The field keeps its bottom edge while it still has height to give.
    assert out[1].top + out[1].height == body.top + body.height


def test_a_body_never_gives_up_more_than_half_its_height():
    head = field(idx=0, kind="heading", top=0, height=INCH)
    body = field(idx=1, kind="body", top=2 * INCH, height=3 * INCH)
    out = space.moved([head, body], head, bottom=4 * INCH, air=0, slide_height=10 * INCH)
    assert out[1].top == 4 * INCH
    assert out[1].height == pytest.approx(1.5 * INCH, abs=2)


def test_a_row_of_subheadings_alone_only_ever_moves():
    head = field(idx=0, kind="heading", top=0, height=INCH)
    left = field(idx=1, kind="subheading", left=0, top=2 * INCH, height=INCH)
    right = field(idx=2, kind="subheading", left=5 * INCH, top=2 * INCH, height=INCH)
    out = space.moved([head, left, right], head, bottom=3 * INCH, air=0, slide_height=10 * INCH)
    assert out[1].height == left.height and out[2].height == right.height
    assert out[1].top == out[2].top == 3 * INCH


def test_a_moved_field_never_leaves_the_slide():
    head = field(idx=0, kind="heading", top=0, height=INCH)
    body = field(idx=1, kind="body", top=2 * INCH, height=3 * INCH)
    out = space.moved([head, body], head, bottom=6 * INCH, air=0, slide_height=6 * INCH)
    assert out[1].top + out[1].height <= 6 * INCH


def test_air_is_one_line_of_the_body_text_and_falls_back_to_the_subheading():
    body = field(kind="body", size_pt=18.0)
    assert space.air([body]) == int(space.AIR_LINES * 18.0 * 1.2 * EMU_PER_PT)
    sub = field(kind="subheading", size_pt=24.0)
    assert space.air([sub]) == int(space.AIR_LINES * 24.0 * 1.2 * EMU_PER_PT)


# The grid search


def test_a_layout_that_fits_beats_one_that_does_not():
    assert _better((True, 1.0, ()), (False, 5.0, ()))
    assert not _better((False, 5.0, ()), (True, 1.0, ()))


def test_among_those_that_fit_the_larger_text_wins():
    assert _better((True, 1.1, ()), (True, 1.0, ()))
    assert not _better((True, 1.0, ()), (True, 1.1, ()))


def test_a_tie_keeps_the_earlier_layout():
    assert not _better((True, 1.0, ()), (True, 1.0, ()))


def test_the_first_layout_always_wins():
    assert _better((False, 0.1, ()), None)


def test_largest_takes_the_biggest_scale_that_fits():
    seen = []

    def measure(k):
        seen.append(k)
        return k <= 1.0, ("mass", k)

    fits, k, mass = _largest(measure, 16.0)
    assert fits and k <= 1.0
    assert seen[0] == pytest.approx(1 / grid.TEXT_RATIO)
    assert mass == ("mass", k)


def test_largest_gives_up_at_the_smallest_readable_size():
    fits, k, _ = _largest(lambda k: (False, ()), 16.0)
    assert not fits
    assert grid.TEXT_RATIO * 16.0 * k >= 10.0
