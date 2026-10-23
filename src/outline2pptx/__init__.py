"""Build PowerPoint slide decks from a Markdown outline or a topic."""

__version__ = "0.1.0"

from .api import Deck, build, list_templates, outline_from_topic
from .errors import ConfigError, DeckError, ModelError, PreviewError, TemplateError

__all__ = [
    "Deck",
    "build",
    "list_templates",
    "outline_from_topic",
    "DeckError",
    "ConfigError",
    "TemplateError",
    "ModelError",
    "PreviewError",
    "__version__",
]
