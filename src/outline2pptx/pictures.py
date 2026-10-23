"""Every picture a deck needs: drawn by the image model, or a plain tinted placeholder without one."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from . import image
from .build import image_key
from .config import Settings
from .errors import ModelError
from .schemas import Slide
from .template import Analysis, Field

log = logging.getLogger(__name__)


def _fields(a: Analysis, slide: Slide, layout_index: int) -> list[tuple[str, Field, str]]:
    """Key, field and prompt of every picture slot of one slide, in the order the builder reads them."""
    layout = a.layout(layout_index)
    out: list[tuple[str, Field, str]] = []
    picture_fields = layout.of_kind("picture")
    for k, field in enumerate(picture_fields):
        prompt = slide.images[k].prompt if k < len(slide.images) else slide.title
        out.append((image_key(slide.id, k), field, prompt))
    if slide.body is not None and slide.body.kind == "image" and slide.body.prompt:
        body_fields = layout.of_kind("body")
        if body_fields:
            out.append((image_key(slide.id, "body"), body_fields[0], slide.body.prompt))
    return out


def plan(a: Analysis, slides: list[Slide], layouts: dict[str, int]) -> list[tuple[str, Field, str]]:
    """Every picture the deck asks for, over all its slides."""
    out: list[tuple[str, Field, str]] = []
    for s in slides:
        out.extend(_fields(a, s, layouts[s.id]))
    return out


def draw(a: Analysis, slides: list[Slide], layouts: dict[str, int], settings: Settings,
         style_text: str, color: str, client=None) -> dict[str, bytes]:
    """The pictures by key. Without an image model every field gets a tinted placeholder."""
    wanted = plan(a, slides, layouts)
    if not wanted:
        return {}
    if not settings.images or not settings.has_image_model:
        return {key: image.placeholder(f.width, f.height, color) for key, f, _ in wanted}
    if client is None:
        from .llm import make_image_client

        client = make_image_client(settings)

    def one(job):
        key, field, prompt = job
        size = image.image_size(field.width, field.height)
        try:
            return key, image.generate(client, settings, image.prompt_for(style_text, prompt), size)
        except ModelError as exc:
            log.warning("No picture for %s, a placeholder steps in: %s", key, exc)
            return key, image.placeholder(field.width, field.height, color)

    workers = max(1, min(settings.image_parallelism, len(wanted)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(one, wanted))
