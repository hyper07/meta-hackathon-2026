"""
Stream every rendered scene through the real Watch Me agents and score them.

    uv run python -m scenarios.build          # first
    uv run python -m scenarios.evaluate       # agents as configured (Muse Spark + decision model)
    uv run python -m scenarios.evaluate --phrases-only   # baseline: phrase list and fixed rules
    uv run python -m scenarios.evaluate --hearing=script      # the agents read the scenes' scripts
    uv run python -m scenarios.evaluate --hearing=muse-whole  # ... or Muse Voice Transcribe's transcript

--hearing takes speech-to-text out of the test, to see how well the agents judge
when they read a transcript instead of hearing the room:
  script      the scene's own script, word for word, each line labelled owner or other
              from the script (perfect hearing and a perfect voice lock);
  muse-whole  Muse Voice Transcribe's transcript of the whole recording (diarization), each
              turn labelled owner or other by the real voiceprint, as audio kept offline is.
Each line is handed to the session in the 4-second chunk where it ends, so timings stay
comparable. The Analyst then reads those lines (ANALYST_STT is set to the live lines).

Each scene is fed in the same 4-second chunks the phone sends, on a simulated
clock that advances 4 s per chunk, so timings mean scene seconds, not how fast
this machine is. The owner never answers, and the check-in timer is parked, so
the first "Are you OK?" is what gets measured. Alerts are forced to dry run:
this never texts anyone, whatever is in .env.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time as real_time
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="watchme-eval-")

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

from watchme import messenger, notice, speech, store  # noqa: E402
from watchme import session as session_module  # noqa: E402
from watchme.config import settings  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT, RESULTS = HERE / "out", HERE / "results"
CHUNK = 4 * speech.SAMPLE_RATE


class SimTime:
    """Stands in for the time module inside the session and the store."""

    def __init__(self) -> None:
        self.now = real_time.time()

    def time(self) -> float:
        return self.now

    def strftime(self, fmt: str, *args) -> str:
        return real_time.strftime(fmt, args[0] if args else real_time.localtime(self.now))

    def localtime(self, seconds: float | None = None):
        return real_time.localtime(self.now if seconds is None else seconds)


class Heard(speech.Piece):
    """A transcript line with its owner match already known (--hearing modes)."""

    def __init__(self, start: float, end: float, text: str, similarity: float) -> None:
        super().__init__(start, end, text)
        self.similarity = similarity


FEED: dict = {"lines": [], "until": 0.0}   # the scene's transcript lines (absolute times), and the chunk's end


def fed_transcribe(audio, watching=True):
    """Stands in for speech.transcribe: the lines that have ended by this chunk's end, not yet handed over."""
    speech.last_engine, speech.last_error = "transcript", None
    chunk_start = FEED["until"] - audio.size / speech.SAMPLE_RATE
    due = [line for line in FEED["lines"] if line.end <= FEED["until"]]
    FEED["lines"] = [line for line in FEED["lines"] if line.end > FEED["until"]]
    return [Heard(max(0.0, line.start - chunk_start), line.end - chunk_start, line.text, line.similarity) for line in due]


def install_hearing() -> None:
    """The session asks for a voiceprint of each line; a Heard line already carries its match."""
    window, voiceprint, similarity, signature = speech.window, speech.voiceprint, speech.similarity, speech.signature
    speech.transcribe = fed_transcribe
    speech.window = lambda audio, piece, minimum=0.8: piece if isinstance(piece, Heard) and minimum else window(audio, piece, minimum)
    speech.voiceprint = lambda audio: audio if isinstance(audio, Heard) else voiceprint(audio)
    speech.similarity = lambda a, b: a.similarity if isinstance(a, Heard) else similarity(a, b)
    speech.signature = lambda p: [] if isinstance(p, Heard) else signature(p)
    settings.hold_max_s = 0          # lines arrive whole
    settings.analyst_stt = "whisper"  # the Analyst reads the lines it was given, not a fresh transcription


def transcript_lines(entry: dict, audio, hearing: str, reference) -> list[Heard]:
    if hearing == "script":
        return [Heard(l["start"], l["end"], l["text"], 0.9 if l["role"] == "owner" else 0.0) for l in entry["lines"]]
    cache = OUT / "muse-whole" / f"{entry['id']}.json"
    if cache.exists():
        turns = json.loads(cache.read_text())
    else:
        pieces = speech.transcribe_muse(audio, "DIARIZATION", timeout=120)
        turns = [{"start": p.start, "end": p.end, "text": p.text,
                  "similarity": speech.similarity(speech.voiceprint(speech.window(audio, p)), reference)} for p in pieces]
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(json.dumps(turns, indent=1))
    return [Heard(t["start"], t["end"], t["text"], t["similarity"]) for t in turns]


