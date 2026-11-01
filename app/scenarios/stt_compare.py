"""
Speech-to-text head to head: Whisper on this machine against Muse Voice Transcribe (Meta Model API),
on the same 22 scene recordings (synthetic voices over party, bar, street and TV noise).

Two ways the app uses speech-to-text, so two tests:
  * live:   4-second chunks, as the phone sends them;
  * whole:  the whole recording at once, as when audio kept offline is transcribed later.

For each: word error rate against the scene's script (lower is better), how often the owner's
"Watch me" is heard, how many harmful lines' words are heard, and the time per request.

    uv run python -m scenarios.stt_compare           -> results/<stamp>-stt.md and .json
"""
from __future__ import annotations

import json
import re
import statistics
import sys
import time
from pathlib import Path

import soundfile as sf

from watchme import speech
from watchme.config import settings

HERE = Path(__file__).resolve().parent
OUT, RESULTS = HERE / "out", HERE / "results"
CHUNK = 4 * speech.SAMPLE_RATE

ONES = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                   "fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * i for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split(), 2)}


def words(text: str) -> list[str]:
    text = text.lower().replace("’", "'").replace("'", "")
    return [str(ONES.get(w, TENS.get(w, w))) for w in re.findall(r"[a-z0-9]+", text)]


def edits(ref: list[str], hyp: list[str]) -> int:
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
    return d[-1]


def recall(line: str, heard: list[str]) -> float:
    """Share of a line's words that appear in what was heard (order ignored)."""
    want = words(line)
    pool = list(heard)
    hit = 0
    for w in want:
        if w in pool:
            pool.remove(w)
            hit += 1
    return hit / max(1, len(want))


ENGINES = {
    "whisper": lambda audio: speech.transcribe_whisper(audio),
    "muse": lambda audio: speech.transcribe_muse(audio, timeout=60),
}


def run(engine: str, audio, chunked: bool) -> tuple[str, list[float], int]:
    pieces_text, seconds, errors = [], [], 0
    parts = [audio[i:i + CHUNK] for i in range(0, len(audio), CHUNK)] if chunked else [audio]
    for part in parts:
        if len(part) < speech.SAMPLE_RATE // 2:
            continue
        started = time.perf_counter()
        try:
            pieces = ENGINES[engine](part)
        except Exception as error:
            errors += 1
            print(f"   {engine}: {type(error).__name__} {str(error)[:80]}", flush=True)
            pieces = []
        seconds.append(time.perf_counter() - started)
        pieces_text.extend(p.text for p in pieces)
    return " ".join(pieces_text), seconds, errors


def main(args: list[str]) -> None:
    if not settings.voice_api_key:
        raise SystemExit("needs MODEL_API_KEY (or META_API_KEY) for Muse Voice Transcribe")
    manifest = json.loads((OUT / "manifest.json").read_text())
    speech.warm_up()
    rows = []
    for scene in manifest["scenes"]:
        if args and scene["id"] not in args:
            continue
        audio, _ = sf.read(OUT / f"{scene['id']}.wav", dtype="float32")
        reference = " ".join(line["text"] for line in scene["lines"])
        harmful = [line["text"] for line in scene["lines"] if line.get("harm_starts")] or []
        row = {"id": scene["id"], "background": scene["background"]}
        for engine in ENGINES:
            for mode, chunked in (("live", True), ("whole", False)):
                text, seconds, errors = run(engine, audio, chunked)
                heard = words(text)
                row[f"{engine}_{mode}"] = {
                    "text": text, "wer": edits(words(reference), heard) / max(1, len(words(reference))),
                    "watch_me": "watch me" in " ".join(heard),
                    "harm_recall": statistics.mean(recall(h, heard) for h in harmful) if harmful else None,
                    "seconds": seconds, "errors": errors,
                }
        rows.append(row)
        print(f"{scene['id']:20s} " + "  ".join(f"{k}: wer {row[k]['wer']:.2f}" for k in row if "_" in k), flush=True)

    RESULTS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M")
    (RESULTS / f"{stamp}-stt.json").write_text(json.dumps(rows, indent=2))
    report = summarise(rows)
    (RESULTS / f"{stamp}-stt.md").write_text(report + "\n")
    print("\n" + report)


def summarise(rows: list[dict]) -> str:
    def col(key):
        values = [r[key] for r in rows]
        wers = [v["wer"] for v in values]
        times = sorted(t for v in values for t in v["seconds"])
        harm = [v["harm_recall"] for v in values if v["harm_recall"] is not None]
        return (f"{statistics.mean(wers) * 100:.1f}%", f"{statistics.median(wers) * 100:.1f}%",
                f"{sum(v['watch_me'] for v in values)} of {len(values)}",
                f"{statistics.mean(harm) * 100:.0f}%" if harm else "–",
                f"{statistics.median(times):.2f} s / {times[int(0.9 * (len(times) - 1))]:.2f} s",
                str(sum(v["errors"] for v in values)))

    keys = [("whisper_live", "Whisper base (this machine), 4 s chunks"), ("muse_live", "Muse Voice Transcribe, 4 s chunks"),
            ("whisper_whole", "Whisper base, whole recording"), ("muse_whole", "Muse Voice Transcribe, whole recording")]
    lines = [f"## Speech-to-text: Whisper on this machine vs Muse Voice Transcribe ({len(rows)} scenes)", "",
             "| | word error rate (mean) | (median) | \"Watch me\" heard | harmful lines' words heard | time per request (median / 90th pct) | failed requests |",
             "|---|---|---|---|---|---|---|"]
    for key, name in keys:
        lines.append(f"| {name} | " + " | ".join(col(key)) + " |")
    lines += ["", "By background noise (word error rate, mean, 4 s chunks):", "",
              "| background | scenes | Whisper | Muse |", "|---|---|---|---|"]
    for bg in sorted({r["background"] for r in rows}):
        group = [r for r in rows if r["background"] == bg]
        lines.append(f"| {bg} | {len(group)} | {statistics.mean(r['whisper_live']['wer'] for r in group) * 100:.1f}% "
                     f"| {statistics.mean(r['muse_live']['wer'] for r in group) * 100:.1f}% |")
    return "\n".join(lines)


if __name__ == "__main__":
    main(sys.argv[1:])
