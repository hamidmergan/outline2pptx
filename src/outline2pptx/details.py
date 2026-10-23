"""What a deck was made with, for the info shown next to the result."""

from .schemas import DeckParams


def details(params: DeckParams, model: str = "", image_model: str = "") -> dict:
    """Template, language, source, instruction and picture style, plus who wrote and who drew."""
    return {"model": model, "image_model": image_model,
            "template": params.template_name or params.template_id, "language": params.language,
            "instructions": params.instructions.strip(), "style_text": params.style_text.strip(),
            "source": params.source_label}