async def _dry_run(contacts, owner, body):
    return [{"to": c.get("name"), "channel": "dry run", "result": "dry run"} for c in contacts]


def enroll(manifest: dict) -> None:
    # On the speech thread, like every other model call (see speech.run).
    prints = [speech._worker.submit(speech.voiceprint, sf.read(OUT / name, dtype="float32")[0]).result()
              for name in manifest["enroll"]]
    mean = np.mean(prints, axis=0)
    store.save_profile({"name": "Alex", "pin": "2468", "sos_phrase": "purple elephant", "duress_phrase": "",
                        "contacts": [{"name": "Sam", "phone": "+12125550100", "email": "", "call": True}],
                        "voiceprint": (mean / np.linalg.norm(mean)).tolist(), "voice_model": speech.VOICE_MODEL})


async def run_scene(entry: dict, clock: SimTime, hearing: str | None = None) -> dict:
    audio = sf.read(OUT / f"{entry['id']}.wav", dtype="float32")[0]
    if hearing:
        reference = np.asarray(store.load_profile()["voiceprint"], dtype=np.float32)
        FEED["lines"] = sorted(await speech.run(transcript_lines, entry, audio, hearing, reference), key=lambda l: l.end)
    s = session_module.Session()
    sent: list[dict] = []

    async def send(message):
        sent.append({**message, "_t": clock.now})

    await s.attach(send)
    if entry["label"] == "notice":
        s.mode = "notice"
    start = clock.now
    for offset in range(0, len(audio), CHUNK):
        chunk = audio[offset:offset + CHUNK]
        if len(chunk) < CHUNK:
            chunk = np.pad(chunk, (0, CHUNK - len(chunk)))
        clock.now = start + (offset + CHUNK) / speech.SAMPLE_RATE   # the chunk is sent when it ends
        FEED["until"] = (offset + CHUNK) / speech.SAMPLE_RATE
        await s.on_audio((chunk * 32767).astype("<i2").tobytes())
        pending = [t for t in s._tasks if t not in (s.checkin_task, s.lost_task)]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    review = None
    if s.mode == "notice" and s.state == "watching":
        before = len(notice.read()["records"])
        await s.stop("end of scene")
        await asyncio.gather(*[t for t in s._tasks if t not in (s.checkin_task, s.lost_task)], return_exceptions=True)
        records = notice.read()["records"]
        review = records[-1]["review"] if len(records) > before else None
    for task in list(s._tasks):
        task.cancel()

    harm_line = next((l for l in entry["lines"] if l["harm_starts"]), None)
    asks = [m for m in sent if m["type"] == "checkin"]
    decisions = [m for m in sent if m["type"] == "decision"]
    segments = [m for m in sent if m["type"] in ("segment", "update")]
    events = store.read_session(s.log.id)["events"] if s.log else []
    first_ask = asks[0] if asks else None
    return {
        "id": entry["id"], "label": entry["label"], "background": entry["background"],
        "started": s.log is not None,
        "asked": bool(asks),
        "urgent": bool(first_ask and first_ask["urgent"]),
        "ask_at": round(first_ask["_t"] - start, 1) if first_ask else None,
        "harm_at": harm_line["start"] if harm_line else None,
        "delay": round(first_ask["_t"] - start - harm_line["start"], 1) if first_ask and harm_line else None,
        "max_score": max((m.get("score", 0) for m in segments), default=0),
        "decisions": [{k: d.get(k) for k in ("action", "urgent", "engine", "probabilities", "why")} for d in decisions],
        "stop_refused": any(e["kind"] == "stop_refused" for e in events),
        "transcript": [{"who": m.get("speaker"), "text": m.get("text"), "score": m.get("score")}
                       for m in sent if m["type"] == "segment"],
        "analyst": [{"seg": m["seg"], "score": m.get("score"), "reason": m.get("reason"), "heard_by": m.get("transcript_engine")}
                    for m in sent if m["type"] == "update"],
        "notice": {"match": review.get("match"), "types": sorted({m["type"] for m in review.get("moments", [])})}
                  if review else None,
    }


