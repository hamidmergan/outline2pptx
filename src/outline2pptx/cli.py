import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__, api, config
from .errors import DeckError

LOOPBACK = ("127.0.0.1", "localhost", "::1")
UI_HINT = ('The web page needs extra packages: pip install '
           '"outline2pptx[ui] @ git+https://github.com/hamidmergan/outline2pptx.git"')
NO_LOGIN = "Warning: the page has no login. Anyone who can reach this port can use it."


def _model_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--base-url", help="URL of the OpenAI-compatible server, e.g. http://localhost:11434/v1")
    p.add_argument("--model", help="Name of the text model")
    p.add_argument("--api-key", help="API key, if the server requires one")
    p.add_argument("--image-base-url", help="Server of the image model. Default: --base-url")
    p.add_argument("--image-model", help="Model that draws the illustrations")
    p.add_argument("--image-api-key", help="API key of the image server. Default: --api-key")
    p.add_argument("--language", help='Language of the slide text, "en" or "de". Default: en')
    p.add_argument("--template", help="Template id or path to a .pptx or .potx. Default: clean")
    p.add_argument("--template-dir", help="Folder with your own templates, searched before the built-in ones")
    p.add_argument("--presenter", help="Name shown on the cover")
    p.add_argument("--instructions", help="What the deck should pay attention to, in plain language")
    p.add_argument("--style-text", help="The look every illustration shares. Default: the template's style")
    p.add_argument("--notice", help="A short note in the bottom right corner of every slide")
    p.add_argument("--notes", action="store_true", help="Write speaker notes")
    p.add_argument("--timeout", type=float, help="Seconds per request")


MODEL_KEYS = ("base_url", "model", "api_key", "image_base_url", "image_model", "image_api_key",
              "language", "template", "template_dir", "presenter", "instructions", "style_text",
              "notice", "timeout")


def _model_options(args: argparse.Namespace) -> dict:
    out = {k: getattr(args, k, None) for k in MODEL_KEYS}
    out["notes"] = True if getattr(args, "notes", False) else None
    return out


def _serve_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="outline2pptx serve", description="Start the local web page.")
    p.add_argument("--host", default="127.0.0.1", help="Default: 127.0.0.1 (this computer only)")
    p.add_argument("--port", type=int, default=8000)
    _model_args(p)
    return p


def _serve(argv: List[str]) -> int:
    args = _serve_parser().parse_args(argv)
    try:
        import uvicorn

        from .web.app import create_app
    except ImportError:
        _err(UI_HINT)
        return 2
    app = create_app(
        _model_options(args),
        # on loopback, only accept our own host names, so other web pages cannot reach it via DNS rebinding
        allowed_hosts=list(LOOPBACK) if args.host in LOOPBACK else None,
    )
    if args.host not in LOOPBACK:
        _err(NO_LOGIN)
    print(f"outline2pptx is listening on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="outline2pptx",
        description="Build a PowerPoint deck from a Markdown outline or from a topic. "
        "The model writes the slides, python-pptx builds the file.",
        epilog="Example: outline2pptx outline.md -o deck.pptx --template clean. "
        "Run 'outline2pptx serve' for the web page.",
    )
    p.add_argument("outline", nargs="?", help="Markdown file with the outline, or - for standard input")
    p.add_argument("-o", "--output", help="Where the .pptx goes. Default: next to the outline")
    p.add_argument("--topic", help="Plan the outline from a topic instead of reading a file")
    p.add_argument("--slides", type=int, help=f"How many slides to plan for a topic "
                   f"({config.MIN_SLIDES} to {config.MAX_SLIDES}). Default: the model decides")
    p.add_argument("--outline-only", action="store_true",
                   help="Print the planned outline as Markdown and build nothing")
    p.add_argument("--images", action="store_true", help="Draw the illustrations with the image model")
    p.add_argument("--preview", metavar="DIR", help="Also write one PNG per slide into this folder. "
                   "Needs LibreOffice")
    p.add_argument("--list-templates", action="store_true", help="Show the templates that can be used")
    _model_args(p)
    p.add_argument("--version", action="version", version=f"outline2pptx {__version__}")
    return p


def _err(message: str) -> None:
    print(message, file=sys.stderr)


def _read_outline(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    if not path.is_file():
        raise DeckError(f"No such outline file: {source}")
    return path.read_text("utf8")


def _default_output(args: argparse.Namespace) -> str:
    if args.output:
        return args.output
    if args.outline and args.outline != "-":
        return str(Path(args.outline).with_suffix(".pptx"))
    return "deck.pptx"


def _list_templates(args: argparse.Namespace) -> int:
    for entry in api.list_templates(args.template_dir):
        print(f"{entry['id']:<12} {entry['name']}")
        if entry["style_text"]:
            print(f"{'':<12} {entry['style_text']}")
    return 0


def _write_preview(deck, folder: str) -> None:
    target = Path(folder)
    target.mkdir(parents=True, exist_ok=True)
    for i, png in enumerate(deck.preview(), start=1):
        (target / f"slide-{i:02d}.png").write_bytes(png)
    _err(f"Preview written to {target}")


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "serve":
        return _serve(argv[1:])
    args = _parser().parse_args(argv)
    try:
        if args.list_templates:
            return _list_templates(args)
        if not args.outline and not args.topic:
            _err("Give an outline file or --topic. See outline2pptx --help.")
            return 2
        if args.outline and args.topic:
            _err("Give either an outline file or --topic, not both.")
            return 2
        if args.outline and args.slides is not None:
            _err("--slides plans an outline from --topic. An outline file sets its own slides.")
            return 2

        options = _model_options(args)
        if args.topic:
            outline_md = api.outline_from_topic(args.topic, slides=args.slides, **options)
        else:
            outline_md = _read_outline(args.outline)
        if args.outline_only:
            print(outline_md, end="")
            return 0

        def progress(stage: str, done: int, total: int) -> None:
            _err(f"[{stage}] {done}/{total}")

        deck = api.build(outline_md, _default_output(args), images=args.images or None,
                         progress=progress, **options)
        written = _default_output(args)
        _err(f"Wrote {written} with {deck.info['slides']} slides.")
        if args.preview:
            try:
                _write_preview(deck, args.preview)
            except DeckError as exc:
                # The deck is on disk and correct. Only the extra pictures are missing, so say
                # which half failed instead of letting the caller read this as a lost deck.
                _err(f"Error: {exc}")
                _err(f"The deck {written} was written, only the preview is missing.")
                return 2
        return 0
    except DeckError as exc:
        _err(f"Error: {exc}")
        return 2
    except KeyboardInterrupt:
        _err("Stopped.")
        return 130
