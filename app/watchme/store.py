"""
The owner's profile and the evidence log.

Each Watch Me session is a folder:

    data/sessions/<id>/log.jsonl    append-only; every line carries the hash of the one before it
    data/sessions/<id>/clips/*.wav  audio of flagged moments (only where the recording rule allows)

Nothing is edited in place. When an agent revises a segment's score, it appends
an "update" line; the review screen folds updates onto their segments. So the
chain shows if anyone changes or deletes a line afterwards, the same
verify-by-hash idea as Knowledge-Addressed Transport.
"""

from __future__ import annotations

import hashlib
import io
import json
import time
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf

from .config import settings

GENESIS = "0" * 64


def _sessions_dir() -> Path:
    path = settings.data_dir / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


# ── profile ──────────────────────────────────────────────────────────────────

def profile_path() -> Path:
    return settings.data_dir / "profile.json"


def load_profile() -> dict:
    from .speech import VOICE_MODEL

    path = profile_path()
    if not path.exists():
        return {"name": "", "contacts": [], "sos_phrase": "", "duress_phrase": "", "pin": "", "voiceprint": None}
    profile = json.loads(path.read_text())
    if profile.get("voiceprint") and profile.get("voice_model") != VOICE_MODEL:
        # A print from another model can't be compared with this one's: ask for a new recording.
        profile["voiceprint"], profile["needs_reenroll"] = None, True
    return profile


def save_profile(profile: dict) -> None:
    profile_path().write_text(json.dumps(profile, indent=2))


def voice_id(voiceprint: list[float]) -> str:
    """A short name for an enrolled voiceprint: the start of its SHA-256."""
    return hashlib.sha256(np.asarray(voiceprint, dtype=np.float32).tobytes()).hexdigest()[:12]


def public_profile(profile: dict) -> dict:
    """What the browser may see: not the PIN, and not the voiceprint, only a coarse picture of it."""
    from .speech import signature

    out = {k: v for k, v in profile.items() if k not in ("voiceprint", "pin")}
    out["enrolled"] = bool(profile.get("voiceprint"))
    out["has_pin"] = bool(profile.get("pin"))
    if out["enrolled"]:
        out["voice_id"] = voice_id(profile["voiceprint"])
        out["voice_signature"] = signature(np.asarray(profile["voiceprint"], dtype=np.float32))
    return out


# ── evidence log ─────────────────────────────────────────────────────────────

def _digest(record: dict) -> str:
    body = json.dumps({k: v for k, v in record.items() if k != "hash"}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(body.encode()).hexdigest()


class EvidenceLog:
    def __init__(self, session_id: str | None = None, folder: Path | None = None):
        """A session's log, or, with folder, any other hash-chained log (the notice book)."""
        self.id = session_id or time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.dir = folder or _sessions_dir() / self.id
        (self.dir / "clips").mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "log.jsonl"
        self.last_hash = GENESIS
        if self.path.exists():
            lines = self.path.read_text().splitlines()
            if lines:
                self.last_hash = json.loads(lines[-1])["hash"]

    def append(self, kind: str, **fields) -> dict:
        # Both the epoch time and a readable local time, so the record reads as a dated log on its own.
        now = time.time()
        record = {"kind": kind, "t": round(now, 3), "at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
                  **fields, "prev": self.last_hash}
        record["hash"] = _digest(record)
        with self.path.open("a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.last_hash = record["hash"]
        return record

    def save_clip(self, name: str, audio: np.ndarray, sample_rate: int = 16_000) -> dict:
        buffer = io.BytesIO()
        sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
        data = buffer.getvalue()
        (self.dir / "clips" / name).write_bytes(data)
        return {"file": name, "sha256": hashlib.sha256(data).hexdigest(), "seconds": round(len(audio) / sample_rate, 1)}


# ── work waiting for the network ─────────────────────────────────────────────
# When the model API can't be reached, the analysis is queued here with its transcript and time, and
# done when the connection is back. The audio and the transcript are already on disk by then.

def pending_path() -> Path:
    return settings.data_dir / "pending.jsonl"


def read_pending() -> list[dict]:
    path = pending_path()
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def write_pending(items: list[dict]) -> None:
    pending_path().write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items))


def queue_pending(**item) -> dict:
    now = time.time()
    item = {"id": uuid.uuid4().hex[:10], "queued_t": round(now, 3),
            "queued_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)), **item}
    with pending_path().open("a") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item


def list_sessions() -> list[dict]:
    out = []
    for folder in sorted(_sessions_dir().iterdir(), reverse=True):
        log = folder / "log.jsonl"
        if not log.exists():
            continue
        records = [json.loads(line) for line in log.read_text().splitlines()]
        segments = fold(records)["segments"]
        worst = max((s.get("score", 0) for s in segments), default=0)
        out.append({
            "id": folder.name,
            "started": records[0]["t"] if records else None,
            "segments": len(segments),
            "flagged": sum(1 for s in segments if s.get("level", "none") != "none"),
            "alerts": sum(1 for r in records if r["kind"] == "alert"),
            "worst": worst,
        })
    return out


def read_session(session_id: str) -> dict:
    log = _sessions_dir() / session_id / "log.jsonl"
    records = [json.loads(line) for line in log.read_text().splitlines()]
    return {"id": session_id, **fold(records), "chain": verify(records)}


def fold(records: list[dict]) -> dict:
    """Segments with their latest revision applied, plus the session's events in order."""
    segments: dict[str, dict] = {}
    events = []
    for record in records:
        if record["kind"] == "segment":
            segments[record["seg"]] = dict(record)
        elif record["kind"] == "update" and record.get("seg") in segments:
            segments[record["seg"]].update({k: v for k, v in record.items() if k not in ("kind", "t", "prev", "hash")})
            segments[record["seg"]].setdefault("revisions", 0)
            segments[record["seg"]]["revisions"] += 1
        else:
            events.append(record)
    return {"segments": list(segments.values()), "events": events}


def verify(records: list[dict]) -> dict:
    """Recompute every hash. Any edit, insertion or deletion breaks the chain at that line."""
    previous = GENESIS
    for number, record in enumerate(records, start=1):
        if record.get("prev") != previous or _digest(record) != record.get("hash"):
            return {"ok": False, "broken_at": number, "lines": len(records)}
        previous = record["hash"]
    return {"ok": True, "lines": len(records), "head": previous}


def clip_path(session_id: str, name: str) -> Path:
    path = (_sessions_dir() / session_id / "clips" / name).resolve()
    if _sessions_dir().resolve() not in path.parents:
        raise ValueError("bad clip path")
    return path