def summarise(rows: list[dict], mode: str) -> str:
    harm = [r for r in rows if r["label"] == "harm"]
    ok = [r for r in rows if r["label"] == "ok"]
    noticed = [r for r in rows if r["label"] == "notice"]
    caught = [r for r in harm if r["asked"]]
    needless = [r for r in ok if r["asked"]]
    delays = sorted(r["delay"] for r in caught if r["delay"] is not None)
    lines = [
        f"## {mode}",
        "",
        f"- Started by the owner's \"Watch me\": {sum(r['started'] for r in rows)} of {len(rows)}",
        f"- Harmful scenes with an \"Are you OK?\": **{len(caught)} of {len(harm)}**",
        f"- Harmless scenes with a needless check-in: **{len(needless)} of {len(ok)}**",
        f"- Seconds from the first harmful line to the check-in: median "
        f"{delays[len(delays) // 2] if delays else '–'}, worst {delays[-1] if delays else '–'} (n = {len(delays)}; 4 s chunks)",
        *([f"- Notice scenes (school, work): {sum(not r['asked'] for r in noticed)} of {len(noticed)} without a check-in; "
            "the review named " + "; ".join(f"{r['id']}: {(r['notice'] or {}).get('match', 'no review')} "
                                            f"({', '.join((r['notice'] or {}).get('types', [])) or '–'})" for r in noticed)]
          if noticed else []),
        "",
        "| scene | label | background | asked | urgent | after (s) | top score | decider |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        first = r["decisions"][0] if r["decisions"] else {}
        engine = first.get("engine", "–")
        probs = first.get("probabilities")
        if probs:
            engine += " " + "/".join(f"{probs[k]:.2f}" for k in ("discard", "ask", "alert"))
        right = r["asked"] == (r["label"] == "harm")   # notice scenes: right when nothing interrupted her
        lines.append(f"| {r['id']} | {r['label']} | {r['background']} | {'yes' if r['asked'] else 'no'}{'' if right else ' ✗'} "
                     f"| {'yes' if r['urgent'] else ''} | {r['delay'] if r['delay'] is not None else ''} "
                     f"| {r['max_score']:.2f} | {engine} |")
    return "\n".join(lines)


async def main(args: list[str]) -> None:
    phrases_only = "--phrases-only" in args
    hearing = next((a.split("=", 1)[1] for a in args if a.startswith("--hearing=")), None)
    if hearing not in (None, "script", "muse-whole"):
        raise SystemExit("--hearing is script or muse-whole")
    if hearing == "muse-whole" and not settings.voice_api_key:
        raise SystemExit("--hearing=muse-whole needs MODEL_API_KEY (or META_API_KEY)")
    only = [a for a in args if not a.startswith("--")]
    if phrases_only:
        settings.meta_api_key = None
    settings.checkin_timeout_s = settings.urgent_checkin_timeout_s = 10**6   # measure the ask, not the alert
    messenger.alert_all = _dry_run
    clock = SimTime()
    session_module.time = clock
    store.time = clock

    manifest = json.loads((OUT / "manifest.json").read_text())
    enroll(manifest)
    if hearing:
        install_hearing()
    rows = []
    for entry in manifest["scenes"]:
        if only and entry["id"] not in only:
            continue
        row = await run_scene(entry, clock, hearing)
        rows.append(row)
        print(f"{row['id']:20s} {row['label']:4s} asked={str(row['asked']):5s} delay={row['delay']} top={row['max_score']:.2f}")

    agents = f"agents: {settings.analyst_model or settings.describe()['muse_spark']} + {settings.decider_model if settings.muse_ready else 'rules'}"
    mode = "phrase list and fixed rules" if phrases_only else (
        agents if hearing else f"{agents}; live speech-to-text {settings.stt_engine}, the Analyst reads "
                               f"{settings.analyst_stt if settings.voice_api_key else 'whisper'}")
    if hearing:
        mode += {"script": "; the agents read the scenes' scripts (perfect hearing)",
                 "muse-whole": "; the agents read Muse Voice Transcribe's transcript of the whole recording"}[hearing]
    report = summarise(rows, mode)
    RESULTS.mkdir(exist_ok=True)
    stamp = real_time.strftime("%Y%m%d-%H%M")
    name = f"{stamp}-{'phrases' if phrases_only else 'agents'}{'-' + hearing if hearing else ''}"
    (RESULTS / f"{name}.json").write_text(json.dumps(rows, indent=2))
    (RESULTS / f"{name}.md").write_text(report + "\n")
    print("\n" + report)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
