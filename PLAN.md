# PLAN

Build a slide deck as PPTX from a Markdown outline or from a topic. The model plans the
outline and writes the slide content (bullets, tables, charts, cards, bars, steps, figures,
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

## Open

- The example picture in the README is rendered in the container, LibreOffice is not needed
  on the host
- The page builds one deck at a time and keeps it in memory, a second request waits, and a
  running build cannot be stopped
