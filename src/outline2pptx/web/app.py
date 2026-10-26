"""The web UI of outline2pptx: a topic, an outline or your documents in the browser, a
PowerPoint file back.

One run at a time. The deck stays in memory until the next one replaces it, nothing is
written to disk.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import tempfile
import threading
from io import BytesIO
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from .. import __version__, api, budget as bd, library
from ..config import (
    DEFAULT_WINDOW_TOKENS, MAX_MATERIAL_CHARS, MAX_MATERIAL_FILES, MAX_OUTLINE_CHARS,
    MAX_TOPIC_CHARS, MAX_SLIDES, MIN_SLIDES, resolve,
)
from ..errors import ConfigError, DeckError
from ..source_reading import EXTENSIONS

STATIC = Path(__file__).parent / "static"
log = logging.getLogger(__name__)

LANGUAGES = ("de", "en")
# Mirrors the caps of the outline and the slide writer.
MAX_PRESENTER_CHARS = 80
MAX_STYLE_CHARS = 1000
MAX_INSTRUCTION_CHARS = 1000
# The template ids of uploaded slide masters start with this. The colon keeps them apart from
# every file name a template folder can hold.
UPLOADED = ":uploaded:"
# How many uploaded masters the server holds, the oldest one goes first.
MAX_UPLOADS = 5
MISSING_UPLOAD = "Upload the slide master again, the server no longer holds it."


class ModelFields(BaseModel):
    """What the fields on the page may override per run."""

    base_url: str = ""
    model: str = ""
    api_key: str = ""
    image_base_url: str = ""
    image_model: str = ""
    image_api_key: str = ""
    language: str = ""
    template: str = ""
    presenter: str = ""
    instructions: str = ""
    style_text: str = ""
    notice: str = ""
    # The outline already needs these, a deck without pictures is planned without picture layouts.
    notes: bool = False
    images: bool = False


class OutlineRequest(ModelFields):
    topic: str = ""
    slides: Optional[int] = None


class BuildRequest(ModelFields):
    outline: str = ""


class Job:
    """The one run the server holds, with what the browser needs to show it."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.state = "idle"  # idle, running, done or error
        self.step = ""
        self.done = 0
        self.total = 0
        self.error = ""
        self.slides: list[dict] = []
        self.info: dict = {}
        self.data: bytes = b""
        # Rendered once, the whole deck goes through LibreOffice in one call.
        self.pages: list[bytes] = []

    def as_dict(self) -> dict:
        return {"state": self.state, "step": self.step, "done": self.done, "total": self.total,
                "error": self.error, "slides": self.slides, "info": self.info}


def _hostname(host: str) -> str:
    if host.startswith("["):
        return host[1:host.find("]")].lower()
    return host.rsplit(":", 1)[0].lower() if host.count(":") == 1 else host.lower()


def _clean(value: str, cap: int) -> Optional[str]:
    text = (value or "").strip()[:cap]
    return text or None


def _safe_name(name: str) -> str:
    """The plain file name of an upload, without any path the browser sent along."""
    return Path(name.replace("\\", "/")).name


def _window_chars(settings) -> int:
    """How much material one call may carry, 0 when the window is set too small for a deck."""
    try:
        return bd.window_chars(settings.context_window if settings else DEFAULT_WINDOW_TOKENS)
    except ConfigError:
        return 0


def _model_fields(raw: str) -> ModelFields:
    """The settings of one upload, sent as JSON beside the files."""
    try:
        return ModelFields.model_validate_json(raw or "{}")
    except ValidationError as exc:
        raise HTTPException(400, "The settings of the request cannot be read.") from exc


