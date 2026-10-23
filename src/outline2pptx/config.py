"""Default values and resolution of settings.

Order: argument, then environment variable, then default. The chat model writes the deck, the
image model draws its illustrations and falls back to the chat values when it has none of its own.
"""

import os
from dataclasses import dataclass
from typing import Optional

from .errors import ConfigError
from .schemas import DEFAULT_TEMPLATE, MAX_SLIDES, MIN_SLIDES

__all__ = ["Settings", "resolve", "MAX_SLIDES", "MIN_SLIDES"]

# Limits
MAX_OUTLINE_CHARS = 200_000
MAX_TOPIC_CHARS = 2000
# How many slides the model writes in one content call.
BATCH = 5
# How many content calls and how many pictures run at the same time.
WRITE_PARALLELISM = 3
IMAGE_PARALLELISM = 4
TIMEOUT_SECONDS = 180
IMAGE_TIMEOUT_SECONDS = 300
MAX_RETRIES = 2
# The language the deck is written in when none is given.
DEFAULT_LANGUAGE = "en"
# The look every picture of a deck shares when the caller names no style of its own.
DEFAULT_STYLE_TEXT = (
    "A warm, hand-painted editorial illustration with soft shapes, a light background and "
    "a calm palette."
)
# The note in the bottom right corner of every slide, empty switches it off.
DEFAULT_NOTICE = ""

# Placeholder, because the OpenAI library requires a value. Local servers ignore it.
PLACEHOLDER_API_KEY = "not-needed"

ENV_PREFIX = "OUTLINE2PPTX_"


@dataclass(frozen=True)
class Settings:
    base_url: str
    model: str
    api_key: str
    image_base_url: str
    image_model: str
    image_api_key: str
    language: str
    template: str
    template_dir: Optional[str]
    slides: Optional[int]
    images: bool
    notes: bool
    presenter: str
    style_text: str
    instructions: str
    notice: str
    batch: int
    write_parallelism: int
    image_parallelism: int
    timeout: float
    image_timeout: float
    max_retries: int

    @property
    def has_image_model(self) -> bool:
        return bool(self.image_base_url and self.image_model)


def _env(name: str) -> Optional[str]:
    value = os.environ.get(ENV_PREFIX + name)
    if value is None or value.strip() == "":
        return None
    return value.strip()


def _pick(arg, env_name: str, default, cast):
    if arg is not None:
        return arg
    raw = _env(env_name)
    if raw is None:
        return default
    try:
        return cast(raw)
    except ValueError:
        raise ConfigError(
            f"Environment variable {ENV_PREFIX}{env_name} has an invalid value: {raw!r}"
        )


def resolve(
    *,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    image_base_url: Optional[str] = None,
    image_model: Optional[str] = None,
    image_api_key: Optional[str] = None,
    language: Optional[str] = None,
    template: Optional[str] = None,
    template_dir: Optional[str] = None,
    slides: Optional[int] = None,
    images: Optional[bool] = None,
    notes: Optional[bool] = None,
    presenter: Optional[str] = None,
    style_text: Optional[str] = None,
    instructions: Optional[str] = None,
    notice: Optional[str] = None,
    batch: Optional[int] = None,
    write_parallelism: Optional[int] = None,
    image_parallelism: Optional[int] = None,
    timeout: Optional[float] = None,
    image_timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    need_model: bool = True,
) -> Settings:
    """The settings of one run. ``need_model`` is False where no model is called at all."""
    base_url = _pick(base_url, "BASE_URL", None, str)
    model = _pick(model, "MODEL", None, str)
    if need_model:
        missing = []
        if not base_url:
            missing.append("base_url (--base-url or OUTLINE2PPTX_BASE_URL)")
        if not model:
            missing.append("model (--model or OUTLINE2PPTX_MODEL)")
        if missing:
            raise ConfigError(
                "Missing: " + " and ".join(missing) + ". "
                "Example for Ollama: base_url http://localhost:11434/v1 and a text model."
            )

    key = _pick(api_key, "API_KEY", None, str)
    if not key:
        key = os.environ.get("OPENAI_API_KEY") or PLACEHOLDER_API_KEY

    image_base_url = _pick(image_base_url, "IMAGE_BASE_URL", None, str) or base_url or ""
    image_model = _pick(image_model, "IMAGE_MODEL", None, str) or ""
    image_key = _pick(image_api_key, "IMAGE_API_KEY", None, str) or key

    want_images = _pick(images, "IMAGES", False, _flag)
    if want_images and not (image_base_url and image_model):
        raise ConfigError(
            "Images were asked for but no image model is set: "
            "image_model (--image-model or OUTLINE2PPTX_IMAGE_MODEL) and an image_base_url."
        )

    count = _pick(slides, "SLIDES", None, int)
    if count is not None and not MIN_SLIDES <= count <= MAX_SLIDES:
        raise ConfigError(f"slides must be between {MIN_SLIDES} and {MAX_SLIDES}, not {count}")

    return Settings(
        base_url=base_url or "",
        model=model or "",
        api_key=key,
        image_base_url=image_base_url,
        image_model=image_model,
        image_api_key=image_key,
        language=_pick(language, "LANGUAGE", DEFAULT_LANGUAGE, str),
        template=_pick(template, "TEMPLATE", DEFAULT_TEMPLATE, str),
        template_dir=_pick(template_dir, "TEMPLATE_DIR", None, str),
        slides=count,
        images=want_images,
        notes=_pick(notes, "NOTES", False, _flag),
        presenter=_pick(presenter, "PRESENTER", "", str),
        style_text=_pick(style_text, "STYLE_TEXT", DEFAULT_STYLE_TEXT, str),
        instructions=_pick(instructions, "INSTRUCTIONS", "", str),
        notice=_pick(notice, "NOTICE", DEFAULT_NOTICE, str),
        batch=_pick(batch, "BATCH", BATCH, int),
        write_parallelism=_pick(write_parallelism, "WRITE_PARALLELISM", WRITE_PARALLELISM, int),
        image_parallelism=_pick(image_parallelism, "IMAGE_PARALLELISM", IMAGE_PARALLELISM, int),
        timeout=_pick(timeout, "TIMEOUT", TIMEOUT_SECONDS, float),
        image_timeout=_pick(image_timeout, "IMAGE_TIMEOUT", IMAGE_TIMEOUT_SECONDS, float),
        max_retries=_pick(max_retries, "MAX_RETRIES", MAX_RETRIES, int),
    )


def _flag(raw) -> bool:
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("1", "true", "yes", "on")
