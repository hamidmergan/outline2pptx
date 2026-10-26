# PLAN

Build a slide deck as PPTX from your own documents, from a Markdown outline or from a topic.
The model plans the outline and writes the slide content (bullets, tables, charts, cards, bars, steps, figures,
levels, symbols, highlight, images). The deck is built from a template file with python-pptx:
layouts by role, grid, colours from the template, bullet lists, shapes and icons. Images come
from an optional image model, a placeholder stands in without one. An optional PNG preview per
slide is rendered with LibreOffice.

## Decisions

- Library first, thin CLI on top, web UI with `outline2pptx serve`
- OpenAI compatible interface only: `base_url`, `model`, optional `api_key` (placeholder `none`)
- Image model with its own variables, falling back to the chat values
- Templates are files: `src/outline2pptx/templates/<name>.pptx` plus `<name>.json`, or a user folder via `--template-dir`
- LibreOffice is only needed for `--preview`, tests skip the preview when it is missing
- Documents are read in the package itself: PDF, DOCX, PPTX, Markdown and plain text. A PDF
  goes through its layout, so a running header and a footer are counted out over the whole
  document instead of guessed at per page
- The material shapes the outline. `outline_from_topic` is untouched and
  `outline_from_material` stands beside it

## Progress

- [x] 0 Scaffold
- [x] 1 Data model and outline
- [x] 2 Building the slides
- [x] 3 Images and preview
- [x] 4 API and CLI
- [x] 5 Tests with fake server
- [x] 6 README, CHANGELOG, smoke test
- [x] 7 English sweep, acceptance greps
- [x] 8 Web UI and Docker
- [x] 9 Review fixes
- [x] 10 Documents as input: reader, material aware outline, size budget, CLI, page
- [x] 11 Variety: 51 layouts in the packaged templates, picture layouts only with pictures,
  a rule that spreads the drawn elements, new elements (timeline, cycle, comparison, matrix,
  quote, checklist, definitions, mistakes, scale, venn, tree, example)

## The material path

### The shape of the API

`outline_from_material(material, *, slides=None, ...)` takes a path, a list of paths or a
`Material` that was read already, and returns the same Markdown `outline_from_topic` returns,
so `build` is reached the same way from all three inputs and nothing about the old API moved.

Paths only, never a string of text: a string that is sometimes a file name and sometimes the
text itself is a guess waiting to go wrong. A text with no document behind it goes through
`text_material("...")` and becomes the same record a file becomes.

`read_material(paths)` exists so a caller can show what was read before the first model call
is paid for: `Material` carries the sources, their names, their pages and `chars`. The command
line prints that line to stderr and the page shows it in the documents tab.

### The budget

One outline call carries the whole material, so the window of the chat model is the limit that
decides. `context_window` (default 131072 tokens) less the room the task and the answer take
is turned into characters. Material that fits goes in as it is and costs nothing extra.

Material that does not fit is mapped: it is cut into window sized pieces at block boundaries,
every piece is boiled down to the topics it covers in one call, and the deck is planned from
those topics. That way the last document still has its say instead of being cut off by the
server. The topics are paid for once.

Two refusals, both naming what to do, because material is never shortened behind the author's
back: a window below 16384 tokens carries no useful share of the material, and material over
`max_material_chars` (default 500000) is too much for one deck. A mapping that comes back
without a single topic is an error as well, not a deck planned on nothing.

## Known properties

Things that look like defects at first reading and are kept on purpose.

- The closing and the divider layout are found by name in English and in German, so a
  template whose layout is called "Abschluss", "Danke" or "Abschnitt" is read correctly.
  "end" carries its word boundaries, so Agenda, Appendix, Calendar, Trends and Legend stay
  ordinary content layouts.
- `tools/make_templates.py` writes the whole box of every placeholder it touches, in the
  master as well. A placeholder that inherits only part of its geometry comes out at the top
  edge of the slide with no height, which is why the two attribute write is never used.
- A `--preview` that cannot run after the deck was written exits with 2, because the run did
  not do everything it was asked. The deck stays on disk and the message says which half
  failed.
- `_BRACKET` and `_REFERENCE` in `diagrams.py` strip the bracketed source marks a German
  academic text uses. They cost nothing on text that has none.
- A slide whose picture was never drawn keeps its text in the width the layout gives it. The
  text box is not widened, the same way the layout renders a slide with a picture.

## Deliberate deviations from the source

- One notes switch, not two. Notes that were written always reach the file.
- A template that cannot be read raises instead of quietly falling back to the default one,
  so nobody presents a deck in the wrong master without knowing.
- `IMAGE_MODEL` has no fallback to `MODEL`. A chat model cannot draw, so the fallback the
  provider rules describe would only produce a confusing error from the server.
- The page has no per slide editing, no regenerate chat and no template upload. All three sat
  on a job and storage layer that is not carried. The outline can be edited before the slides
  are written, which shapes the deck in one round trip instead of one per slide.
- The template picker shows no cover thumbnail. Rendering one cover per template needs
  LibreOffice, which is optional here and only required for the preview, and three renders
  would hold up the first paint of the page.
- The page has no cancel. One run at a time, and a long run has to be waited out.
- The language fallback is English, not German.
- The material shapes the outline, the slides are written from the title and the gist of
  their entry. The deck is planned over the whole material in one call, and the slide calls
  then run in parallel over a plan that already says what each slide shows. Carrying the
  material into every slide call as well would put the whole document into every one of them,
  which is the mistake the budget exists to prevent.
- No passage numbering and no refs. The source numbered every passage of the material and had
  the model name the numbers a slide rests on, which is how a citation can be traced back.
  That machinery is a tool of its own and is not carried, so a deck here names no sources.
- An outline over several files is asked for once and taken as it comes. The source measured
  the answer against the share of every file and asked again when a document was buried, which
  it could only do because every entry named its passages.

## Open

- The example picture in the README is rendered in the container, LibreOffice is not needed
  on the host
- A scanned PDF without a text layer is refused. There is no text recognition
- The page builds one deck at a time and keeps it in memory, a second request waits, and a
  running build cannot be stopped
