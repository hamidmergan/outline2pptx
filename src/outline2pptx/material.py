"""The material of one deck: the documents it is planned over, read into one text.

Every source keeps its file name, so the model can tell two documents apart and give
each of them slides of its own.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, Union

from . import config
from .errors import LimitError, NoReadableText
from .source_reading import EXTENSIONS, Source, from_text, read_file

log = logging.getLogger(__name__)

__all__ = ["EXTENSIONS", "Material", "from_text", "read", "text_material"]

Paths = Union[str, Path, Iterable[Union[str, Path]]]


@dataclass(frozen=True)
class Material:
    """What a deck is planned over: the read documents and the block the model sees."""

    sources: list[Source]

    @property
    def names(self) -> list[str]:
        return [s.name for s in self.sources]

    @property
    def chars(self) -> int:
        return sum(len(s.text) for s in self.sources)

    @property
    def pages(self) -> int:
        return sum(s.pages for s in self.sources)

    @property
    def block(self) -> str:
        """Every source as one text, each under its file name.

        The name travels with it so the model can tell two documents apart, nothing more.
        """
        return "\n\n".join(f"# {s.name}\n{s.text}" for s in self.sources if s.text.strip())

    @property
    def weights(self) -> dict[str, int]:
        """How many characters each file brings, in the order they were read."""
        out: dict[str, int] = {}
        for s in self.sources:
            out[s.name] = out.get(s.name, 0) + len(s.text)
        return out

    def as_dict(self) -> dict:
        """What the page shows about the material: its files, its size and its pages."""
        return {
            "files": [{"name": s.name, "chars": len(s.text), "pages": s.pages}
                      for s in self.sources],
            "chars": self.chars,
            "pages": self.pages,
        }


def _as_list(paths: Paths) -> list[str]:
    if isinstance(paths, (str, Path)):
        return [str(paths)]
    return [str(p) for p in paths]


def read(paths: Paths, *, max_files: int = config.MAX_MATERIAL_FILES,
         max_chars: int = config.MAX_MATERIAL_CHARS,
         max_pages: int = config.MAX_SOURCE_PAGES,
         max_file_mb: float = config.MAX_FILE_MB) -> Material:
    """The given documents read into the material of one deck.

    Refuses rather than shortens: material over ``max_chars`` is an error naming the
    setting, because a deck built from the first half of a document is a deck nobody asked
    for. What is too long for the model window is dealt with in ``budget``, not here.
    """
    names = _as_list(paths)
    if not names:
        raise NoReadableText("No document was given.")
    if len(names) > max_files:
        raise LimitError(f"{len(names)} files were given, at most {max_files} go into one deck "
                         "(max_files, --max-material-files or OUTLINE2PPTX_MAX_MATERIAL_FILES).")
    sources = [read_file(name, max_pages=max_pages, max_file_mb=max_file_mb) for name in names]
    material = Material(sources=sources)
    if material.chars > max_chars:
        raise LimitError(
            f"The material has {material.chars} characters, at most {max_chars} are allowed "
            "(max_chars, --max-material-chars or OUTLINE2PPTX_MAX_MATERIAL_CHARS). Nothing is "
            "cut off behind your back, so raise the limit or give fewer documents.")
    log.info("Material: %d file(s), %d page(s), %d characters",
             len(sources), material.pages, material.chars)
    return material


def text_material(text: str, name: str = "material.txt") -> Material:
    """Material out of a text that has no document behind it."""
    return Material(sources=[from_text(name, text)])


def coerce(value: Union[Material, Paths], **options) -> Material:
    """Material as it stands, or the documents at the given paths read into it."""
    if isinstance(value, Material):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, Path)) and not value:
        raise NoReadableText("No document was given.")
    return read(value, **options)
