"""
The instant first pass: phrases that suggest harassment, coercion, threats or
drugging, each with a category and a weight. It runs on every transcribed chunk
in under a millisecond, decides whether the slower agents are worth waking, and
is the whole analysis when no model is configured.

A starting list, not a vetted one. Refine the phrases and weights with
advocates; every hit is shown to the owner with the exact words, so a bad entry
is visible rather than silent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

CATEGORIES = (
    "distress",            # the owner, or anyone, asking for it to stop
    "sexual_harassment",
    "coercion",
    "threat",
    "incapacitation",      # drugging or someone unable to respond
    "isolation",           # separating someone from their friends
)

# (pattern, category, weight). Patterns are matched case-insensitively on word boundaries.
PHRASES: list[tuple[str, str, float]] = [
    # distress
    (r"get off (of )?me", "distress", 0.8),
    (r"don'?t touch me", "distress", 0.8),
    (r"stop touching( me)?", "distress", 0.8),
    (r"leave me alone", "distress", 0.6),
    (r"help me", "distress", 0.7),
    (r"somebody help|someone help", "distress", 0.8),
    (r"i (don'?t|do not) want (to|this)", "distress", 0.6),
    (r"let me go", "distress", 0.7),
    (r"you'?re hurting me", "distress", 0.9),
    (r"no,? stop|stop,? no|please stop", "distress", 0.6),
    (r"help", "distress", 0.4),
    (r"stop", "distress", 0.25),
    # sexual harassment
    (r"sit on my lap", "sexual_harassment", 0.5),
    (r"show me your (body|tits|boobs|ass)", "sexual_harassment", 0.6),
    (r"send (me )?nudes", "sexual_harassment", 0.5),
    (r"nice (ass|tits|boobs)", "sexual_harassment", 0.5),
    (r"take (it|your \w+) off", "sexual_harassment", 0.5),
    (r"you know you want (it|this|me)", "sexual_harassment", 0.7),
    (r"you were asking for it", "sexual_harassment", 0.7),
    # coercion
    (r"don'?t tell anyone", "coercion", 0.6),
    (r"nobody will believe you", "coercion", 0.8),
    (r"no one will believe you", "coercion", 0.8),
    (r"you owe me", "coercion", 0.5),
    (r"just relax", "coercion", 0.3),
    (r"stop being (a )?(tease|prude|baby)", "coercion", 0.5),
    # threat
    (r"i'?ll (kill|hurt) you", "threat", 0.9),
    (r"or else", "threat", 0.4),
    (r"shut (the fuck )?up", "threat", 0.35),
    (r"you'?ll regret", "threat", 0.6),
    # incapacitation
    (r"(she|he)'?s (passed|blacked) out", "incapacitation", 0.8),
    (r"(she|he)'?s out cold", "incapacitation", 0.8),
    (r"(she|he) won'?t remember", "incapacitation", 0.9),
    (r"finish (your|the) drink", "incapacitation", 0.4),
    (r"drink this", "incapacitation", 0.4),
    (r"i can'?t (feel my|move|stand)", "incapacitation", 0.7),
    (r"what did you put in", "incapacitation", 0.8),
    (r"i feel (really )?(dizzy|weird|sick)", "incapacitation", 0.4),
    # isolation
    (r"come (upstairs|to my room|with me) (alone|now)", "isolation", 0.4),
    (r"your friends? (left|went home)", "isolation", 0.4),
    (r"lock the door", "isolation", 0.5),
]

_COMPILED = [(re.compile(rf"\b(?:{p})\b", re.IGNORECASE), c, w) for p, c, w in PHRASES]


@dataclass
class Hit:
    phrase: str      # the words as they appear in the transcript
    category: str
    weight: float


def scan(text: str) -> list[Hit]:
    """Every phrase found, longest-match first, without counting the same words twice."""
    hits: list[Hit] = []
    taken: list[tuple[int, int]] = []
    for pattern, category, weight in sorted(_COMPILED, key=lambda c: -c[2]):
        for match in pattern.finditer(text):
            span = match.span()
            if any(span[0] < end and start < span[1] for start, end in taken):
                continue
            taken.append(span)
            hits.append(Hit(match.group(0), category, weight))
    return hits


def score(hits: list[Hit], loud: bool = False) -> float:
    """The strongest hit, plus a little for each further one and for a loud sound. 0 to 1."""
    if not hits and not loud:
        return 0.0
    weights = sorted((h.weight for h in hits), reverse=True)
    value = (weights[0] if weights else 0.0) + 0.1 * len(weights[1:]) + (0.15 if loud else 0.0)
    return round(min(1.0, value), 3)


def level(value: float) -> str:
    """The colour band the review screen shows."""
    if value >= 0.7:
        return "urgent"
    if value >= 0.45:
        return "concern"
    if value >= 0.2:
        return "watch"
    return "none"
