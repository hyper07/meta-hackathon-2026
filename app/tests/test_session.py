"""
The agents together, with speech faked: each "chunk" is a (words, voice) pair, so
the tests drive the real gatekeeper, scribe, analyst, decider, check-in and
messenger without a microphone or models.
"""

import asyncio

import numpy as np
import pytest

from watchme import session as session_module
from watchme import speech, store

OWNER = np.eye(512, dtype=np.float32)[0]
STRANGER = np.eye(512, dtype=np.float32)[1]
LOUD_SPEECH = (np.sin(np.linspace(0, 2000, 64000)) * 0.1).astype(np.float32)


@pytest.fixture
def harness(monkeypatch):
    script: list[tuple[str, np.ndarray]] = []
    monkeypatch.setattr(speech, "transcribe", lambda audio, *_: [speech.Piece(0.0, 1.0, script[0][0])] if script[0][0] else [])
    monkeypatch.setattr(speech, "voiceprint", lambda audio: script.pop(0)[1])

    store.save_profile({"name": "Alex", "pin": "2468", "sos_phrase": "purple elephant",
                        "duress_phrase": "all good now", "voiceprint": OWNER.tolist(), "voice_model": speech.VOICE_MODEL,
                        "contacts": [{"name": "Sam", "phone": "+12125550100", "email": "sam@example.com", "call": True}]})
    s = session_module.Session()
    sent: list[dict] = []

    async def send(message):
        sent.append(message)

    async def say(words, voice=OWNER):
        script.append((words, voice))
        await s.on_audio((LOUD_SPEECH * 32767).astype("<i2").tobytes())
        await asyncio.sleep(0.01)   # let spawned agents run

    return s, send, sent, say


def kinds(s):
    return [r["kind"] for r in [*store.read_session(s.log.id)["events"]]]


async def test_only_the_owner_starts_and_stops(harness):
    s, send, sent, say = harness
    await s.attach(send)
    await say("watch me", STRANGER)
    assert s.state == "standby"
    assert any("not in your voice" in m["text"] for m in sent if m["type"] == "notice")
    voice = [m for m in sent if m["type"] == "voice"][-1]
    assert (voice["command"], voice["outcome"], voice["text"]) == ("start", "refused", None)   # no words in standby
    await say("watch me")
    assert s.state == "watching"
    await say("stop watching", STRANGER)
    assert [m for m in sent if m["type"] == "voice"][-1]["outcome"] == "refused"
    assert s.state == "watching"
    assert "stop_refused" in kinds(s) and "checkin" in kinds(s)   # someone else trying to stop it is itself a warning
    await say("I'm okay")
    await say("stop watching")
    assert s.state == "standby"


async def test_unanswered_checkin_alerts_contacts(harness):
    s, send, sent, say = harness
    await s.attach(send)
    await say("watch me")
    await say("no, stop, get off me", STRANGER)
    assert any(m["type"] == "checkin" for m in sent)
    await asyncio.sleep(0.5)                      # urgent timeout is 0.2 s in tests
    alert = next(m for m in sent if m["type"] == "alert")
    assert alert["contacts"] == 1
    assert {r["channel"] for r in alert["results"]} == {"sms", "call", "email"}
    assert all(r["result"] == "dry run" for r in alert["results"])
    session = store.read_session(s.log.id)
    assert session["chain"]["ok"]
    assert any(e["kind"] == "clip" for e in session["events"]) or s.clip   # the flagged audio is being kept


async def test_owner_voice_ok_cancels_the_alert_but_a_stranger_cannot(harness):
    s, send, sent, say = harness
    await s.attach(send)
    await say("watch me")
    await say("leave me alone, let me go", STRANGER)
    assert s.checkin_task
    await say("she's okay, I'm fine", STRANGER)
    assert s.checkin_task and "ok_refused" in kinds(s)
    await say("I'm okay")
    assert s.checkin_task is None
    await asyncio.sleep(0.5)
    assert not any(m["type"] == "alert" for m in sent)


async def test_duress_phrase_looks_off_but_alerts(harness):
    s, send, sent, say = harness
    await s.attach(send)
    await say("watch me")
    await say("it's all good now")
    await asyncio.sleep(0.05)
    assert s.state == "watching" and s.covert
    assert sent[-1] == {"type": "state", "state": "standby", "notice": "Watch Me is off."} or \
        any(m.get("notice") == "Watch Me is off." for m in sent)
    assert not any(m["type"] == "alert" for m in sent)   # nothing on screen gives it away
    assert "alert" in kinds(s)
    await say("stop watching")                            # a voice stop can't end duress mode
    assert s.state == "watching"
    await s.stop_with_pin("2468")
    assert s.state == "standby"


async def test_phone_dropping_off_while_watching_alerts(harness):
    s, send, sent, say = harness
    await s.attach(send)
    await say("watch me")
    s.detach(send)
    await asyncio.sleep(0.5)
    assert "alert" in kinds(s)


