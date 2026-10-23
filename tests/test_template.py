"""Reading a template that is not one of the packaged ones."""

from io import BytesIO

import pytest
from pptx import Presentation

from outline2pptx import library, template


def renamed(layout_name: str, new_name: str) -> bytes:
    """The packaged template with one of its layouts under another name."""
    data, _, _ = library.load("clean")
    prs = Presentation(BytesIO(data))
    layout = next(l for l in prs.slide_masters[0].slide_layouts if l.name == layout_name)
    layout.name = new_name
    out = BytesIO()
    prs.save(out)
    return out.getvalue()


def role_of(layout_name: str, new_name: str) -> str | None:
    analysis = template.analyse(renamed(layout_name, new_name))
    return next(l.role for l in analysis.layouts if l.name == new_name)


@pytest.mark.parametrize("name", ["Agenda", "Appendix", "Calendar", "Trends", "Legend",
                                  "Kalender", "Legende", "Trendwende", "Content"])
def test_an_ordinary_layout_name_is_not_read_as_the_closing_slide(name):
    assert role_of("Title and Content", name) == "text"


@pytest.mark.parametrize("name", ["Closing", "Thank You", "The End", "Ende", "Abschluss",
                                  "Abschlussfolie", "Danke", "Ending"])
def test_a_closing_layout_is_found_in_english_and_in_german(name):
    assert role_of("Title and Content", name) == "closing"


@pytest.mark.parametrize("name", ["Section Divider", "Abschnitt", "Abschnittstitel"])
def test_a_divider_layout_is_found_in_english_and_in_german(name):
    assert role_of("Title and Content", name) == "section"


def test_a_closing_layout_stays_out_of_the_selectable_roles():
    analysis = template.analyse(renamed("Title and Content", "Agenda"))
    assert "Agenda" in [l.name for l in analysis.layouts if l.role == "text"]
    assert sorted(template.selectable_roles(analysis)) == [
        "section", "text", "text_with_image", "two_columns"]
