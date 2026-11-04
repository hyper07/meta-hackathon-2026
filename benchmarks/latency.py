"""
Latency of each stage of Watch Me's pipeline, measured with the app's own code on the test scenes.

    cd app && uv run python ../benchmarks/latency.py            # 20 runs of each Meta Model API stage
    cd app && uv run python ../benchmarks/latency.py --runs=5   # quicker
    cd app && uv run python ../benchmarks/latency.py --open     # the agents on Muse Spark Open instead

On this machine: Whisper on a 4-second chunk, the ECAPA voiceprint, and the phrase list.
On the Meta Model API (MODEL_API_KEY in .env): Muse Voice Transcribe on the last minute, the Muse Spark
Analyst and Decider, the Muse Spark alert writer, and the Muse Wonder Notice reviewer.
Nothing is ever sent to anyone: no alert is delivered, only its text is written.

Each stage runs once to warm up (model loading and connection setup are not counted). A call that
fails, or falls back to the fixed rules or the template, is counted as a failure, not as a time.
Results go to benchmarks/results/latency-<time>.json and .md.
"""
from __future__ import annotations

import asyncio
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from scenarios.notice_cases import CASES  # noqa: E402
from watchme import decider, lexicon, muse, notice, speech  # noqa: E402
from watchme.config import settings  # noqa: E402

