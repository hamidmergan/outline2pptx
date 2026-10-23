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
- [ ] 8 Web UI and Docker

## Open

- The example picture in the README is rendered in the container, LibreOffice is not needed on the host
