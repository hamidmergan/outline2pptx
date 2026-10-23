import time
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pptx import Presentation

from conftest import outline_answer
from test_api import OUTLINE_MD, answer_for_batch

pytest.importorskip("fastapi")


def make_client(server=None, **extra):
    from outline2pptx.web.app import create_app

    defaults = dict(extra)
    if server is not None:
        defaults.setdefault("base_url", server.base_url)
        defaults.setdefault("model", "a-model")
    return TestClient(create_app(defaults, allowed_hosts=["testserver"]))


def wait_for(client, state="done", seconds=30):
    deadline = time.time() + seconds
    while time.time() < deadline:
        job = client.get("/api/status").json()
        if job["state"] == state:
            return job
        if job["state"] == "error":
            return job
        time.sleep(0.05)
    raise AssertionError(f"the job never reached {state}")


def test_the_page_is_served():
    client = make_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "outline2pptx" in response.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_info_lists_the_templates_and_the_limits():
    data = make_client().get("/api/info").json()
    assert [t["id"] for t in data["templates"]] == ["clean", "forest", "warm"]
    assert data["languages"] == ["de", "en"]
    assert data["min_slides"] == 3 and data["max_slides"] == 30
    assert data["configured"] is False


def test_info_shows_what_the_environment_decided(server):
    data = make_client(server, language="de", template="forest").get("/api/info").json()
    assert data["configured"] is True
    assert data["model"] == "a-model"
    assert data["language"] == "de"
    assert data["template"] == "forest"


def test_an_unknown_host_is_refused():
    from outline2pptx.web.app import create_app

    client = TestClient(create_app({}, allowed_hosts=["localhost"]))
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400


def test_a_cross_origin_request_is_refused():
    client = make_client()
    response = client.get("/api/info", headers={"Origin": "http://evil.example"})
    assert response.status_code == 403


def test_the_outline_route_plans_from_a_topic(server):
    server.outline = outline_answer(6, title="Bees")
    client = make_client(server)
    data = client.post("/api/outline", json={"topic": "Bees", "slides": 6}).json()
    assert data["outline"].startswith("# Bees")
    assert server.kinds() == ["outline"]


def test_the_outline_route_needs_a_topic():
    response = make_client().post("/api/outline", json={"topic": "  "})
    assert response.status_code == 400
    assert "topic" in response.json()["detail"]


def test_the_fields_on_the_page_beat_the_environment(server):
    server.outline = outline_answer(5)
    client = make_client(base_url="http://127.0.0.1:1/v1", model="wrong")
    client.post("/api/outline", json={"topic": "Bees", "base_url": server.base_url,
                                      "model": "from-the-page"})
    assert server.requests[0]["body"]["model"] == "from-the-page"


def test_without_a_model_the_outline_route_says_what_is_missing():
    response = make_client().post("/api/outline", json={"topic": "Bees"})
    assert response.status_code == 400
    assert "base_url" in response.json()["detail"]


def test_build_runs_and_the_deck_can_be_downloaded(server):
    server.slides = answer_for_batch
    client = make_client(server)
    assert client.post("/api/build", json={"outline": OUTLINE_MD}).json()["state"] == "running"
    job = wait_for(client)
    assert job["state"] == "done", job["error"]
    assert len(job["slides"]) == 6
    assert job["slides"][0]["number"] == 1 and job["slides"][0]["role"] == "cover"
    assert job["info"]["template"] == "Clean"
    deck = client.get("/api/download")
    assert deck.status_code == 200
    assert deck.headers["content-disposition"].endswith('filename="deck.pptx"')
    prs = Presentation(BytesIO(deck.content))
    assert len(prs.slides._sldIdLst) == 6


def test_an_empty_outline_is_refused(server):
    response = make_client(server).post("/api/build", json={"outline": "  "})
    assert response.status_code == 400