RUNS = int(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--runs=")), 20))
# --open: the same agents on Muse Spark Open, the open-weight model (OPEN_WEIGHTS_*), instead of the hosted models.
OPEN = "--open" in sys.argv
if OPEN:
    settings.analyst_model = settings.decider_model = settings.writer_model = settings.reviewer_model = "open"
LOCAL_RUNS = max(RUNS, 50)
OUT = ROOT / "app" / "scenarios" / "out"
RESULTS = ROOT / "benchmarks" / "results"
SR = speech.SAMPLE_RATE


def load(scene_id: str) -> np.ndarray:
    audio, rate = sf.read(OUT / f"{scene_id}.wav", dtype="float32")
    audio = audio if audio.ndim == 1 else audio.mean(axis=1)
    assert rate == SR, rate
    return audio


def script(scene: dict) -> str:
    """The scene's words in the [owner]/[other] form the Analyst reads."""
    return "\n".join(f"[{'owner' if l['role'] == 'owner' else 'other'}] {l['text']}" for l in scene["lines"])


def stats(times: list[float]) -> dict:
    if not times:
        return {"n": 0}
    ordered = sorted(times)
    pick = lambda q: ordered[min(len(ordered) - 1, max(0, round(q * len(ordered) + 0.5) - 1))]   # nearest rank
    return {"n": len(times), "median": statistics.median(times), "p90": pick(0.90), "p95": pick(0.95),
            "min": ordered[0], "max": ordered[-1]}


async def main() -> None:
    if not settings.muse_ready or not settings.voice_api_key:
        raise SystemExit("needs MODEL_API_KEY in .env: the Meta Model API stages are the point of this benchmark")
    if OPEN and not settings.open_ready:
        raise SystemExit("--open needs Muse Spark Open configured (OPEN_WEIGHTS_* or BASETEN_API_KEY)")
    manifest = json.loads((OUT / "manifest.json").read_text())
    harm = [s for s in manifest["scenes"] if s["label"] == "harm"]
    cases = [c for c in CASES if c.get("text")]
    times: dict[str, list[float]] = {}
    failures: dict[str, int] = {}

    def timed(stage: str, seconds: float, ok: bool = True) -> None:
        if ok:
            times.setdefault(stage, []).append(seconds)
        else:
            failures[stage] = failures.get(stage, 0) + 1

    # ── on this machine ──────────────────────────────────────────────────────
    speech.warm_up()
    for i in range(LOCAL_RUNS + 1):
        scene = harm[i % len(harm)]
        audio = load(scene["id"])
        first_harm = next((l for l in scene["lines"] if l.get("harm_starts")), scene["lines"][-1])
        start = max(0, int(first_harm["start"] * SR))
        chunk = audio[start:start + 4 * SR]
        owner = next(l for l in scene["lines"] if l["role"] == "owner")
        clip = audio[int(owner["start"] * SR):int(max(owner["end"], owner["start"] + 1.0) * SR)]
        text = script(scene)

        t = time.perf_counter(); speech.transcribe_whisper(chunk); whisper = time.perf_counter() - t
        t = time.perf_counter(); speech.voiceprint(clip); print_ = time.perf_counter() - t
        t = time.perf_counter(); lexicon.score(lexicon.scan(text)); phrases = time.perf_counter() - t
        if i:   # run 0 is the warm-up
            timed("whisper_4s_chunk", whisper)
            timed("voiceprint", print_)
            timed("phrase_list", phrases)
    print(f"local stages: {LOCAL_RUNS} runs each", flush=True)

    # ── on the Meta Model API ────────────────────────────────────────────────
    context = {"local time": "Sat 23:40", "owner said OK": "not this session", "loud sounds in the last minute": 0,
               "another voice tried to stop the app": "no"}
    for i in range(RUNS + 1):
        scene = harm[i % len(harm)]
        audio = load(scene["id"])[-60 * SR:]               # the last minute, as before each analysis
        text = script(scene)
        warm = i == 0

        t = time.perf_counter()
        try:
            await asyncio.to_thread(speech.transcribe_muse, audio)
            ok = True
        except Exception:
            ok = False
        transcribe = time.perf_counter() - t

        t = time.perf_counter(); analysis = await muse.analyse(text); analyst = time.perf_counter() - t
        analyst_ok = bool(analysis) and "error" not in analysis

        t = time.perf_counter()
        decision = await decider.decide(text, analysis if analyst_ok else {"score": 0.8}, context)
        decide = time.perf_counter() - t
        decider_ok = decision.get("engine") == "muse-spark"

        facts = {"name": "Alex", "why": "no answer to \"Are you OK?\"", "time": "23:41 EST",
                 "location_link_added_by_app": True, "heard": scene["lines"][-1]["text"][:160]}
        t = time.perf_counter(); body = await muse.write_alert(facts); write = time.perf_counter() - t
        writer_ok = body != muse._alert_fallback(facts)

        case = cases[i % len(cases)]
        t = time.perf_counter(); review = await notice.review(case["text"], case.get("setting", "")); reviewed = time.perf_counter() - t
        review_ok = bool(review) and "error" not in review

        if not warm:
            timed("voice_transcribe_last_minute", transcribe, ok)
            timed("analyst_muse_spark_1_3", analyst, analyst_ok)
            timed("decider_muse_spark_1_1", decide, decider_ok)
            timed("alert_writer_muse_spark_1_3", write, writer_ok)
            timed("notice_review_muse_wonder_1_0", reviewed, review_ok)
            if ok and analyst_ok and decider_ok:
                timed("check_in_path_model_time", transcribe + analyst + decide)
        print(f"run {i}{' (warm-up)' if warm else ''}: transcribe {transcribe:.2f}s, analyst {analyst:.2f}s, "
              f"decider {decide:.2f}s, writer {write:.2f}s, review {reviewed:.2f}s", flush=True)

    # ── report ───────────────────────────────────────────────────────────────
    stamp = time.strftime("%Y%m%d-%H%M") + ("-open" if OPEN else "")
    summary = {name: stats(values) for name, values in times.items()}
    data = {
        "when": time.strftime("%Y-%m-%d %H:%M %Z"), "runs": RUNS, "local_runs": LOCAL_RUNS,
        "machine": f"{platform.system()} {platform.machine()}, Python {platform.python_version()}",
        "open_weights": {"model": settings.open_weights_model, "base": settings.open_weights_base} if OPEN else None,
        "models": {"analyst": settings.analyst_model or settings.meta_model, "decider": settings.decider_model,
                   "writer": settings.writer_model or settings.meta_model,
                   "reviewer": settings.reviewer_model or settings.meta_model,
                   "transcribe": "muse-voice-transcribe-1.0", "whisper": settings.whisper_model},
        "failures": failures, "summary": summary, "raw_seconds": times,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"latency-{stamp}.json").write_text(json.dumps(data, indent=2))
    who = "Muse Spark Open" if OPEN else None
    rows = [("whisper_4s_chunk", "Whisper base, one 4 s chunk", "this machine"),
            ("voiceprint", "ECAPA voiceprint, one sentence", "this machine"),
            ("phrase_list", "Phrase list, the whole scene", "this machine"),
            ("voice_transcribe_last_minute", "Muse Voice Transcribe 1.0, the last minute", "Meta Model API"),
            ("analyst_muse_spark_1_3", f"Analyst, {who or 'Muse Spark 1.3'}", "Baseten (open weights)" if OPEN else "Meta Model API"),
            ("decider_muse_spark_1_1", f"Decider, {who or 'Muse Spark 1.1'}", "Baseten (open weights)" if OPEN else "Meta Model API"),
            ("check_in_path_model_time", "Check-in path: transcribe + Analyst + Decider", "both" if OPEN else "Meta Model API"),
            ("alert_writer_muse_spark_1_3", f"Alert text, {who or 'Muse Spark 1.3'}", "Baseten (open weights)" if OPEN else "Meta Model API"),
            ("notice_review_muse_wonder_1_0", f"Notice review, {who or 'Muse Wonder 1.0'}", "Baseten (open weights)" if OPEN else "Meta Model API")]
    ms = lambda s: f"{s * 1000:.1f} ms" if s < 0.1 else f"{s:.2f} s"
    lines = [f"# Latency, {data['when']}", "", f"{data['machine']}. Meta Model API stages: {RUNS} runs each after a warm-up; "
             f"local stages: {LOCAL_RUNS}.", "", "| Stage | Where | median | p90 | p95 | max | n | failed |", "|---|---|---|---|---|---|---|---|"]
    for key, label, where in rows:
        s = summary.get(key, {"n": 0})
        if s["n"]:
            lines.append(f"| {label} | {where} | {ms(s['median'])} | {ms(s['p90'])} | {ms(s['p95'])} | {ms(s['max'])} | {s['n']} | {failures.get(key, 0)} |")
    (RESULTS / f"latency-{stamp}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote benchmarks/results/latency-{stamp}.json and .md")


if __name__ == "__main__":
    asyncio.run(main())
