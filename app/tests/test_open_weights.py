"""
Muse Spark Open, the open-weight model on a Modal shared endpoint, as the backup for the Meta Model API:
when a call to the Meta Model API fails, the same request goes to Muse Spark Open before any rule takes over.
"""
import httpx
import pytest

from watchme import decider, muse
from watchme.config import settings

META = "https://api.meta.ai/v1"
OPEN = "https://inference.us-west.modal.direct/v1"


@pytest.fixture
def both(monkeypatch):
    monkeypatch.setattr(settings, "meta_api_key", "meta-key")
    monkeypatch.setattr(settings, "meta_api_base", META)
    monkeypatch.setattr(settings, "open_weights_base", OPEN)
    monkeypatch.setattr(settings, "open_weights_key", "wk-id.ws-secret")
    monkeypatch.setattr(settings, "open_weights_model", "muse-spark-open.us-west.modal.direct")
    calls = []

    def fake(meta_fails_with=None, open_answer='{"discard": 0.1, "ask": 0.8, "alert": 0.1, "why": "pressure"}'):
        async def post(base, key, model, system, user, max_tokens, timeout, reasoning):
            calls.append((base, model, reasoning))
            if base == META and meta_fails_with is not None:
                raise meta_fails_with
            return open_answer if base == OPEN else '{"discard": 0.9, "ask": 0.1, "alert": 0.0, "why": "banter"}'
        monkeypatch.setattr(muse, "_post", post)
        return calls

    return fake


def http_error(status):
    request = httpx.Request("POST", META + "/chat/completions")
    return httpx.HTTPStatusError("x", request=request, response=httpx.Response(status, request=request))


async def test_the_meta_model_api_answers_when_it_can(both):
    calls = both()
    await muse._chat("s", "u", model="muse-spark-1.3")
    assert [c[0] for c in calls] == [META] and muse.answered_by.get() == "muse-spark-1.3"


@pytest.mark.parametrize("failure", [httpx.ConnectError("no network"), httpx.ReadTimeout("slow"), http_error(503),
                                     http_error(429), ValueError("empty answer")])
async def test_when_the_meta_model_api_fails_muse_spark_open_answers(both, failure):
    calls = both(meta_fails_with=failure)
    answer = await muse._chat("s", "u", model="muse-spark-1.3")
    assert [c[0] for c in calls] == [META, OPEN] and '"ask": 0.8' in answer
    assert calls[1][1] == settings.open_weights_model and calls[1][2] is False   # no Meta-only parameters
    assert muse.answered_by.get() == "muse-spark-open"


async def test_a_bad_request_is_not_hidden_by_the_backup(both):
    both(meta_fails_with=http_error(400))
    with pytest.raises(httpx.HTTPStatusError):
        await muse._chat("s", "u", model="muse-spark-1.3")


async def test_an_agent_can_run_on_muse_spark_open_directly(both):
    calls = both()
    await muse._chat("s", "u", model=muse.OPEN)
    assert [c[0] for c in calls] == [OPEN]


async def test_the_decider_says_which_model_decided(both):
    both(meta_fails_with=httpx.ConnectError("no network"))
    decision = await decider.decide("[other] finish your drink", {"score": 0.7, "categories": [], "reason": ""}, {})
    assert decision["engine"] == "muse-spark" and decision["model"] == "muse-spark-open"
    assert decision["action"] == "ask"


async def test_without_muse_spark_open_a_failure_still_falls_back_to_the_rules(both, monkeypatch):
    both(meta_fails_with=httpx.ConnectError("no network"))
    monkeypatch.setattr(settings, "open_weights_key", None)
    decision = await decider.decide("[other] finish your drink", {"score": 0.7, "categories": [], "reason": ""}, {})
    assert decision["engine"] == "rules" and decision["action"] == "ask"
