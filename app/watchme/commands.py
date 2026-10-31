"""
Voice commands, matched in the transcript. Whether the *owner* said them is the
gatekeeper's job (the voiceprint); this module only finds the words.
"""

from __future__ import annotations

import re

START = re.compile(r"\bwatch me\b", re.IGNORECASE)
STOP = re.compile(r"\bstop watching( me)?\b|\bwatch me off\b", re.IGNORECASE)
IM_OK = re.compile(r"\b(i'?m|i am) (ok|okay|fine|good|alright|all right)\b|\byes,? (i'?m )?(ok|okay|fine)\b", re.IGNORECASE)
NOT_OK = re.compile(r"\b(i'?m|i am) not (ok|okay|fine)\b|\bhelp\b|\bno\b", re.IGNORECASE)


def _phrase(text: str, phrase: str | None) -> bool:
    if not phrase:
        return False
    words = r"\W+".join(re.escape(w) for w in phrase.split())
    return re.search(rf"\b{words}\b", text, re.IGNORECASE) is not None


def find(text: str, sos_phrase: str | None = None, duress_phrase: str | None = None) -> set[str]:
    """Every command present in the text: start, stop, ok, not_ok, sos, duress."""
    found: set[str] = set()
    if _phrase(text, duress_phrase):
        found.add("duress")
    if _phrase(text, sos_phrase):
        found.add("sos")
    if STOP.search(text):
        found.add("stop")
    elif START.search(text):
        found.add("start")
    if IM_OK.search(text):
        found.add("ok")
    elif NOT_OK.search(text):
        found.add("not_ok")
    return found


def strip_commands(text: str, sos_phrase: str | None = None, duress_phrase: str | None = None) -> str:
    """The transcript without command words, so "stop watching" is not scored as distress."""
    for pattern in (STOP, START):
        text = pattern.sub(" ", text)
    for phrase in (sos_phrase, duress_phrase):
        if phrase:
            words = r"\W+".join(re.escape(w) for w in phrase.split())
            text = re.sub(rf"\b{words}\b", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()