def test_a_failing_model_ends_the_job_with_the_reason(server):
    server.slides = "nonsense"
    client = make_client(server)
    client.post("/api/build", json={"outline": OUTLINE_MD})
    job = wait_for(client, "error")
    assert job["state"] == "error" and job["error"]


def test_images_need_an_image_model(server):
    response = make_client(server).post("/api/build", json={"outline": OUTLINE_MD, "images": True})
    assert response.status_code == 400
    assert "image_model" in response.json()["detail"]


def test_notes_reach_the_file(server):
    from conftest import slides_answer

    def reply(body):
        user = body["messages"][1]["content"]
        ids = [line.split()[1] for line in user.splitlines() if line.startswith("SLIDE ")]
        return slides_answer(ids, notes="What the speaker says here.")

    server.slides = reply
    client = make_client(server)
    client.post("/api/build", json={"outline": OUTLINE_MD, "notes": True})
    assert wait_for(client)["state"] == "done"
    prs = Presentation(BytesIO(client.get("/api/download").content))
    assert any(s.has_notes_slide for s in prs.slides)


def test_download_before_a_run_is_a_404():
    assert make_client().get("/api/download").status_code == 404


def test_the_preview_says_so_without_libreoffice(server, monkeypatch):
    server.slides = answer_for_batch
    monkeypatch.setattr("outline2pptx.render.available", lambda: False)
    client = make_client(server)
    client.post("/api/build", json={"outline": OUTLINE_MD})
    assert wait_for(client)["state"] == "done"
    response = client.get("/api/preview/1")
    assert response.status_code == 409
    assert "LibreOffice" in response.json()["detail"]


def test_the_preview_serves_one_png_per_slide(server, monkeypatch):
    server.slides = answer_for_batch
    monkeypatch.setattr("outline2pptx.render.available", lambda: True)
    monkeypatch.setattr("outline2pptx.preview.render", lambda data, dpi=80: [b"\x89PNG-one"])
    client = make_client(server)
    client.post("/api/build", json={"outline": OUTLINE_MD})
    assert wait_for(client)["state"] == "done"
    response = client.get("/api/preview/1")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert client.get("/api/preview/9").status_code == 404


def test_a_second_outline_is_refused_while_one_is_being_planned(server, monkeypatch):
    """One call to the model at a time, so two browser tabs cannot plan two outlines at once."""
    import threading

    started, go = threading.Event(), threading.Event()

    def slow(topic, **kwargs):
        started.set()
        assert go.wait(10)
        return OUTLINE_MD

    monkeypatch.setattr("outline2pptx.api.outline_from_topic", slow)
    client = make_client(server)
    first: dict = {}

    def plan():
        first["response"] = client.post("/api/outline", json={"topic": "Bees"})

    worker = threading.Thread(target=plan)
    worker.start()
    try:
        assert started.wait(10)
        second = client.post("/api/outline", json={"topic": "Bees"})
        build = client.post("/api/build", json={"outline": OUTLINE_MD})
    finally:
        go.set()
        worker.join(10)
    assert second.status_code == 409
    assert build.status_code == 409
    assert first["response"].status_code == 200
    # The flag is cleared again, so the next call goes through.
    assert client.post("/api/outline", json={"topic": "Bees"}).status_code == 200


def test_the_page_shows_every_field_of_the_deck_info(server):
    """The info the server computes is shown, not collected and dropped."""
    from pathlib import Path

    import outline2pptx.web.app as web

    server.slides = answer_for_batch
    client = make_client(server, instructions="Keep it short", style_text="Flat shapes")
    client.post("/api/build", json={"outline": OUTLINE_MD})
    info = wait_for(client)["info"]
    assert info["model"] == "a-model"
    assert info["template"] and info["language"] and info["instructions"] and info["style_text"]
    page = (Path(web.STATIC) / "index.html").read_text("utf8")
    script = (Path(web.STATIC) / "app.js").read_text("utf8")
    assert 'id="deckInfo"' in page
    for key in info:
        if key == "slides":
            continue
        assert f'"{key}"' in script, f"the page never reads {key}"
