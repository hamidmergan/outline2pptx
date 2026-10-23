import shutil
from io import BytesIO

import pytest
from pptx import Presentation

from outline2pptx import config, image, library, pictures, preview, render
from outline2pptx.deck import build_deck
from outline2pptx.errors import PreviewError
from outline2pptx.schemas import Body, ImageSpec, Slide

HAS_LIBREOFFICE = render.available()


@pytest.fixture(scope="module")
def clean():
    return library.load("clean")


def settings_for(server=None, images=True):
    if server is None:
        return config.resolve(base_url="http://x/v1", model="m", images=False)
    return config.resolve(base_url=server.base_url, model="m",
                          image_base_url=server.base_url, image_model="draw", images=images)


def picture_slides(analysis):
    index = analysis.roles["text_with_image"][0]
    return [Slide(id="s1", role="text_with_image", layout=index, title="A picture slide",
                  images=[ImageSpec(prompt="a quiet library")])], {"s1": index}


def test_image_size_follows_the_field():
    assert image.image_size(5303520, 4300000) == "1744x1408"
    # a tiny field still gets a usable picture, a huge one stays capped
    assert image.image_size(10000, 10000) == "768x768"
    assert image.image_size(12192000, 1000000) == "1920x256"


def test_a_quoted_word_is_taken_out_of_a_prompt():
    assert '"Quiet"' not in image.prompt_for("Flat.", 'A door with a sign "Quiet" on it')
    assert image.prompt_for("Flat.", "A door").startswith("Flat. Subject: A door")
    assert image.NO_LETTERING in image.prompt_for("", "A door")


def test_without_an_image_model_every_field_gets_a_placeholder(clean):
    _, analysis, _ = clean
    slides, layouts = picture_slides(analysis)
    drawn = pictures.draw(analysis, slides, layouts, settings_for(), "Flat.", "2563EB")
    assert set(drawn) == {"s1_0"}
    assert drawn["s1_0"].startswith(b"\x89PNG")


def test_the_image_model_draws_every_field(clean, server):
    _, analysis, _ = clean
    slides, layouts = picture_slides(analysis)
    drawn = pictures.draw(analysis, slides, layouts, settings_for(server), "Flat.", "2563EB")
    assert set(drawn) == {"s1_0"}
    assert drawn["s1_0"] == server.image_bytes
    assert server.kinds() == ["image"]
    body = server.requests[0]["body"]
    assert body["model"] == "draw"
    assert body["size"] == image.image_size(*_field_size(analysis))
    assert "a quiet library" in body["prompt"]


def _field_size(analysis):
    layout = analysis.layout(analysis.roles["text_with_image"][0])
    field = layout.of_kind("picture")[0]
    return field.width, field.height


def test_a_refused_size_is_retried_as_a_square(clean, server):
    _, analysis, _ = clean
    slides, layouts = picture_slides(analysis)
    server.image_status = 400
    drawn = pictures.draw(analysis, slides, layouts, settings_for(server), "Flat.", "2563EB")
    # both sizes were refused, so a placeholder stepped in
    assert len(server.requests) == 2
    assert server.requests[1]["body"]["size"] == "1024x1024"
    assert drawn["s1_0"].startswith(b"\x89PNG")


def test_a_failing_image_model_falls_back_to_a_placeholder(clean, server):
    _, analysis, _ = clean
    slides, layouts = picture_slides(analysis)
    server.fail = True
    drawn = pictures.draw(analysis, slides, layouts, settings_for(server), "Flat.", "2563EB")
    assert drawn["s1_0"].startswith(b"\x89PNG")


def test_a_drawn_picture_reaches_the_deck(clean):
    data, analysis, _ = clean
    slides, layouts = picture_slides(analysis)
    drawn = pictures.draw(analysis, slides, layouts, settings_for(), "Flat.", "2563EB")
    deck = build_deck(data, analysis, slides, drawn, "A Deck", False)
    prs = Presentation(BytesIO(deck))
    pictures_on_slide = [s for s in prs.slides[0].shapes if hasattr(s, "image")]
    assert len(pictures_on_slide) == 1
    assert pictures_on_slide[0].image.blob


def test_images_need_a_model_in_the_settings():
    from outline2pptx.errors import ConfigError

    with pytest.raises(ConfigError, match="no image model"):
        config.resolve(base_url="http://x/v1", model="m", images=True)


@pytest.mark.skipif(HAS_LIBREOFFICE, reason="LibreOffice is installed here")
def test_preview_says_so_when_libreoffice_is_missing(clean):
    data, analysis, _ = clean
    deck = build_deck(data, analysis, [Slide(id="s1", role="cover", title="A")], {}, "A", False)
    with pytest.raises(PreviewError, match="LibreOffice"):
        preview.render(deck)


@pytest.mark.skipif(not HAS_LIBREOFFICE, reason="LibreOffice is not installed here")
def test_preview_renders_one_png_per_slide(clean):
    data, analysis, _ = clean
    slides = [Slide(id="s1", role="cover", title="A Deck"),
              Slide(id="s2", role="closing", title="Done")]
    deck = build_deck(data, analysis, slides, {}, "A Deck", False)
    pngs = preview.render(deck)
    assert len(pngs) == 2
    assert all(p.startswith(b"\x89PNG") for p in pngs)


def test_available_checks_the_three_tools(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/" + name)
    assert render.available()
    monkeypatch.setattr(shutil, "which", lambda name: None if name == "pdftoppm" else "/usr/bin/x")
    assert not render.available()