async def test_a_sentence_cut_by_the_chunk_end_is_held_for_the_next_chunk(harness, monkeypatch):
    s, send, sent, say = harness
    seen = []

    def transcribe(audio, *_):
        seen.append(audio.size / speech.SAMPLE_RATE)
        # First chunk: "watch me" runs to the very end, so it's held. Second: the whole sentence.
        return [speech.Piece(3.5, 3.95, "watch")] if len(seen) == 1 else [speech.Piece(0.0, 1.2, "watch me")]

    monkeypatch.setattr(speech, "transcribe", transcribe)
    await s.attach(send)
    await say("", OWNER)          # the script entry feeds the voiceprint of whichever piece is checked
    assert s.state == "standby" and s.held is not None
    await say("", OWNER)
    assert seen == [4.0, 4.5]     # the held half second came back in front of the next chunk
    assert s.state == "watching" and s.held is None


async def test_an_alert_in_the_last_session_does_not_mute_the_next(harness):
    s, send, sent, say = harness
    await s.attach(send)
    await say("watch me")
    await s.answer_checkin_tap(False, None) if s.checkin_task else await s.escalate("first emergency")
    await s.stop_with_pin("2468")
    await say("watch me")
    await say("no, stop, get off me", STRANGER)
    await asyncio.sleep(0.5)                      # urgent timeout is 0.2 s in tests
    kinds = [e["kind"] for e in store.read_session(s.log.id)["events"]]
    assert "alert" in kinds and "alert_skipped" not in kinds


async def test_two_decisions_at_once_open_one_checkin(harness):
    s, send, sent, say = harness
    await s.attach(send)
    await say("watch me")
    first = asyncio.ensure_future(s.start_checkin(False, "first"))
    second = asyncio.ensure_future(s.start_checkin(True, "second"))
    await asyncio.gather(first, second)
    assert sum(1 for m in sent if m["type"] == "checkin") == 1
    await say("I'm okay")
    await asyncio.sleep(0.5)                      # the first timer (0.3 s) would have fired by now if it were orphaned
    kinds = [e["kind"] for e in store.read_session(s.log.id)["events"]]
    assert kinds.count("checkin") == 1 and "checkin_missed" not in kinds and "alert" not in kinds


async def test_offline_keeps_all_audio_and_catches_up_later(harness, monkeypatch):
    s, send, sent, say = harness
    from watchme import muse
    if store.pending_path().exists():
        store.pending_path().unlink()

    async def api_down(transcript):
        return {"error": "ConnectError: no route to host", "retry": True}

    monkeypatch.setattr(muse, "analyse", api_down)
    await s.attach(send)
    await say("watch me")
    await say("no, stop, get off me", STRANGER)          # a flagged line: the Analyst is asked, and fails
    assert s.offline and store.read_pending()[0]["kind"] == "analyse"
    assert any(m["type"] == "offline" for m in sent)
    await say("what a nice evening", STRANGER)           # unflagged, yet kept while offline
    await say("the music is good", STRANGER)
    assert len(s.clip) >= 2
    assert any(m["type"] == "checkin" for m in sent)     # the phrase list and rules still work offline
    await say("I'm okay")
    await s.stop_with_pin("2468")
    session = store.read_session(s.log.id)
    assert any(e["kind"] == "clip" for e in session["events"]) and any(e["kind"] == "offline" for e in session["events"])
    assert all("at" in e for e in session["events"])      # every line carries a readable time

    async def api_back(transcript):
        return {"score": 0.8, "categories": ["coercion"], "quotes": [], "reason": "later analysis"}

    async def online():
        return True

    monkeypatch.setattr(muse, "analyse", api_back)
    monkeypatch.setattr(muse, "online", online)
    assert await s.catch_up_once() == 1
    assert not store.read_pending() and not s.offline
    session = store.read_session(s.log.id)
    flagged = next(x for x in session["segments"] if x["text"] == "no, stop, get off me")
    assert flagged["engine"] == "muse-spark" and flagged["score"] == 0.8 and flagged.get("later") is True
    assert session["chain"]["ok"] and "online" in [e["kind"] for e in session["events"]]


async def test_offline_audio_is_transcribed_by_muse_before_the_analysis(harness, monkeypatch):
    s, send, sent, say = harness
    from watchme import muse
    from watchme.config import settings
    if store.pending_path().exists():
        store.pending_path().unlink()
    monkeypatch.setattr(settings, "stt_engine", "muse")
    monkeypatch.setattr(settings, "voice_api_key", "test")

    async def api_down(transcript):
        return {"error": "ConnectError: no route to host", "retry": True}

    monkeypatch.setattr(muse, "analyse", api_down)
    await s.attach(send)
    await say("watch me")
    await say("no, stop, get off me", STRANGER)
    await say("what a nice evening", STRANGER)
    await say("I'm okay")
    await s.stop_with_pin("2468")
    assert {i["kind"] for i in store.read_pending()} == {"analyse", "transcribe"}

    seen = []

    async def api_back(transcript):
        seen.append(transcript)
        return {"score": 0.8, "categories": ["coercion"], "quotes": [], "reason": "later analysis"}

    async def online():
        return True

    monkeypatch.setattr(muse, "analyse", api_back)
    monkeypatch.setattr(muse, "online", online)
    monkeypatch.setattr(speech, "transcribe_muse", lambda audio: [speech.Piece(0.0, 1.0, "No. Stop. Get off me!")])
    monkeypatch.setattr(speech, "voiceprint", lambda audio: STRANGER)
    assert await s.catch_up_once() == 2
    assert not store.read_pending()
    assert seen == ["[other] No. Stop. Get off me!"]          # the Analyst read Muse's transcript, not Whisper's
    events = store.read_session(s.log.id)["events"]
    transcript = next(e for e in events if e["kind"] == "transcript")
    assert transcript["engine"] == "muse-voice-transcribe" and transcript["turns"][0]["speaker"] == "other"
    assert store.read_session(s.log.id)["chain"]["ok"]


