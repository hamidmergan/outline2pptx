# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Build a deck from your own documents: PDF, DOCX, PPTX, Markdown and plain text, on the
  command line with `--material`, in the library with `outline_from_material` and
  `read_material`, and on the page through a documents tab beside the topic and the outline
- A PDF is read by its layout, so a running header, a footer and a page counter never reach
  the material and cannot turn up as a bullet point
- The outline step is told it is reading material and not a topic: it works through the pages
  to the last line, the amount of material sets the length of the deck, and over several files
  every one of them gets slides of its own
- A size budget: material longer than one call can carry is boiled down to the topics it
  covers, one call per piece, instead of being cut off at the end. Material over
  `--max-material-chars` is refused with an error naming the limit, never shortened silently
- Settings for the material: `--context-window`, `--max-material-chars`,
  `--max-material-files`, `--max-pages` and `--max-file-mb`

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

[Unreleased]: https://github.com/hamidmergan/outline2pptx/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hamidmergan/outline2pptx/releases/tag/v0.1.0
