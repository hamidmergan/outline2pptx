"""The templates: the ones that ship with the package, and the ones in a folder of your own."""

from __future__ import annotations

import functools
import json
import zipfile
from io import BytesIO
from pathlib import Path

from . import template
from .errors import TemplateError
from .template import Analysis

BUILTIN = Path(__file__).parent / "templates"
ALLOWED = (".pptx", ".potx")
MAX_MB = 30
MAX_BYTES = MAX_MB * 1024 * 1024


class TemplateUnusable(TemplateError):
    """The file is refused, the message names the reason."""


def _meta_for(path: Path) -> dict:
    """Name and picture style beside the file, defaults when there is no json."""
    side = path.with_suffix(".json")
    if side.exists():
        try:
            data = json.loads(side.read_text("utf8"))
        except (OSError, ValueError):
            data = {}
    else:
        data = {}
    return {"name": str(data.get("name") or path.stem.replace("_", " ").title()),
            "style_text": str(data.get("style_text") or "")}


def folders(template_dir: str | Path | None = None) -> list[Path]:
    """Where templates are looked for: your own folder first, the packaged one after it."""
    out = []
    if template_dir:
        out.append(Path(template_dir).expanduser())
    out.append(BUILTIN)
    return out


def available(template_dir: str | Path | None = None) -> list[dict]:
    """Every template that can be used, by id, with its name, style and file."""
    seen: dict[str, dict] = {}
    for folder in folders(template_dir):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*")):
            if path.suffix.lower() not in ALLOWED or path.stem in seen:
                continue
            seen[path.stem] = {"id": path.stem, "path": str(path), **_meta_for(path)}
    return list(seen.values())


def find(name: str, template_dir: str | Path | None = None) -> Path:
    """The file of a template, named by its id or given as a path."""
    direct = Path(name).expanduser()
    if direct.suffix.lower() in ALLOWED and direct.is_file():
        return direct
    for folder in folders(template_dir):
        for suffix in ALLOWED:
            path = folder / f"{name}{suffix}"
            if path.is_file():
                return path
    known = ", ".join(t["id"] for t in available(template_dir)) or "none"
    raise TemplateUnusable(f"Unknown template {name!r}. Available: {known}.")


def has_macros(data: bytes) -> bool:
    with zipfile.ZipFile(BytesIO(data)) as z:
        return any(n.lower().endswith("vbaproject.bin") for n in z.namelist())


def as_pptx(data: bytes) -> bytes:
    """A potx is a pptx with another content type, the rest is the same."""
    out = BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for n in src.namelist():
            b = src.read(n)
            if n == "[Content_Types].xml":
                b = b.replace(b"presentationml.template.main+xml",
                              b"presentationml.presentation.main+xml")
            dst.writestr(n, b)
    return out.getvalue()


def check(data: bytes, ext: str) -> tuple[bytes, Analysis]:
    """The file as pptx bytes plus its analysis, or the reason it cannot be used."""
    if ext.lower() not in ALLOWED:
        raise TemplateUnusable("A template is a .pptx or a .potx file.")
    if len(data) > MAX_BYTES:
        raise TemplateUnusable(f"The template is larger than {MAX_MB} MB.")
    try:
        if has_macros(data):
            raise TemplateUnusable("The template holds macros, those are not accepted.")
        if ext.lower() == ".potx":
            data = as_pptx(data)
        analysis = template.analyse(data)
    except TemplateUnusable:
        raise
    except Exception as exc:
        raise TemplateUnusable(f"The template cannot be read: {exc}") from exc
    if not analysis.layouts or not any(layout.role for layout in analysis.layouts):
        raise TemplateUnusable("The template has no layout the builder can use.")
    return data, analysis


def load(name: str, template_dir: str | Path | None = None) -> tuple[bytes, Analysis, dict]:
    """The bytes, the analysis and the metadata of one template."""
    path = find(name, template_dir)
    data, analysis = check(path.read_bytes(), path.suffix)
    return data, analysis, {"id": path.stem, **_meta_for(path)}


@functools.lru_cache(maxsize=4)
def builtin(name: str) -> tuple[bytes, Analysis, dict]:
    """A packaged template, cached because it never changes while the process runs."""
    return load(name)
