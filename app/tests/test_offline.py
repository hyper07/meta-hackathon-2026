"""
With no internet and no models (the "on this device only" plan, or the network down): Whisper, the
voiceprint, the phrase list and the fixed rules still have to catch the case Watch Me was built for.
"""
import asyncio

from test_session import STRANGER, harness  # noqa: F401  (fixture)
from watchme import lexicon
from watchme.config import settings


def test_a_drink_then_feeling_unwell_is_the_drugging_pattern():
    assert lexicon.drugging_pattern(["Come on, finish your drink.", "I feel really dizzy."]).weight >= settings.trigger_score
    assert lexicon.drugging_pattern(["Drink this, it's special.", "I can't move my legs"]) is not None


def test_either_alone_is_not():
    for minute in (["Come on, finish your drink."], ["I feel really dizzy, I stood up too fast."],
                   ["I feel sick, I ate too much pizza."]):
        assert lexicon.drugging_pattern(minute) is None
    for line in ("Come on, finish your drink.", "I feel really dizzy."):
        assert lexicon.score(lexicon.scan(line)) < settings.trigger_score     # each alone stays below the trigger


async def test_on_the_device_only_a_drink_then_dizziness_asks_are_you_ok(harness, monkeypatch):
    monkeypatch.setattr(settings, "model_plan", "local")
    s, send, sent, say = harness
    await s.attach(send)
    monkeypatch.setattr(settings, "model_plan", "local")            # attach applies her profile's plan
    await say("watch me")
    await say("come on, finish your drink", STRANGER)
    assert not any(m["type"] == "checkin" for m in sent)           # one line alone: no
    await say("I feel really dizzy")
    await asyncio.sleep(0.05)
    assert any(m["type"] == "checkin" for m in sent)               # together, with no model: "Are you OK?"
    decision = next(m for m in sent if m["type"] == "decision")
    assert decision["engine"] == "rules"