async def test_the_analyst_reads_muse_transcript_of_the_last_minute(harness, monkeypatch):
    s, send, sent, say = harness
    from watchme import muse
    from watchme.config import settings
    monkeypatch.setattr(settings, "analyst_stt", "muse")
    monkeypatch.setattr(settings, "voice_api_key", "test")
    monkeypatch.setattr(settings, "meta_api_key", "test")
    sent_audio, seen = [], []

    def transcribe_muse(audio, mode="DIARIZATION", timeout=30):
        sent_audio.append(audio.size)
        return [speech.Piece(0.0, 1.0, "Finish your drink. Nobody will know.")]

    async def label_turns(audio, pieces, started):
        return [{"t": started, "speaker": "other", "similarity": 0.1, "text": p.text} for p in pieces]

    async def analyse(transcript):
        seen.append(transcript)
        return {"score": 0.8, "categories": ["drink_pressure"], "quotes": [], "reason": "pressure to drink"}

    monkeypatch.setattr(speech, "transcribe_muse", transcribe_muse)
    monkeypatch.setattr(s, "label_turns", label_turns)
    monkeypatch.setattr(muse, "analyse", analyse)
    await s.attach(send)
    await say("watch me")
    await say("no, stop, get off me", STRANGER)               # flagged: the Analyst runs
    assert seen and seen[0] == "[other] Finish your drink. Nobody will know."
    assert sent_audio == [LOUD_SPEECH.size]                  # the minute since "Watch me", in one request
    flagged = next(x for x in store.read_session(s.log.id)["segments"] if x["text"] == "no, stop, get off me")
    assert flagged["engine"] == "muse-spark" and flagged["transcript_engine"] == "muse-voice-transcribe"


async def test_alerts_carry_her_location_and_follow_her_when_she_moves(harness, monkeypatch):
    from watchme import messenger
    monkeypatch.setattr(session_module, "UPDATE_EVERY_S", 0)
    s, send, sent, say = harness
    await s.attach(send)
    await say("watch me")
    s.set_location({"lat": 40.7484, "lon": -73.9857, "accuracy": 12})
    await say("no, stop, get off me", STRANGER)
    assert {"type": "locate"} in sent                 # a check-in asks the phone for a fresh fix
    await asyncio.sleep(0.5)
    alert = next(m for m in sent if m["type"] == "alert")
    # The app adds the link itself, whole, whatever the model writes.
    assert "Location (now, within 12 m): https://maps.google.com/?q=40.748400,-73.985700" in alert["message"]
    spoken = messenger.spoken_text(alert["message"])
    assert "http" not in spoken and spoken.endswith("Their location is in the text message.")

    s.set_location({"lat": 40.7486, "lon": -73.9858})  # about 20 m: no update
    await asyncio.sleep(0.05)
    assert "location_update" not in kinds(s)
    s.set_location({"lat": 40.7580, "lon": -73.9855})  # about 1 km north: her people are told
    await asyncio.sleep(0.05)
    update = next(e for e in store.read_session(s.log.id)["events"] if e["kind"] == "location_update")
    assert "q=40.758000,-73.985500" in update["message"]
    assert {r["channel"] for r in update["results"]} == {"sms", "email"}   # no second phone call


def test_an_old_fix_is_labelled_last_known():
    fix = {"lat": 1.0, "lon": 2.0, "accuracy": None, "at": 1000.0}
    line = session_module.location_line(fix, now=1000.0 + 600)
    assert line.startswith("Location (last known, at ") and "10 min ago" in line
    assert session_module.location_line(None) is None


async def test_a_tap_can_get_help_but_never_say_im_ok(harness):
    s, send, sent, say = harness
    await s.attach(send)
    await say("watch me")
    await say("leave me alone, let me go", STRANGER)
    assert s.checkin_task
    await s.answer_checkin_tap(True, "2468")          # even with her PIN: whoever holds the phone could type it
    assert s.checkin_task and "ok_refused" in kinds(s)
    await s.answer_checkin_tap(False, None)           # "Get help now" needs nothing
    assert s.checkin_task is None
    assert next(m for m in sent if m["type"] == "alert")
