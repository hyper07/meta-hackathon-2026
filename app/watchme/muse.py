"""
Muse Spark through the Meta Model API: the slow, careful agents.

  analyse()      the Analyst: reads the last minute of transcript, names the
                 categories, quotes the exact words, scores 0 to 1
  write_alert()  the Messenger: one calm text for the owner's contacts
  summarise()    the Reviewer: a short account of a session for the owner

The API speaks OpenAI-style Chat Completions at https://api.meta.ai/v1
(Meta's "Build with Muse Spark" post; the legal-agent-workshop uses the same
base URL with muse-spark-1.3). Every call has a fallback, so a missing
key or a slow network never stops the safety loop.
"""

from __future__ import annotations

import json
import re
import time

import httpx

from .config import settings
from .lexicon import CATEGORIES

ANALYST_PROMPT = f"""You are the Analyst in a personal safety app the user switched on for themselves.
You read a transcript of what the user's phone heard in the last minute. Lines are tagged
[owner] (the user) or [other] (anyone else). Speech-to-text makes mistakes.

Judge whether harassment, sexual harassment, coercion, threats, drugging or incapacitation,
or isolation of the owner is happening. Banter, flirting both people welcome, music lyrics,
TV and talk about other people's experiences are not incidents.

Answer with JSON only:
{{"score": 0.0-1.0, "categories": [subset of {list(CATEGORIES)}],
  "quotes": [exact words copied from the transcript], "reason": "one short sentence"}}

score: 0 nothing wrong; 0.2 worth a note; 0.45 the owner should be asked if they are OK;
0.7+ looks like it is happening now. Quote only words that appear in the transcript."""

ALERT_PROMPT = """You write one SMS for a personal safety app. The user chose these contacts in
advance and asked to be alerted when they do not answer a safety check. Write at most 320
characters: who, that they did not answer, when, what was heard in plain words, and what to do
(call them; if no answer, call 911). The app adds the location link on its own line after your
text: never write a link, an address or coordinates. Calm, factual, no speculation about what
happened to them. Plain text only."""

SUMMARY_PROMPT = """You summarise a Watch Me session for the person who switched it on. Use their
own transcript and flags. Five sentences at most, in plain words: when it ran, the moments the
app marked and why, and anything an alert was sent for. Do not tell them what "really"
happened, do not diagnose, and do not use alarming language. If nothing was marked, say so."""


async def _chat(system: str, user: str, max_tokens: int = 1500, timeout: float = 20, model: str = "") -> str:
    # max_tokens covers the model's reasoning as well as its answer; too small and the answer is empty.
    body = {
        "model": model or settings.meta_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    if settings.reasoning_effort:
        body["reasoning_effort"] = settings.reasoning_effort
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            settings.meta_api_base.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {settings.meta_api_key}"},
            json=body,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"].get("content")
        if not content:
            raise ValueError("the model used its whole budget reasoning and gave no answer")
        return content.strip()


def retryable(error: Exception) -> bool:
    """A failure worth queuing for later: no network, a timeout, or the service being busy or down."""
    if isinstance(error, httpx.TransportError):           # connect errors and timeouts included
        return True
    return isinstance(error, httpx.HTTPStatusError) and (error.response.status_code == 429 or error.response.status_code >= 500)


_online: tuple[float, bool] = (0.0, False)


async def online(max_age: float = 20.0) -> bool:
    """Can the model API be reached right now? Cached briefly so the catch-up loop doesn't hammer it."""
    global _online
    if time.time() - _online[0] < max_age:
        return _online[1]
    ok = False
    if settings.muse_ready:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(settings.meta_api_base.rstrip("/") + "/models",
                                            headers={"Authorization": f"Bearer {settings.meta_api_key}"})
                ok = response.status_code < 500
        except httpx.HTTPError:
            ok = False
    _online = (time.time(), ok)
    return ok


def _first_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON in answer: {text[:120]!r}")
    return json.loads(match.group(0))


async def analyse(transcript: str) -> dict | None:
    """None when Muse Spark is not configured or failed; the caller keeps the phrase-list score."""
    if not settings.muse_ready:
        return None
    try:
        answer = _first_json(await _chat(ANALYST_PROMPT, transcript, model=settings.analyst_model))
    except Exception as error:
        return {"error": f"{type(error).__name__}: {error}", "retry": retryable(error)}
    plain = re.sub(r"^\[\w+\]\s*", "", transcript, flags=re.MULTILINE).lower()
    return {
        "score": max(0.0, min(1.0, float(answer.get("score", 0)))),
        "categories": [c for c in answer.get("categories", []) if c in CATEGORIES],
        # A quote the model cannot point to in the transcript is dropped, not shown.
        "quotes": [q for q in answer.get("quotes", []) if isinstance(q, str) and q.lower().strip() in plain],
        "reason": str(answer.get("reason", ""))[:300],
    }


def _alert_fallback(facts: dict) -> str:
    heard = f" Heard: \"{facts['heard'].rstrip('.!?')}\"." if facts.get("heard") else ""
    return (
        f"Watch Me alert for {facts['name']}: {facts['why']} at {facts['time']}.{heard} "
        f"Please call {facts['name']} now. If you can't reach them, call 911."
    )[:480]


async def write_alert(facts: dict) -> str:
    if not settings.muse_ready:
        return _alert_fallback(facts)
    try:
        text = await _chat(ALERT_PROMPT, json.dumps(facts), max_tokens=1200, timeout=10, model=settings.writer_model)
        return text[:480] or _alert_fallback(facts)
    except Exception:
        return _alert_fallback(facts)


async def summarise(session: dict) -> str:
    marked = [s for s in session["segments"] if s.get("level", "none") != "none"]
    if not settings.muse_ready:
        if not marked:
            return f"{len(session['segments'])} moments transcribed; nothing was marked."
        worst = max(marked, key=lambda s: s.get("score", 0))
        return (f"{len(session['segments'])} moments transcribed, {len(marked)} marked for review. "
                f"The highest-scored moment: \"{worst.get('text', '')[:120]}\".")
    lines = [
        {"time": s["t"], "who": s.get("speaker"), "text": s.get("text"), "level": s.get("level"),
         "reason": s.get("reason")}
        for s in session["segments"]
    ]
    events = [{"time": e["t"], "kind": e["kind"], "detail": e.get("detail") or e.get("action")} for e in session["events"]]
    try:
        return await _chat(SUMMARY_PROMPT, json.dumps({"segments": lines[-200:], "events": events[-50:]}), max_tokens=2500,
                           timeout=40, model=settings.writer_model)
    except Exception as error:
        return f"Summary unavailable ({type(error).__name__}). {len(marked)} moments were marked."
