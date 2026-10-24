# outline2pptx

A Python tool that builds a PowerPoint deck from your own documents, from a Markdown outline or from a plain topic. The model plans the outline and writes the slide content. The file itself is built with python-pptx from a template, so the result is a normal editable `.pptx`.

![One slide of a deck built with the clean template](https://raw.githubusercontent.com/hamidmergan/outline2pptx/main/docs/example.png)

outline2pptx currently writes:

- Bullet slides, two column slides and section dividers
- Tables, bar charts and line charts
- Cards with icons, bar comparisons, key figures, process steps and pyramid levels
- One highlighted key statement
- Illustrations from an image model, and a deck without one simply has no picture boxes
- Speaker notes, on request

It reads PDF, DOCX, PPTX, Markdown and plain text. A PDF is read by its layout, so the running header and the footer of a handout do not turn up as bullet points on a slide.

## Prerequisites

- Python 3.10 or newer
- A server with an OpenAI-compatible API and a **text model** (for example Ollama, vLLM, LM Studio, a research server or a cloud provider). It is needed for `--topic`, for `--material` and for writing the slides.
- An **image model** on the same kind of API, only needed for `--images`. Without one the deck is built without pictures, and a slide that asked for one keeps its text alone.
- An API key is optional. Many self-hosted servers do not need one.
- LibreOffice, only needed for `--preview`. Nothing else uses it.

If you run your own model, your documents, your topic and your slide text stay on your own network. Nothing leaves your machine or data center.

## Installation

outline2pptx is installed from GitHub:

```bash
pip install git+https://github.com/hamidmergan/outline2pptx.git
```

For the web page, install the extra:

```bash
pip install "outline2pptx[ui] @ git+https://github.com/hamidmergan/outline2pptx.git"
```

Alternatively, you can install it from a local copy (`pip install ".[ui]"` for the web page):

```bash
git clone https://github.com/hamidmergan/outline2pptx.git
cd outline2pptx
pip install .
```

## Usage

### Command-Line

Build a deck from an outline file:

```bash
outline2pptx outline.md -o deck.pptx --base-url http://localhost:11434/v1 --model your-model
```

Without `-o`, the deck is written next to the outline as `outline.pptx`. Use `-` to read the outline from standard input.

Build a deck from your own documents:

```bash
outline2pptx --material handout.pdf notes.docx -o deck.pptx \
  --base-url http://localhost:11434/v1 --model your-model
```

The documents are read first, and their size and page count are printed to stderr before the first call is paid for. The amount of material decides how long the deck becomes, unless `--slides` says otherwise. Material longer than one call can carry is boiled down to the topics it covers and planned from those, so nothing is cut off at the end where the last document stands. Nothing is ever shortened silently: material over `--max-material-chars` is refused with an error naming the limit.

Let the model plan the outline from a topic instead:

```bash
outline2pptx --topic "How honeybees pollinate flowers" --slides 12 -o deck.pptx \
  --base-url http://localhost:11434/v1 --model your-model
```

Print the planned outline and build nothing, so you can edit it first:

```bash
outline2pptx --material handout.pdf --outline-only > outline.md
```

Pick a template and draw the illustrations:

```bash
outline2pptx outline.md --template forest --images --image-model your-image-model
```

Show the templates that can be used:

```bash
outline2pptx --list-templates
```

Write one PNG per slide next to the deck, which needs LibreOffice:

```bash
outline2pptx outline.md --preview preview/
```

Progress and errors go to stderr. The exit code is 2 if the deck could not be built.

### The outline format

An outline is plain Markdown. The first level one heading is the deck title, the line under it the subtitle. Every further heading is one slide, and the lines under a heading are its gist, one sentence saying what the slide shows.

```markdown
# Bees and Flowers

How pollination really works

## What bees do all day

## Pollination step by step

Pollen travels from one flower to the next.

## [two_columns] Winners and losers

Who gains and who pays.

## [text_with_image] A hive from the inside

What the comb looks like up close.
```

A heading with no text under it becomes a section divider. A heading with text becomes a text slide. Put a role in square brackets to choose one yourself:

| Role | What the slide looks like |
| --- | --- |
| `section` | A divider with only a heading |
| `text` | A heading with bullets, or a table, chart, cards, bars or a key figure |
| `two_columns` | A heading with two or more columns, each with its own subheading |
| `text_with_image` | A heading, bullets and one or more illustrations |

The cover and the closing slide are added from the title and the last heading. A deck has between 3 and 30 slides. An outline file outside that range is refused with an error naming the limit, so split a longer plan into several decks. Nothing in an outline file is ever dropped or renamed, and every heading needs a title of its own, a role tag alone is not enough.

### Documents

`--material` takes one or more files: `.pdf`, `.docx`, `.pptx`, `.md` and `.txt`. At most ten of them, at most 200 pages and 500 MB each, and at most 500,000 characters in sum. A PDF without a text layer is refused, nothing is recognised from a picture.

Each file keeps its name in the material, so the model can tell two documents apart. Over several files every one of them gets slides of its own, shared out by how much it brings, and the slide before the closing one compares the documents along the same points.

### Python API

```python
from outline2pptx import build

deck = build(
    open("outline.md").read(),
    "deck.pptx",
    template="clean",
    base_url="http://localhost:11434/v1",
    model="your-model",
)
print(deck.info["slides"], "slides")
```

Build a deck from documents, with the outline in between so you can edit it:

```python
from outline2pptx import outline_from_material, read_material, build

material = read_material(["handout.pdf", "notes.docx"])
print(material.chars, "characters from", material.names)

text = outline_from_material(
    material,
    base_url="http://localhost:11434/v1",
    model="your-model",
)
deck = build(text, base_url="http://localhost:11434/v1", model="your-model")
deck.save("deck.pptx")
```

`outline_from_material` also takes a path or a list of paths straight away, and `read_material` only exists so a caller can show what was read before any model call. `text_material("...")` wraps a text that has no document behind it.

Plan the outline first and edit it before building:

```python
from outline2pptx import outline_from_topic, build

text = outline_from_topic(
    "How honeybees pollinate flowers",
    slides=12,
    base_url="http://localhost:11434/v1",
    model="your-model",
)
deck = build(text, base_url="http://localhost:11434/v1", model="your-model")
deck.save("deck.pptx")
```

`build` returns a `Deck` with the file as `deck.data`, the parsed outline as `deck.outline`, the slides as `deck.slides` and what it was made with as `deck.info`. `deck.preview()` renders one PNG per slide through LibreOffice. `list_templates()` returns the templates that can be used.

Pass `progress=lambda stage, done, total: ...` to follow a long run. The stages are `slides`, `pictures` and `done`.

### Templates

Three templates ship with the package: `clean`, `forest` and `warm`. A template is a `.pptx` or `.potx` whose layouts carry the roles above, with an optional `<name>.json` beside it:

```json
{
  "name": "Clean",
  "style_text": "A clear, modern vector illustration with flat shapes and a calm blue palette."
}
```

Point `--template-dir` at a folder of your own. It is searched before the packaged templates, so a file of the same name wins. `--template` also takes a path to a single file. Templates with macros and files over 30 MB are refused.

### Settings

Order: argument, then environment variable, then default.

| Argument / flag | Environment variable | Default |
| --- | --- | --- |
| `base_url` / `--base-url` | `OUTLINE2PPTX_BASE_URL` | none, required |
| `model` / `--model` | `OUTLINE2PPTX_MODEL` | none, required |
| `api_key` / `--api-key` | `OUTLINE2PPTX_API_KEY` (then `OPENAI_API_KEY`) | optional |
| `image_base_url` / `--image-base-url` | `OUTLINE2PPTX_IMAGE_BASE_URL` | the chat `base_url` |
| `image_model` / `--image-model` | `OUTLINE2PPTX_IMAGE_MODEL` | none, required for `--images` |
| `image_api_key` / `--image-api-key` | `OUTLINE2PPTX_IMAGE_API_KEY` | the chat `api_key` |
| `language` / `--language` | `OUTLINE2PPTX_LANGUAGE` | `en` |
| `template` / `--template` | `OUTLINE2PPTX_TEMPLATE` | `clean` |
| `template_dir` / `--template-dir` | `OUTLINE2PPTX_TEMPLATE_DIR` | none |
| `slides` / `--slides` | `OUTLINE2PPTX_SLIDES` | 3 to 30, for a topic or for material: the model decides over a topic, the amount of material decides over documents |
| `context_window` / `--context-window` | `OUTLINE2PPTX_CONTEXT_WINDOW` | 131072 tokens |
| `max_material_chars` / `--max-material-chars` | `OUTLINE2PPTX_MAX_MATERIAL_CHARS` | 500000 |
| `max_material_files` / `--max-material-files` | `OUTLINE2PPTX_MAX_MATERIAL_FILES` | 10 |
| `max_pages` / `--max-pages` | `OUTLINE2PPTX_MAX_SOURCE_PAGES` | 200 per document |
| `max_file_mb` / `--max-file-mb` | `OUTLINE2PPTX_MAX_FILE_MB` | 500 per document |
| `images` / `--images` | `OUTLINE2PPTX_IMAGES` | off |
| `notes` / `--notes` | `OUTLINE2PPTX_NOTES` | off |
| `presenter` / `--presenter` | `OUTLINE2PPTX_PRESENTER` | empty |
| `instructions` / `--instructions` | `OUTLINE2PPTX_INSTRUCTIONS` | empty |
| `style_text` / `--style-text` | `OUTLINE2PPTX_STYLE_TEXT` | the template's style |
| `notice` / `--notice` | `OUTLINE2PPTX_NOTICE` | empty |
| `batch` | `OUTLINE2PPTX_BATCH` | 5 slides per call |
| `write_parallelism` | `OUTLINE2PPTX_WRITE_PARALLELISM` | 3 |
| `image_parallelism` | `OUTLINE2PPTX_IMAGE_PARALLELISM` | 4 |
| `timeout` / `--timeout` | `OUTLINE2PPTX_TIMEOUT` | 180 seconds |
| `image_timeout` | `OUTLINE2PPTX_IMAGE_TIMEOUT` | 300 seconds |
| `max_retries` | `OUTLINE2PPTX_MAX_RETRIES` | 2 |

If `base_url` or `model` is missing, the error names the flag and the variable to set. The same holds for `--images` without an image model.

## Web UI

Start a local page with the same options as the CLI:

```bash
outline2pptx serve
```

It listens on `http://127.0.0.1:8000`. The page has three steps: content, outline and done. The first step offers all three ways in and says which one is in use: a topic, your own documents or your own Markdown. Uploaded documents are read on the spot and the page shows how much text came out of them, and whether that was more than one call can carry. Edit the outline, pick a template and a language, then build the deck and download it. Where LibreOffice is installed, every slide is shown as a picture. Server and model can come from the environment or from the fields on the page, and nothing is stored on disk.

The page is available in English and German.

The page has no login. `--host 0.0.0.0` opens it to the network, and then anyone who can reach the port can use it.

## Docker

```bash
docker compose up
```

The page is then on `http://localhost:8000`. The image carries LibreOffice, so the slide preview works inside the container. Set the model in `docker-compose.yml` or in the environment:

```bash
OUTLINE2PPTX_BASE_URL=http://host.docker.internal:11434/v1 \
OUTLINE2PPTX_MODEL=your-model docker compose up
```

The CLI works in the container too:

```bash
docker compose run --rm outline2pptx outline2pptx outline.md -o /data/deck.pptx
```

Documents are read from the same folder:

```bash
docker compose run --rm outline2pptx outline2pptx --material /data/handout.pdf -o /data/deck.pptx
```

## Limitations

Quality depends on the chosen model. A small model writes thin bullets, picks the wrong body kind and sometimes ignores the language. Slides that come back too thin are asked for once more, but the result is still worth reading before you present it.

Charts and tables are built from what the model returns, so the numbers are only as good as its source. Check them.

The documents shape the outline, and every slide is written from the title and the gist its entry carries. A gist that says too little about the material leaves the slide text to the model, so read the outline before the slides are written.

A scanned PDF without a text layer carries no text for the deck. There is no text recognition.

A template only works if its layouts can be matched to the roles. A deck built from a very unusual template may fall back to plain text slides.

## Running Tests

```bash
pip install -e ".[test]"
pytest
```

The tests run against a local fake server and need no real model. The preview test is skipped when LibreOffice is not installed.

## License

MIT
