"""Build PowerPoint slide decks from a Markdown outline, a topic or your documents."""

__version__ = "0.1.0"

from .api import Deck, build, list_templates, outline_from_material, outline_from_topic
from .errors import (
    ConfigError, DeckError, LimitError, ModelError, NoReadableText, OutlineError,
    PreviewError, TemplateError, UnsupportedFileError,
)
from .material import Material, read as read_material, text_material

__all__ = [
    "Deck",
    "build",
    "list_templates",
    "outline_from_topic",
    "outline_from_material",
    "Material",
    "read_material",
    "text_material",
    "DeckError",
    "ConfigError",
    "TemplateError",
    "ModelError",
    "OutlineError",
    "PreviewError",
    "LimitError",
    "UnsupportedFileError",
    "NoReadableText",
    "__version__",
]
