import io
from io import BytesIO

import pytest
from pptx import Presentation

from conftest import outline_answer, slides_answer
from outline2pptx import cli
from test_api import OUTLINE_MD, answer_for_batch


def flags(server):
    return ["--base-url", server.base_url, "--model", "a-model"]


@pytest.fixture
def outline_file(tmp_path):
    path = tmp_path / "outline.md"
    path.write_text(OUTLINE_MD, "utf8")
    return path


def test_help_is_english(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    text = capsys.readouterr().out
    assert "Build a PowerPoint deck" in text
    assert "--base-url" in text and "--template" in text


def test_version_prints_the_number(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert "0.1.0" in capsys.readouterr().out


def test_list_templates_shows_the_built_in_ones(capsys):
    assert cli.main(["--list-templates"]) == 0
    out = capsys.readouterr().out
    assert "clean" in out and "forest" in out and "warm" in out


def test_build_from_a_file_writes_the_deck(server, outline_file, tmp_path, capsys):
    server.slides = answer_for_batch
    out = tmp_path / "deck.pptx"
    assert cli.main([str(outline_file), "-o", str(out), *flags(server)]) == 0
    assert out.exists()
    prs = Presentation(BytesIO(out.read_bytes()))
    assert len(prs.slides._sldIdLst) >= 6
    assert "Wrote" in capsys.readouterr().err


def test_the_output_defaults_to_the_outline_name(server, outline_file):
    server.slides = answer_for_batch
    assert cli.main([str(outline_file), *flags(server)]) == 0
    assert outline_file.with_suffix(".pptx").exists()


def test_an_outline_can_come_from_standard_input(server, tmp_path, monkeypatch):
    server.slides = answer_for_batch
    monkeypatch.setattr("sys.stdin", io.StringIO(OUTLINE_MD))
    out = tmp_path / "deck.pptx"
    assert cli.main(["-", "-o", str(out), *flags(server)]) == 0
    assert out.exists()


def test_a_topic_plans_the_outline_first(server, tmp_path):
    server.outline = outline_answer(6, title="Bees")
    server.slides = answer_for_batch
    out = tmp_path / "deck.pptx"
    assert cli.main(["--topic", "Bees", "--slides", "6", "-o", str(out), *flags(server)]) == 0
    assert server.kinds()[0] == "outline"
    assert out.exists()


def test_outline_only_prints_markdown_and_builds_nothing(server, capsys, tmp_path):
    server.outline = outline_answer(5, title="Bees")
    out = tmp_path / "deck.pptx"
    assert cli.main(["--topic", "Bees", "--outline-only", "-o", str(out), *flags(server)]) == 0
    assert capsys.readouterr().out.startswith("# Bees")
    assert not out.exists()


def test_images_switch_on_the_image_model(server, outline_file, tmp_path):
    server.slides = answer_for_batch
    out = tmp_path / "deck.pptx"
    code = cli.main([str(outline_file), "-o", str(out), "--images", "--image-model", "draw",
                     *flags(server)])
    assert code == 0
    assert "image" in server.kinds()


def test_notes_reach_the_file(server, outline_file, tmp_path):
    def reply(body):
        user = body["messages"][1]["content"]
        ids = [line.split()[1] for line in user.splitlines() if line.startswith("SLIDE ")]
        return slides_answer(ids, notes="What the speaker says about this slide.")

    server.slides = reply
    out = tmp_path / "deck.pptx"
    assert cli.main([str(outline_file), "-o", str(out), "--notes", *flags(server)]) == 0
    prs = Presentation(BytesIO(out.read_bytes()))
    assert any(s.has_notes_slide for s in prs.slides)


def test_without_an_outline_or_a_topic_it_asks_for_one(capsys):
    assert cli.main([]) == 2
    assert "outline file or --topic" in capsys.readouterr().err


def test_an_outline_and_a_topic_together_are_refused(capsys, outline_file):
    assert cli.main([str(outline_file), "--topic", "Bees"]) == 2
    assert "not both" in capsys.readouterr().err


def test_a_missing_outline_file_is_reported(capsys, tmp_path):
    assert cli.main([str(tmp_path / "nope.md"), "--base-url", "http://x/v1", "--model", "m"]) == 2
    assert "No such outline file" in capsys.readouterr().err


def test_a_missing_base_url_names_the_flag(capsys, outline_file):
    assert cli.main([str(outline_file)]) == 2
    err = capsys.readouterr().err
    assert "--base-url" in err and "--model" in err


def test_an_unknown_template_names_the_known_ones(capsys, outline_file, server):
    assert cli.main([str(outline_file), "--template", "nope", *flags(server)]) == 2
    assert "clean" in capsys.readouterr().err


def test_images_without_an_image_model_are_refused(capsys, outline_file, server):
    assert cli.main([str(outline_file), "--images", *flags(server)]) == 2
    assert "image_model" in capsys.readouterr().err


def test_settings_can_come_from_the_environment(server, outline_file, tmp_path, monkeypatch):
    server.slides = answer_for_batch
    monkeypatch.setenv("OUTLINE2PPTX_BASE_URL", server.base_url)
    monkeypatch.setenv("OUTLINE2PPTX_MODEL", "a-model")
    out = tmp_path / "deck.pptx"
    assert cli.main([str(outline_file), "-o", str(out)]) == 0
    assert out.exists()


def test_preview_says_so_without_libreoffice(server, outline_file, tmp_path, monkeypatch, capsys):
    server.slides = answer_for_batch
    monkeypatch.setattr("outline2pptx.render.available", lambda: False)
    out = tmp_path / "deck.pptx"
    code = cli.main([str(outline_file), "-o", str(out), "--preview", str(tmp_path / "png"),
                     *flags(server)])
    assert code == 2
    assert "LibreOffice" in capsys.readouterr().err


def test_preview_writes_one_png_per_slide(server, outline_file, tmp_path, monkeypatch):
    server.slides = answer_for_batch
    monkeypatch.setattr("outline2pptx.render.available", lambda: True)
    monkeypatch.setattr("outline2pptx.preview.render", lambda data, dpi=80: [b"png1", b"png2"])
    out = tmp_path / "deck.pptx"
    folder = tmp_path / "png"
    assert cli.main([str(outline_file), "-o", str(out), "--preview", str(folder),
                     *flags(server)]) == 0
    assert sorted(p.name for p in folder.iterdir()) == ["slide-01.png", "slide-02.png"]


def test_serve_without_the_extra_packages_says_what_to_install(capsys, monkeypatch):
    import builtins

    real = builtins.__import__

    def no_uvicorn(name, *args, **kwargs):
        if name == "uvicorn":
            raise ImportError("no uvicorn")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_uvicorn)
    assert cli.main(["serve"]) == 2
    assert "outline2pptx[ui]" in capsys.readouterr().err
