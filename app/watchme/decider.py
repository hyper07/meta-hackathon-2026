"""
The Decider: one of three actions, in about a second, from a fixed menu.

Jev (TypeSafe's hosted "System One" model) or Kev (its open-weights family,
local or on Modal) answers `POST /v1/systemone` with a probability for every
option, the same client shape as the Deterrence commanders. Then the rules
below, not the model, pick the action. The Deterrence rule was "hold when
unsure"; here it is "ask when unsure":

  * discard  only when its probability is at least MIN_LIFT x a blind guess
             (2.5 of 3 options = 0.83). Uncertainty never discards.
  * ask      everything else: "Are you OK?" with the normal timeout.
  * alert    from the model becomes an *urgent* ask, with a shorter timeout.
             The app alerts without asking only on the owner's SOS or duress
             phrase, and otherwise only when an ask goes unanswered.

A needless "Are you OK?" costs the owner a tap; a missed emergency costs far more.
Without a Jev endpoint the same rules run on the Analyst's score alone.
"""

from __future__ import annotations

import time

import httpx

from .config import settings

OPTIONS = ("discard", "ask", "alert")

INSTRUCTIONS = (
    "The owner switched on a personal safety mode. Given what their phone just heard, choose: "
    "discard (nothing wrong, forget it), ask (check privately whether they are OK), or alert "
    "(they may be in danger right now). Missing real danger is the worst outcome; a needless "
    "check costs the owner one tap."
)


def build_request(transcript: str, analysis: dict, context: dict) -> dict:
    state = {
        "context": "\n".join(f"{k}: {v}" for k, v in context.items()),
        "analyst": (
            f"score {analysis.get('score', 0):.2f}; categories {', '.join(analysis.get('categories') or []) or 'none'}; "
            f"{analysis.get('reason') or ''}"
        ),
        "transcript (last minute, oldest first)": transcript,
    }
    return {
        "state": state,
        "questions": {
            "action": {"type": "choice", "instructions": INSTRUCTIONS, "criteria": {o: None for o in OPTIONS}},
            "in_danger": {"type": "noul", "instructions": "Is the owner in danger right now?"},
        },
    }


def apply_rules(probabilities: dict[str, float]) -> tuple[str, bool, str]:
    """(action, urgent, why) from the model's distribution. The rules, not the argmax, decide."""
    bar = settings.jev_min_lift / len(OPTIONS)
    p_discard = float(probabilities.get("discard", 0))
    p_alert = float(probabilities.get("alert", 0))
    top = max(OPTIONS, key=lambda o: probabilities.get(o, 0))
    if top == "discard" and p_discard >= bar:
        return "discard", False, f"discard at p={p_discard:.2f} (bar {bar:.2f})"
    if top == "alert":
        return "ask", True, f"alert at p={p_alert:.2f} -> urgent ask; alerts need a missed answer or an SOS"
    if top == "discard":
        return "ask", False, f"unsure: discard only p={p_discard:.2f}, needs {bar:.2f}"
    return "ask", False, f"ask at p={probabilities.get('ask', 0):.2f}"


def rules_only(score: float) -> tuple[str, bool, str]:
    """No Jev: the Analyst's score alone, through the same thresholds as the colour bands."""
    if score >= 0.7:
        return "ask", True, f"score {score:.2f} >= 0.70 -> urgent ask (rules only, Jev not configured)"
    if score >= settings.trigger_score:
        return "ask", False, f"score {score:.2f} >= {settings.trigger_score:.2f} -> ask (rules only)"
    return "discard", False, f"score {score:.2f} below trigger (rules only)"


async def decide(transcript: str, analysis: dict, context: dict) -> dict:
    started = time.perf_counter()
    if not settings.jev_ready:
        action, urgent, why = rules_only(float(analysis.get("score", 0)))
        return {"action": action, "urgent": urgent, "why": why, "engine": "rules", "ms": 0}
    url = settings.jev_base_url.rstrip("/")
    for suffix in ("/v1/systemone", "/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    try:
        async with httpx.AsyncClient(timeout=settings.jev_timeout) as client:
            response = await client.post(
                url + "/v1/systemone",
                headers={"Authorization": f"Bearer {settings.jev_api_key}"},
                json={**build_request(transcript, analysis, context), "model": settings.jev_model},
            )
            response.raise_for_status()
            answers = response.json().get("answers") or {}
        probabilities = (answers.get("action") or {}).get("probabilities") or {}
        if not any(o in probabilities for o in OPTIONS):
            raise ValueError(f"no menu option in answer: {answers.get('action')!r}")
        action, urgent, why = apply_rules(probabilities)
        return {
            "action": action, "urgent": urgent, "why": why, "engine": "jev",
            "probabilities": {o: round(float(probabilities.get(o, 0)), 3) for o in OPTIONS},
            "in_danger": (answers.get("in_danger") or {}).get("noul"),
            "ms": round((time.perf_counter() - started) * 1000),
        }
    except Exception as error:
        # A dead link must never mean "discard": fall back to the rules, which ask on any trigger.
        action, urgent, why = rules_only(max(float(analysis.get("score", 0)), settings.trigger_score))
        return {"action": action, "urgent": urgent, "why": f"Jev failed ({type(error).__name__}); {why}",
                "engine": "rules", "ms": round((time.perf_counter() - started) * 1000)}
