"""
The model plan she picks in Setup, for cost: which models the agents may call. The check-ins and alerts
work in every plan; only the analysis and the Notice reviews depend on a model.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

from watchme import decider, main, muse, notice, session as session_module
from watchme.config import settings

META = "https://api.meta.ai/v1"
OPEN = "https://inference.baseten.co/v1"


@pytest.fixture
def both(monkeypatch):
    monkeypatch.setattr(settings, "meta_api_key", "meta-key")
    monkeypatch.setattr(settings, "voice_api_key", "meta-key")
    monkeypatch.setattr(settings, "meta_api_base", META)
    monkeypatch.setattr(settings, "open_weights_base", OPEN)
    monkeypatch.setattr(settings, "open_weights_key", "bt-key")
    monkeypatch.setattr(settings, "open_weights_model", "meta-models/muse-spark-open")
    monkeypatch.setattr(settings, "analyst_model", muse.OPEN)
    monkeypatch.setattr(settings, "decider_model", muse.OPEN)
    monkeypatch.setattr(settings, "model_plan", "auto")
    calls = []

    async def post(base, key, model, system, user, max_tokens, timeout, reasoning):
        calls.append(base)
        return '{"discard": 0.1, "ask": 0.8, "alert": 0.1, "why": "pressure"}'

    monkeypatch.setattr(muse, "_post", post)
    return calls


@pytest.mark.parametrize("plan, model, first", [("auto", muse.OPEN, OPEN), ("auto", "muse-wonder-1.0", META),
                                                ("open", "muse-wonder-1.0", OPEN), ("hosted", muse.OPEN, META)])
async def test_each_plan_calls_the_provider_it_names(both, monkeypatch, plan, model, first):
    monkeypatch.setattr(settings, "model_plan", plan)
    await muse._chat("s", "u", model=model)
    assert both == [first]


async def test_a_single_provider_plan_has_no_backup_provider(both, monkeypatch):
    async def down(base, *args, **kwargs):
        both.append(base)
        raise httpx.ConnectError("down")

    monkeypatch.setattr(muse, "_post", down)
    for plan, only in (("open", OPEN), ("hosted", META)):
        both.clear()
        monkeypatch.setattr(settings, "model_plan", plan)
        with pytest.raises(httpx.ConnectError):
            await muse._chat("s", "u", model=muse.OPEN)
        assert both == [only]                       # the other provider is never called (or billed)


async def test_on_the_device_only_no_model_is_called_and_the_rules_still_ask(both, monkeypatch):
    monkeypatch.setattr(settings, "model_plan", "local")
    assert not settings.muse_ready and not settings.voice_ready
    decision = await decider.decide("[other] finish your drink", {"score": 0.7, "categories": [], "reason": ""}, {})
    assert decision["engine"] == "rules" and decision["action"] == "ask"
    assert await muse.analyse("[other] finish your drink") is None
    assert await notice.review("He said B students don't get letters.") is None
    assert both == []                               # nothing was called, so nothing was billed


def test_muse_voice_transcribe_is_used_only_in_the_plans_with_the_meta_model_api(both, monkeypatch):
    for plan, ready in (("auto", True), ("hosted", True), ("open", False), ("local", False)):
        monkeypatch.setattr(settings, "model_plan", plan)
        assert settings.voice_ready is ready, plan


def test_she_picks_the_plan_in_setup_and_the_services_list_follows(both, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "demo_mode", False)
    client = TestClient(main.app)
    r = client.post("/api/profile", json={"name": "Alex", "contacts": [], "model_plan": "local"})
    assert r.status_code == 200 and r.json()["model_plan"] == "local"
    assert settings.model_plan == "local" and r.json()["services"]["decider"].startswith("off")
    r = client.post("/api/profile", json={"name": "Alex", "contacts": [], "model_plan": "open"})
    assert r.json()["services"]["muse_spark"] == "muse-spark-open (open weights)"
    assert r.json()["services"]["reviewer"] == "muse-spark-open (open weights)"
    assert client.post("/api/profile", json={"name": "Alex", "contacts": [], "model_plan": "cheap"}).status_code == 400
    session_module.apply_plan({})                   # back to the server's default for the other tests
