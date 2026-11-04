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
    assert calls[1][1] == settings.open_weights_model and calls[1][2] is True    # the same low reasoning effort
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


# ── Muse Spark Open first, the hosted models as its backup ──────────────────

@pytest.fixture
def open_first(both, monkeypatch):
    monkeypatch.setattr(settings, "analyst_model", muse.OPEN)
    monkeypatch.setattr(settings, "decider_model", muse.OPEN)
    monkeypatch.setattr(settings, "decider_hosted_model", "muse-spark-1.1")
    return both


async def test_open_first_answers_on_muse_spark_open(open_first):
    calls = open_first()
    decision = await decider.decide("[other] finish your drink", {"score": 0.7, "categories": [], "reason": ""}, {})
    assert [c[0] for c in calls] == [OPEN] and decision["model"] == "muse-spark-open"


@pytest.mark.parametrize("failure", [httpx.ConnectError("down"), httpx.ReadTimeout("slow"), ValueError("cut off")])
async def test_when_muse_spark_open_fails_the_hosted_model_answers(open_first, monkeypatch, failure):
    calls = []

    async def post(base, key, model, system, user, max_tokens, timeout, reasoning):
        calls.append((base, model))
        if base == OPEN:
            raise failure
        return '{"discard": 0.1, "ask": 0.8, "alert": 0.1, "why": "pressure"}'

    monkeypatch.setattr(muse, "_post", post)
    decision = await decider.decide("[other] finish your drink", {"score": 0.7, "categories": [], "reason": ""}, {})
    assert calls == [(OPEN, settings.open_weights_model), (META, "muse-spark-1.1")]   # the Decider's own hosted model
    assert decision["engine"] == "muse-spark" and decision["model"] == "muse-spark-1.1" and decision["action"] == "ask"


async def test_a_cut_off_answer_counts_as_a_failure(monkeypatch):
    def reply(request):
        return httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {"content": '{"score": 0.'}}]})
    real = httpx.AsyncClient
    monkeypatch.setattr(muse.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(reply), **kw))
    with pytest.raises(ValueError, match="cut off"):
        await muse._post(OPEN, "k", "m", "s", "u", 100, 5, reasoning=True)


def test_the_live_agents_run_on_open_weights_only_when_a_key_is_set(monkeypatch):
    from watchme.config import Settings

    for name in ("OPEN_WEIGHTS_API_KEY", "BASETEN_API_KEY", "MODAL_PROXY_TOKEN", "ANALYST_MODEL", "DECIDER_MODEL", "WRITER_MODEL"):
        monkeypatch.delenv(name, raising=False)
    hosted = Settings()
    assert (hosted.analyst_model, hosted.decider_model, hosted.writer_model) == ("", "muse-spark-1.1", "")
    monkeypatch.setenv("BASETEN_API_KEY", "bt-test")
    first = Settings()
    assert (first.analyst_model, first.decider_model, first.writer_model) == ("open", "open", "open")
    assert first.reviewer_model == "muse-wonder-1.0"          # Notice stays on Muse Wonder (40/40 against 38/40)
