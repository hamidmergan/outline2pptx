# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-23

### Added

- Build a PowerPoint deck from a Markdown outline, with python-pptx and a template file
- Plan an outline from a topic with an OpenAI-compatible text model, as Markdown you can edit
- Slide bodies: bullets, two or more columns, tables, bar and line charts, cards with icons,
  bar comparisons, key figures, process steps, pyramid levels, a highlighted statement and
  full slide images
- Three templates that ship with the package: `clean`, `forest` and `warm`, plus your own
  folder through `--template-dir` or a path to a single `.pptx` or `.potx`
- Layouts chosen by role, a grid that keeps the spacing, colours read from the template and
  an icon set that is matched by name
- Columns that do not fit are split over a second slide, speaker notes along with them
- Illustrations from an optional image model, and a picture it refuses becomes a coloured block
- Speaker notes, a presenter name on the cover and a short notice on every slide
- One PNG per slide through LibreOffice, from the CLI with `--preview` or from `Deck.preview()`
- Command line interface with `--topic`, `--outline-only`, `--images`, `--preview`,
  `--list-templates` and the model flags
- Local web page through `outline2pptx serve`, with the same options as the CLI
- Dockerfile and docker-compose setup, LibreOffice included so the preview works

[0.1.0]: https://github.com/hamidmergan/outline2pptx/releases/tag/v0.1.0
