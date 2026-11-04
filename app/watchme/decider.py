"""
The Decider: one of three actions, from a fixed menu.

Muse Spark (Meta Model API, DECIDER_MODEL) gives a probability for every option, as JSON.
Then the rules below, not the model, pick the action: "ask when unsure".

  * discard  only when its probability is at least MIN_LIFT x a blind guess
             (2.5 of 3 options = 0.83). Uncertainty never discards.
  * ask      everything else: "Are you OK?" with the normal timeout.
  * alert    from the model becomes an *urgent* ask, with a shorter timeout.
             The app alerts without asking only on the owner's SOS or duress
             phrase, and otherwise only when an ask goes unanswered.

A needless "Are you OK?" costs the owner a tap; a missed emergency costs far more.
Without a Meta key, or when the call fails, the rules run on the Analyst's score alone.
"""

from __future__ import annotations

import json
import time

from . import muse
from .config import settings

OPTIONS = ("discard", "ask", "alert")

INSTRUCTIONS = (
    "The owner switched on a personal safety mode. Given what their phone just heard, choose: "
    "discard (nothing wrong, forget it), ask (check privately whether they are OK), or alert "
    "(they may be in danger right now). Missing real danger is the worst outcome; a needless "
    "check costs the owner one tap."
)

PROMPT = INSTRUCTIONS + """

You get the context, the Analyst's reading and the transcript. Give a probability for each option,
honest about uncertainty, summing to 1. Answer with JSON only:
{"discard": 0.0-1.0, "ask": 0.0-1.0, "alert": 0.0-1.0, "in_danger": "yes|no|unclear", "why": "one short sentence"}"""


def build_state(transcript: str, analysis: dict, context: dict) -> dict:
    return {
        "context": "\n".join(f"{k}: {v}" for k, v in context.items()),
        "analyst": (
            f"score {analysis.get('score', 0):.2f}; categories {', '.join(analysis.get('categories') or []) or 'none'}; "
            f"{analysis.get('reason') or ''}"
        ),
        "transcript (last minute, oldest first)": transcript,
    }


def apply_rules(probabilities: dict[str, float]) -> tuple[str, bool, str]:
    """(action, urgent, why) from the model's distribution. The rules, not the argmax, decide."""
    bar = settings.decider_min_lift / len(OPTIONS)
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
    """No Muse Spark: the Analyst's score alone, through the same thresholds as the colour bands."""
    if score >= 0.7:
        return "ask", True, f"score {score:.2f} >= 0.70 -> urgent ask (rules only)"
    if score >= settings.trigger_score:
        return "ask", False, f"score {score:.2f} >= {settings.trigger_score:.2f} -> ask (rules only)"
    return "discard", False, f"score {score:.2f} below trigger (rules only)"


async def decide_with_muse(transcript: str, analysis: dict, context: dict, started: float) -> dict:
    state = build_state(transcript, analysis, context)
    answer = muse._first_json(await muse._chat(
        PROMPT, "\n\n".join(f"{k}:\n{v}" for k, v in state.items()),
        max_tokens=1200, timeout=settings.decider_timeout, model=settings.decider_model,
        hosted=settings.decider_hosted_model))
    raw = {o: max(0.0, float(answer.get(o, 0) or 0)) for o in OPTIONS}
    total = sum(raw.values())
    if total <= 0:
        raise ValueError(f"no probabilities in answer: {json.dumps(answer)[:120]}")
    probabilities = {o: raw[o] / total for o in OPTIONS}
    action, urgent, why = apply_rules(probabilities)
    return {
        "action": action, "urgent": urgent, "why": f"{why}; {str(answer.get('why', ''))[:120]}".rstrip("; "),
        "engine": "muse-spark", "model": muse.answered_by.get(),
        "probabilities": {o: round(p, 3) for o, p in probabilities.items()},
        "in_danger": answer.get("in_danger"), "ms": round((time.perf_counter() - started) * 1000),
    }


async def decide(transcript: str, analysis: dict, context: dict) -> dict:
    started = time.perf_counter()
    if not settings.muse_ready:
        action, urgent, why = rules_only(float(analysis.get("score", 0)))
        return {"action": action, "urgent": urgent, "why": why, "engine": "rules", "ms": 0}
    try:
        return await decide_with_muse(transcript, analysis, context, started)
    except Exception as error:
        # A failed call must never mean "discard": fall back to the rules, which ask on any trigger.
        action, urgent, why = rules_only(max(float(analysis.get("score", 0)), settings.trigger_score))
        return {"action": action, "urgent": urgent, "why": f"Muse Spark failed ({type(error).__name__}); {why}",
                "engine": "rules", "ms": round((time.perf_counter() - started) * 1000)}
