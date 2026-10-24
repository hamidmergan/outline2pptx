"""Real documents go through the reader: PDF, DOCX, PPTX, Markdown and plain text.

The header and footer detection is the most fragile part of the reading side, because it
decides by what repeats over a whole document. A deck built from a handout must not carry
its page footer as a bullet point, so these tests build small real documents and read
them back.
"""

import pytest

from outline2pptx import material as mt
from outline2pptx.errors import LimitError, NoReadableText, UnsupportedFileError
from outline2pptx.source_reading import count_pages, read_file

from conftest import PDF_FOOTER, PDF_HEADER, make_pdf


def test_a_pdf_keeps_its_body_and_loses_its_running_header_and_footer(handout_pdf):
    source = read_file(handout_pdf)
    assert source.pages == 6
    assert "Jahresarbeitszahl" in source.text
    assert "Kapitel 3: Die Waermequelle" in source.text
    # The footer stands on every page and says nothing about any of them.
    assert PDF_FOOTER not in source.text
    assert "Beispielverlag" not in source.text
    assert "Leitfaden Waermepumpe" not in source.text
    # Nor does the page counter of the header survive on its own.
    assert "Seite 3 von 6" not in source.text


def test_a_pdf_of_three_pages_keeps_everything_because_nothing_repeats_often_enough(tmp_path):
    """Under four pages "stands on most pages" says nothing, so no line is dropped."""
    path = tmp_path / "kurz.pdf"
    path.write_bytes(make_pdf([[(72, 800, PDF_HEADER.format(n=n, count=3)),
                                (72, 740, f"Kapitel {n}: Der Speicher")] for n in (1, 2, 3)]))
    source = read_file(path)
    assert "Leitfaden Waermepumpe" in source.text


def test_a_docx_is_read_with_its_heading_and_paragraphs(handout_docx):
    source = read_file(handout_docx)
    assert source.pages == 1
    assert "Waermepumpe im Altbau" in source.text
    assert "Abschnitt 3 erklaert" in source.text


def test_a_pptx_loses_the_line_that_stands_on_every_slide(handout_pptx):
    source = read_file(handout_pptx)
    assert "Die Waermequelle" in source.text
    assert "Jahresarbeitszahl" in source.text
    assert PDF_FOOTER not in source.text


def test_markdown_and_plain_text_are_read_as_one_page(tmp_path):
    (tmp_path / "note.md").write_text("# Titel\n\nEin **Satz** mit `code` und [Link](http://x).\n")
    (tmp_path / "note.txt").write_text("Eine einfache Zeile.\n")
    md = read_file(tmp_path / "note.md")
    assert md.pages == 1
    assert "Titel" in md.text and "Ein Satz mit" in md.text
    assert "**" not in md.text and "http://x" not in md.text
    assert read_file(tmp_path / "note.txt").text == "Eine einfache Zeile."


def test_the_page_count_of_a_pdf_and_a_pptx_is_read_without_reading_the_text(handout_pdf,
                                                                            handout_pptx):
    assert count_pages(".pdf", str(handout_pdf)) == 6
    assert count_pages(".pptx", str(handout_pptx)) == 6
    assert count_pages(".txt", "nothing.txt") is None


def test_a_format_the_deck_cannot_use_is_refused_by_name(tmp_path):
    path = tmp_path / "sound.mp3"
    path.write_bytes(b"not a document")
    with pytest.raises(UnsupportedFileError) as exc:
        read_file(path)
    assert ".mp3" in str(exc.value)
    assert ".pdf" in str(exc.value)


def test_a_pdf_without_a_text_layer_is_refused_instead_of_guessed_at(tmp_path):
    path = tmp_path / "scan.pdf"
    path.write_bytes(make_pdf([[], []]))
    with pytest.raises(NoReadableText):
        read_file(path)


def test_a_missing_file_says_so(tmp_path):
    with pytest.raises(UnsupportedFileError) as exc:
        read_file(tmp_path / "gone.pdf")
    assert "not found" in str(exc.value)


def test_a_document_with_more_pages_than_allowed_is_refused(handout_pdf):
    with pytest.raises(LimitError) as exc:
        read_file(handout_pdf, max_pages=3)
    assert "6 pages" in str(exc.value)


# --- The material of a whole run ---------------------------------------------------------

def test_the_material_of_several_files_carries_every_file_name_and_its_text(handout_pdf,
                                                                           handout_docx):
    found = mt.read([handout_pdf, handout_docx])
    assert found.names == ["leitfaden.pdf", "leitfaden.docx"]
    assert found.pages == 7
    assert found.chars == sum(len(s.text) for s in found.sources)
    assert "# leitfaden.pdf" in found.block
    assert "# leitfaden.docx" in found.block
    assert "Waermepumpe im Altbau" in found.block
    # What the page shows about the material.
    shown = found.as_dict()
    assert [f["name"] for f in shown["files"]] == ["leitfaden.pdf", "leitfaden.docx"]
    assert shown["chars"] == found.chars
    assert found.weights["leitfaden.pdf"] == len(found.sources[0].text)


def test_one_path_on_its_own_is_material_too(handout_docx):
    assert mt.read(handout_docx).names == ["leitfaden.docx"]
    assert mt.coerce(str(handout_docx)).names == ["leitfaden.docx"]


def test_material_already_read_passes_through_coerce_unchanged(handout_docx):
    found = mt.read([handout_docx])
    assert mt.coerce(found) is found


def test_more_files_than_allowed_are_refused_before_anything_is_read(handout_docx):
    with pytest.raises(LimitError) as exc:
        mt.read([handout_docx] * 4, max_files=3)
    assert "at most 3" in str(exc.value)


def test_material_over_the_character_limit_is_refused_and_never_cut_down(tmp_path):
    path = tmp_path / "lang.txt"
    path.write_text("Ein Satz ueber die Waermepumpe. " * 400)
    with pytest.raises(LimitError) as exc:
        mt.read([path], max_chars=1000)
    message = str(exc.value)
    assert "at most 1000" in message
    assert "OUTLINE2PPTX_MAX_MATERIAL_CHARS" in message
    # And the whole text is there when the limit allows it.
    assert mt.read([path]).chars > 1000


def test_no_document_at_all_is_an_error_and_not_an_empty_deck():
    with pytest.raises(NoReadableText):
        mt.read([])
    with pytest.raises(NoReadableText):
        mt.coerce([])


def test_a_text_without_a_document_behind_it_becomes_material_as_well():
    found = mt.text_material("Die Jahresarbeitszahl sagt, wie gut die Pumpe arbeitet.")
    assert found.names == ["material.txt"]
    assert "Jahresarbeitszahl" in found.block
    with pytest.raises(NoReadableText):
        mt.text_material("   ")
