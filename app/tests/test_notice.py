"""
Notice mode: the debrief endpoint, the notice book, patterns, and that a live
notice session never interrupts or alerts.
"""

import asyncio
import shutil

import pytest
from fastapi.testclient import TestClient

from watchme import main, notice, store
from watchme.config import settings

from test_session import STRANGER, harness  # noqa: F401  (fixture)

PROFESSOR = ("At office hours Professor R said we could talk about the grade over drinks at his place. "
             "I said no. He said B students don't get recommendation letters.")


def fake_review(match, *moments):
    async def review(text, setting=""):
        return {"match": match, "moments": [{"quote": q, "type": t, "why": "test"} for t, q in moments],
                "summary": "test summary", "engine": "test"}
    return review


@pytest.fixture(autouse=True)
def empty_book():
    shutil.rmtree(settings.data_dir / "notice", ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(main.app)


def test_debrief_is_reviewed_saved_and_counted(client, monkeypatch):
    monkeypatch.setattr(notice, "review", fake_review("clear", ("conditions", "B students don't get recommendation letters")))
    for day in ("2026-10-01", "2026-10-15"):
        r = client.post("/api/notice/debrief", json={"text": PROFESSOR, "setting": "school", "who": "Prof. R", "when": day})
        assert r.status_code == 200, r.text
    monkeypatch.setattr(notice, "review", fake_review("none"))
    client.post("/api/notice/debrief", json={"text": "My TA gave blunt feedback on my lab report.", "who": "TA"})

    page = client.get("/api/notice").json()
    assert len(page["records"]) == 3 and page["chain"]["ok"]
    # Only matching records count toward a pattern, and names are grouped case-insensitively.
    assert [(p["who"], p["times"], p["first"], p["last"]) for p in page["patterns"]] == [("Prof. R", 2, "2026-10-01", "2026-10-15")]
    assert page["patterns"][0]["types"][0]["label"] == "Strings attached"

    exported = client.get("/api/notice/export").text
    assert "Prof. R" in exported and "Strings attached" in exported and "unaltered" in exported
    assert notice.DISCLAIMER in exported


def test_debrief_rejects_bad_input(client):
    assert client.post("/api/notice/debrief", json={"text": "hi"}).status_code == 400
    assert client.post("/api/notice/debrief", json={"text": PROFESSOR, "when": "last tuesday"}).status_code == 400


async def test_review_drops_quotes_not_in_the_text(monkeypatch):
    async def chat(system, user, **_):
        return ('{"match": "clear", "moments": [{"quote": "B students don\'t get recommendation letters", "type": "conditions", "why": "x"},'
                ' {"quote": "words nobody said", "type": "advances", "why": "x"}, {"quote": "I said no", "type": "made_up", "why": "x"}],'
                ' "summary": "s"}')
    monkeypatch.setattr(settings, "meta_api_key", "test")
    monkeypatch.setattr(notice.muse, "_chat", chat)
    result = await notice.review(PROFESSOR, "school")
    assert [m["type"] for m in result["moments"]] == ["conditions"]


async def test_notice_session_notes_instead_of_asking(harness, monkeypatch):  # noqa: F811
    s, send, sent, say = harness
    reviewed = []

    async def review(text, setting=""):
        reviewed.append(text)
        return {"match": "some", "moments": [], "summary": "", "engine": "test"}

    monkeypatch.setattr(notice, "review", review)
    await s.attach(send)
    await s.set_mode("notice")
    await say("watch me")
    assert s.state == "watching" and s.mode == "notice"
    await say("no, stop, get off me", STRANGER)
    await say("stop watching", STRANGER)                    # a stranger's stop is refused, but noted, not asked
    await asyncio.sleep(0.5)
    assert not any(m["type"] in ("checkin", "alert") for m in sent)
    kinds = [e["kind"] for e in store.read_session(s.log.id)["events"]]
    assert "noted" in kinds and "checkin" not in kinds and "stop_refused" in kinds
    s.detach(send)                                          # a dropped phone doesn't alert in notice mode
    await asyncio.sleep(0.5)
    assert "alert" not in [e["kind"] for e in store.read_session(s.log.id)["events"]]
    await s.attach(send)
    await say("stop watching")
    await asyncio.sleep(0.05)
    assert s.state == "standby"
    assert reviewed and "get off me" in reviewed[0]
    assert notice.read()["records"][-1]["source"] == "session"


async def test_live_notice_needs_one_party_consent(harness, monkeypatch):  # noqa: F811
    s, send, sent, say = harness
    monkeypatch.setattr(settings, "recording_rule", "all-party")
    await s.attach(send)
    await s.set_mode("notice")
    assert s.mode == "watch"
    assert any("consent" in m.get("text", "") for m in sent if m["type"] == "notice")


async def test_review_a_recorded_session(harness, monkeypatch):  # noqa: F811
    s, send, sent, say = harness
    seen = []

    async def review(text, setting=""):
        seen.append(text)
        return {"match": "clear", "moments": [{"quote": "drinks at my place", "type": "isolation", "why": "test"}],
                "summary": "", "engine": "test"}

    monkeypatch.setattr(notice, "review", review)
    await s.attach(send)
    await say("watch me")
    await say("we could talk about it over drinks at my place", STRANGER)
    await say("stop watching")
    r = TestClient(main.app).post(f"/api/notice/session/{s.log.id}", json={"who": "Prof. R", "setting": "school"})
    assert r.status_code == 200, r.text
    assert "[other] we could talk about it over drinks at my place" in seen[0]
    assert r.json()["record"]["session"] == s.log.id and r.json()["patterns"][0]["who"] == "Prof. R"


def test_label_a_record_later(client, monkeypatch):
    monkeypatch.setattr(notice, "review", fake_review("clear", ("isolation", "drinks at his place")))
    rec = notice.add("[other] drinks at his place", {"match": "clear", "moments": [{"quote": "drinks at his place",
                     "type": "isolation", "why": "x"}], "summary": ""}, setting="", who="", where="", when="2026-10-31T12:00",
                     source="session")
    r = client.post(f"/api/notice/{rec['id']}/label", json={"who": "Prof. R", "setting": "school", "where": "office"})
    assert r.status_code == 200 and r.json()["record"]["who"] == "Prof. R" and r.json()["record"]["labelled"]
    assert r.json()["patterns"][0]["who"] == "Prof. R" and r.json()["chain"]["ok"]
    assert client.post("/api/notice/nope/label", json={"who": "x"}).status_code == 404


def test_profile_keeps_relationship_and_default(client):
    r = client.post("/api/profile", json={"name": "Alex", "contacts": [
        {"name": "Mom", "phone": "+12125550101", "relation": "Mom"},
        {"name": "Sam", "email": "sam@example.com", "relation": "boss", "default": True}]})
    assert r.status_code == 200, r.text
    assert [(c["relation"], c["default"]) for c in r.json()["contacts"]] == [("mom", False), ("", True)]


def test_debrief_offline_is_saved_then_reviewed_when_back(client, monkeypatch):
    from watchme import muse
    if store.pending_path().exists():
        store.pending_path().unlink()

    async def down(text, setting=""):
        return {"error": "ReadTimeout", "retry": True}

    monkeypatch.setattr(notice, "review", down)
    r = client.post("/api/notice/debrief", json={"text": PROFESSOR, "setting": "school", "who": "Prof. R", "when": "2026-10-20"})
    assert r.status_code == 200 and r.json()["record"]["pending"] is True and r.json()["record"]["review"] is None
    assert r.json()["pending"] == 1

    async def back(text, setting=""):
        return {"match": "clear", "moments": [{"quote": "B students don't get recommendation letters", "type": "conditions", "why": "x"}],
                "summary": "s", "engine": "test"}

    async def online():
        return True

    monkeypatch.setattr(notice, "review", back)
    monkeypatch.setattr(muse, "online", online)
    assert client.post("/api/pending/retry").json()["done"] == 1
    page = client.get("/api/notice").json()
    rec = next(x for x in page["records"] if x["when"] == "2026-10-20")
    assert rec["review"]["match"] == "clear" and rec["pending"] is False and rec["reviewed_at"]
    assert page["patterns"][0]["who"] == "Prof. R" and page["chain"]["ok"]
