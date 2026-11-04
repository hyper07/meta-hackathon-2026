"""
The public demo (DEMO_MODE=1, the hosted live app): one visitor at a time, only their page may use
the API, alerts are always a dry run, no audio is kept, and everything is wiped when they leave.
"""
import json

import pytest
from fastapi.testclient import TestClient

from watchme import main, store
from watchme.config import settings


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    # Even with real alert keys set, a demo must never send anything.
    monkeypatch.setattr(settings, "twilio_sid", "AC-test")
    monkeypatch.setattr(settings, "twilio_token", "token")
    monkeypatch.setattr(settings, "twilio_from", "+15550000000")
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_user", "user")
    monkeypatch.setattr(settings, "smtp_password", "password")
    store.reset_demo()
    main.VISIT.update(ws=None, token="")
    yield TestClient(main.app)
    main.VISIT.update(ws=None, token="")


def visit_messages(ws):
    """The first messages a visitor's page gets: hello, then the demo note with its token."""
    hello, demo = ws.receive_json(), ws.receive_json()
    assert hello["type"] == "hello" and demo["type"] == "demo"
    return hello, demo


def test_alerts_and_audio_are_off_in_a_demo_whatever_is_set(demo):
    assert not settings.sms_ready and not settings.email_ready and not settings.keep_audio
    assert settings.describe()["sms_and_calls"] == "dry run" and settings.describe()["email"] == "dry run"


def test_a_second_visitor_waits(demo):
    with demo.websocket_connect("/ws") as first:
        visit_messages(first)
        with demo.websocket_connect("/ws") as second:
            busy = second.receive_json()
            assert busy["type"] == "busy" and "visit" not in busy


def test_only_the_current_visitors_page_may_use_the_api(demo):
    assert demo.get("/api/status").status_code == 200            # always open: no personal data
    assert demo.get("/api/sessions").status_code == 423           # no visitor yet
    with demo.websocket_connect("/ws") as ws:
        _, note = visit_messages(ws)
        assert demo.get("/api/sessions").status_code == 423       # someone else, without the token
        assert demo.get("/api/sessions", headers={"X-Visit": "guess"}).status_code == 423
        assert demo.get("/api/sessions", headers={"X-Visit": note["visit"]}).status_code == 200


def test_everything_the_visitor_left_is_wiped(demo):
    with demo.websocket_connect("/ws") as ws:
        _, note = visit_messages(ws)
        profile = store.load_profile()
        profile["voiceprint"], profile["name"] = [0.1] * 192, "Visitor"
        store.save_profile(profile)
        (settings.data_dir / "notice").mkdir(exist_ok=True)
        (settings.data_dir / "notice" / "log.jsonl").write_text(json.dumps({"text": "something private"}))
    # The page closed: the next visitor starts from the demo profile, with nothing left behind.
    assert main.VISIT["ws"] is None and main.VISIT["token"] == ""
    assert sorted(p.name for p in settings.data_dir.iterdir()) == ["profile.json"]
    profile = store.load_profile()
    assert profile["voiceprint"] is None and profile["name"] == store.DEMO_PROFILE["name"]
    assert demo.get("/api/sessions", headers={"X-Visit": note["visit"]}).status_code == 423   # the old token is dead


def test_outside_a_demo_nothing_changes(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    client = TestClient(main.app)
    assert client.get("/api/sessions").status_code == 200
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "hello"
