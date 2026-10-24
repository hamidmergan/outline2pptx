class DeckError(Exception):
    """Base class of all errors in this package."""


class ConfigError(DeckError):
    """A setting is missing or a value is invalid."""


class TemplateError(DeckError):
    """The template cannot be read or holds no usable layouts."""


class ModelError(DeckError):
    """The model server did not answer, or the answer was unusable."""


class OutlineError(DeckError):
    """A hand-written outline cannot be used as it stands."""


class LimitError(DeckError):
    """A limit was exceeded."""


class UnsupportedFileError(DeckError):
    """The file type is not supported or the file cannot be read."""


class NoReadableText(UnsupportedFileError):
    """The file carries no text at all, a scan without a text layer for instance."""


class PreviewError(DeckError):
    """The slide preview could not be rendered."""
