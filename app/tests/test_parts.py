import json

from watchme import commands, decider, lexicon, store


def test_lexicon_scores_distress_above_trigger_and_banter_below():
    assert lexicon.level(lexicon.score(lexicon.scan("no, stop, get off me"))) == "urgent"
    assert lexicon.score(lexicon.scan("can you pass the chips")) == 0
    # A bare "stop" is only a note for review, not a reason to interrupt the owner.
    assert lexicon.level(lexicon.score(lexicon.scan("stop it, that's hilarious"))) == "watch"


def test_lexicon_does_not_count_the_same_words_twice():
    hits = lexicon.scan("somebody help")
    assert [h.phrase.lower() for h in hits] == ["somebody help"]


def test_commands_and_their_removal_before_scoring():
    assert commands.find("hey, watch me okay") >= {"start"}
    assert commands.find("stop watching me") >= {"stop"}
    assert "start" not in commands.find("stop watching me")
    assert "stop" not in commands.find("thanks for watching")
    assert commands.find("yes I'm okay") >= {"ok"}
    assert commands.find("pineapple sky", sos_phrase="pineapple sky") >= {"sos"}
    assert commands.strip_commands("stop watching me") == ""


def test_decider_asks_when_unsure_and_never_alerts_directly():
    assert decider.apply_rules({"discard": 0.9, "ask": 0.08, "alert": 0.02})[0] == "discard"
    action, urgent, _ = decider.apply_rules({"discard": 0.6, "ask": 0.3, "alert": 0.1})
    assert (action, urgent) == ("ask", False)          # top is discard, but below 0.83
    action, urgent, _ = decider.apply_rules({"discard": 0.1, "ask": 0.2, "alert": 0.7})
    assert (action, urgent) == ("ask", True)           # alert becomes an urgent ask


def test_evidence_chain_detects_an_edit():
    log = store.EvidenceLog()
    log.append("start", detail="test")
    log.append("segment", seg="s1", text="leave me alone", score=0.6)
    log.append("update", seg="s1", score=0.8, level="urgent")
    session = store.read_session(log.id)
    assert session["chain"]["ok"] and session["segments"][0]["score"] == 0.8

    lines = log.path.read_text().splitlines()
    record = json.loads(lines[1]); record["text"] = "hello"
    lines[1] = json.dumps(record)
    log.path.write_text("\n".join(lines) + "\n")
    assert store.read_session(log.id)["chain"] == {"ok": False, "broken_at": 2, "lines": 3}


def test_alerts_go_to_defaults_else_family_else_everyone():
    from watchme.messenger import recipients
    sam = {"name": "Sam", "phone": "+12125550100", "relation": "friend"}
    mom = {"name": "Mom", "phone": "+12125550101", "relation": "mom"}
    ana = {"name": "Ana", "email": "ana@example.com", "relation": "roommate"}
    assert recipients([sam, mom, {**ana, "default": True}]) == ([{**ana, "default": True}], "your default contacts")
    assert recipients([sam, mom, ana]) == ([mom], "your family (no default set)")
    assert recipients([sam, ana]) == ([sam, ana], "everyone you listed (no default or family set)")
    assert recipients([]) == ([], "everyone you listed (no default or family set)")


async def test_muse_decider_uses_the_same_rules(monkeypatch):
    from watchme import decider, muse
    from watchme.config import settings
    monkeypatch.setattr(settings, "meta_api_key", "test")

    async def chat(system, user, **_):
        return answers.pop(0)

    monkeypatch.setattr(muse, "_chat", chat)
    answers = ['{"discard": 0.1, "ask": 0.2, "alert": 0.7, "why": "x"}',
               '{"discard": 0.6, "ask": 0.4, "alert": 0.0, "why": "x"}',      # unsure: never discards
               '{"discard": 0.9, "ask": 0.1, "alert": 0.0, "why": "x"}',
               'no json at all']
    analysis = {"score": 0.8, "categories": [], "reason": ""}
    first = await decider.decide("t", analysis, {})
    assert (first["engine"], first["action"], first["urgent"]) == ("muse-spark", "ask", True)
    assert (await decider.decide("t", analysis, {}))["action"] == "ask"
    assert (await decider.decide("t", analysis, {}))["action"] == "discard"
    failed = await decider.decide("t", analysis, {})          # a bad answer falls back to the rules, which ask
    assert (failed["engine"], failed["action"]) == ("rules", "ask")


def test_muse_transcribe_falls_back_to_whisper(monkeypatch):
    import httpx
    from watchme import speech
    from watchme.config import settings
    monkeypatch.setattr(settings, "stt_engine", "muse")
    monkeypatch.setattr(settings, "voice_api_key", "test")
    calls = []

    def muse_down(audio, timeout=30):
        calls.append("muse")
        raise httpx.ConnectError("no route to host")

    monkeypatch.setattr(speech, "transcribe_muse", muse_down)
    monkeypatch.setattr(speech, "transcribe_whisper", lambda audio: [speech.Piece(0, 1, "from whisper")])
    speech.resume_muse()
    assert speech.transcribe(None)[0].text == "from whisper"
    assert speech.last_engine == "whisper" and "ConnectError" in speech.last_error
    speech.transcribe(None)                                    # paused: no second wait on a dead connection
    assert calls == ["muse"]
    monkeypatch.setattr(speech, "transcribe_muse", lambda audio, timeout=30: [speech.Piece(0, 1, "from muse")])
    speech.resume_muse()                                       # back online
    assert speech.transcribe(None)[0].text == "from muse" and speech.last_engine == "muse"
    assert speech.transcribe(None, False)[0].text == "from whisper"   # standby: only on this machine


def test_one_enrollment_line_becomes_three_overlapping_pieces():
    import numpy as np
    from watchme import speech
    sr = speech.SAMPLE_RATE
    line = np.concatenate([np.zeros(sr), (np.sin(np.linspace(0, 9000, 4 * sr)) * 0.2).astype(np.float32), np.zeros(sr)])
    pieces = speech.enrollment_pieces(line)
    assert len(pieces) == 3
    assert all(abs(len(p) / sr - 2.0) < 0.05 for p in pieces)   # 4 s of speech -> three 2 s windows, half overlapping
    assert abs(len(speech.voiced(line)) / sr - 4.0) < 0.05      # the silence around it is dropped