def create_app(defaults: Optional[dict] = None,
               allowed_hosts: Optional[Sequence[str]] = None) -> FastAPI:
    """The page and its JSON API. ``allowed_hosts`` limits the Host header."""
    base = {k: v for k, v in (defaults or {}).items() if v not in (None, "")}
    job = Job()
    lock = threading.Lock()
    # An outline is planned inside the request, so it has no job state to hold. This flag is
    # all it needs: one outline at a time, and no build while one is being planned.
    planning = threading.Event()
    # The uploaded slide masters by id, as pptx bytes. Every upload has its own id, so a run
    # never picks up a master someone else uploaded in between. They live in memory like the
    # deck and are written to a temporary folder only while a request or a run needs them.
    uploads: dict[str, dict] = {}

    app = FastAPI(title="outline2pptx", version=__version__)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    hosts = {h.lower() for h in allowed_hosts} if allowed_hosts is not None else None

    def options(request: ModelFields, **extra) -> dict:
        """Environment and command line first, the fields on the page over them."""
        out = dict(base)
        out.update({k: v for k, v in {
            "base_url": _clean(request.base_url, 500),
            "model": _clean(request.model, 200),
            "api_key": _clean(request.api_key, 500),
            "image_base_url": _clean(request.image_base_url, 500),
            "image_model": _clean(request.image_model, 200),
            "image_api_key": _clean(request.image_api_key, 500),
            "language": _clean(request.language, 10),
            "template": _clean(request.template, 200),
            "presenter": _clean(request.presenter, MAX_PRESENTER_CHARS),
            "instructions": _clean(request.instructions, MAX_INSTRUCTION_CHARS),
            "style_text": _clean(request.style_text, MAX_STYLE_CHARS),
            "notice": _clean(request.notice, 200),
        }.items() if v is not None})
        out.update(notes=request.notes, images=request.images)
        out.update(extra)
        return out

    @contextlib.contextmanager
    def with_template(opts: dict):
        """The options with the uploaded master as a file, for as long as the block runs."""
        if not str(opts.get("template", "")).startswith(UPLOADED):
            yield opts
            return
        with lock:
            master = uploads.get(opts["template"])
        if not master:
            raise DeckError(MISSING_UPLOAD)
        with tempfile.TemporaryDirectory(prefix="outline2pptx-") as folder:
            path = Path(folder) / f"{master['stem']}.pptx"
            path.write_bytes(master["data"])
            yield {**opts, "template": str(path)}

    @app.middleware("http")
    async def guard(request: Request, call_next):
        host = request.headers.get("host", "")
        if hosts is not None and _hostname(host) not in hosts:
            return PlainTextResponse("Unknown host", status_code=400)
        origin = request.headers.get("origin")
        own = {host.lower(), request.headers.get("x-forwarded-host", "").lower()}
        if origin is not None and urlsplit(origin).netloc.lower() not in own:
            return PlainTextResponse("Cross-origin requests are not allowed", status_code=403)
        response = await call_next(request)
        # The page and its scripts are checked again on every load, so an update is never
        # met by a script the browser kept from the version before.
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/", response_class=HTMLResponse)
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/info")
    def info():
        from ..render import available

        try:
            settings = resolve(**base)
        except ConfigError:
            settings = None
        return {
            "version": __version__,
            "templates": api.list_templates(base.get("template_dir")),
            "languages": list(LANGUAGES),
            "min_slides": MIN_SLIDES,
            "max_slides": MAX_SLIDES,
            "max_topic_chars": MAX_TOPIC_CHARS,
            "max_outline_chars": MAX_OUTLINE_CHARS,
            "extensions": list(EXTENSIONS),
            "max_material_files": settings.max_material_files if settings else MAX_MATERIAL_FILES,
            "max_material_chars": settings.max_material_chars if settings else MAX_MATERIAL_CHARS,
            # Material longer than this is planned through its topics instead of in full.
            "window_chars": _window_chars(settings),
            "max_presenter_chars": MAX_PRESENTER_CHARS,
            "max_style_chars": MAX_STYLE_CHARS,
            "max_instruction_chars": MAX_INSTRUCTION_CHARS,
            # What the environment already decided, so the fields start where it points.
            "model": settings.model if settings else "",
            "image_model": settings.image_model if settings else "",
            "language": settings.language if settings else LANGUAGES[1],
            "template": settings.template if settings else "",
            "presenter": settings.presenter if settings else "",
            "instructions": settings.instructions if settings else "",
            "notes": bool(settings.notes) if settings else False,
            "images": bool(settings.images) if settings else False,
            "preview": available(),
            # The masters uploaded earlier are still held, so a reload of the page keeps offering them.
            "uploads": [{"id": key, "name": item["name"]} for key, item in uploads.items()],
            # Without a model in the environment the page asks for one.
            "configured": settings is not None,
        }

    @app.post("/api/outline")
    def outline(request: OutlineRequest):
        topic = request.topic.strip()[:MAX_TOPIC_CHARS]
        if not topic:
            raise HTTPException(400, "Enter a topic first.")
        with lock:
            if job.state == "running" or planning.is_set():
                raise HTTPException(409, "A presentation is being created right now.")
            planning.set()
        try:
            with with_template(options(request)) as opts:
                text = api.outline_from_topic(topic, slides=request.slides, **opts)
        except DeckError as exc:
            raise HTTPException(400, str(exc)) from None
        finally:
            with lock:
                planning.clear()
        return {"outline": text}

    @app.post("/api/material")
    def material(files: list[UploadFile] = File(...), fields: str = Form("{}"),
                 slides: Optional[int] = Form(None)):
        """The uploaded documents read and planned into an outline, in one request."""
        import shutil
        import tempfile

        request = _model_fields(fields)
        if not files:
            raise HTTPException(400, "Choose at least one document.")
        with lock:
            if job.state == "running" or planning.is_set():
                raise HTTPException(409, "A presentation is being created right now.")
            planning.set()
        try:
            with tempfile.TemporaryDirectory(prefix="outline2pptx-") as folder:
                paths = []
                for item in files:
                    name = _safe_name(item.filename or "")
                    if not name:
                        raise HTTPException(400, "A file without a name cannot be read.")
                    target = Path(folder) / name
                    with target.open("wb") as handle:
                        shutil.copyfileobj(item.file, handle)
                    paths.append(target)
                # Read first, so the answer can say how large the material turned out to be
                # even when the planning call then fails.
                found = api.material_for(paths, **options(request))
                with with_template(options(request)) as opts:
                    text = api.outline_from_material(found, slides=slides, **opts)
                limit = _window_chars(resolve(**options(request)))
        except DeckError as exc:
            raise HTTPException(400, str(exc)) from None
        finally:
            with lock:
                planning.clear()
        # What was read and how large it is, so the page can say why the budget stepped in.
        return {"outline": text, "material": found.as_dict(),
                "shortened": bool(limit) and found.chars > limit, "window_chars": limit}

    def run(request: BuildRequest, text: str) -> None:
        def progress(step: str, done: int, total: int) -> None:
            with lock:
                job.step, job.done, job.total = step, done, total

        try:
            with with_template(options(request)) as opts:
                deck = api.build(text, progress=progress, **opts)
        except DeckError as exc:
            with lock:
                job.state, job.error = "error", str(exc)
            return
        except Exception as exc:  # noqa: BLE001 - the browser must see why the run stopped
            log.warning("The run failed: %s", exc)
            with lock:
                job.state, job.error = "error", str(exc)
            return
        with lock:
            job.data = deck.data
            job.info = deck.info
            job.slides = [{"number": i, "role": s.role, "title": s.title,
                           "kind": s.body.kind if s.body is not None else ""}
                          for i, s in enumerate(deck.slides, start=1)]
            job.state, job.step, job.done, job.total = "done", "", len(deck.slides), len(deck.slides)

    @app.post("/api/template")
    def upload_template(file: UploadFile = File(...)):
        """A slide master of your own, checked and kept until the next one replaces it."""
        name = _safe_name(file.filename or "")
        suffix = Path(name).suffix.lower()
        data = file.file.read(library.MAX_BYTES + 1)
        try:
            data, analysis = library.check(data, suffix)
        except DeckError as exc:
            raise HTTPException(400, str(exc)) from None
        stem = Path(name).stem or "template"
        key = UPLOADED + hashlib.sha256(data).hexdigest()[:16]
        with lock:
            uploads.pop(key, None)
            uploads[key] = {"name": name, "stem": stem, "data": data}
            while len(uploads) > MAX_UPLOADS:
                uploads.pop(next(iter(uploads)))
        used = [layout for layout in analysis.layouts if layout.role]
        return {"id": key, "name": name, "layouts": len(analysis.layouts),
                "used": len(used), "skipped": list(analysis.skipped),
                "roles": {role: len(found) for role, found in sorted(analysis.roles.items())}}

    @app.post("/api/build")
    def build(request: BuildRequest):
        text = request.outline.strip()[:MAX_OUTLINE_CHARS]
        if not text:
            raise HTTPException(400, "The outline is empty.")
        with lock:
            if job.state == "running" or planning.is_set():
                raise HTTPException(409, "A presentation is being created right now.")
            try:
                resolve(**options(request))
            except ConfigError as exc:
                raise HTTPException(400, str(exc)) from None
            if request.template.startswith(UPLOADED) and request.template not in uploads:
                raise HTTPException(400, MISSING_UPLOAD)
            job.reset()
            job.state, job.step = "running", "slides"
        threading.Thread(target=run, args=(request, text), daemon=True).start()
        return job.as_dict()

    @app.get("/api/status")
    def status():
        with lock:
            return job.as_dict()

    @app.get("/api/download")
    def download():
        with lock:
            data = job.data
        if not data:
            raise HTTPException(404, "There is no presentation to download yet.")
        return StreamingResponse(
            BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": 'attachment; filename="deck.pptx"'})

    @app.get("/api/preview/{number}")
    def preview(number: int):
        from .. import preview as pv
        from ..render import available

        with lock:
            data, pages = job.data, job.pages
        if not data:
            raise HTTPException(404, "There is no presentation yet.")
        if not available():
            raise HTTPException(409, "LibreOffice is not installed, so there is no preview.")
        if not pages:
            try:
                pages = pv.render(data)
            except DeckError as exc:
                raise HTTPException(409, str(exc)) from None
            with lock:
                if job.data == data:
                    job.pages = pages
        if number < 1 or number > len(pages):
            raise HTTPException(404, "This slide does not exist.")
        return StreamingResponse(BytesIO(pages[number - 1]), media_type="image/png")

    return app


def serve(host: str = "127.0.0.1", port: int = 8000, defaults: Optional[dict] = None) -> None:
    """Starts the web UI. Settings missing here are read from the environment per run."""
    import uvicorn

    # The Host header is checked without its port, so only names belong in here.
    hosts = None if host == "0.0.0.0" else {_hostname(host), "localhost", "127.0.0.1"}
    app = create_app(defaults, allowed_hosts=hosts)
    print(f"outline2pptx is listening on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")
