# Benchmarks

What Watch Me was measured on, the headline numbers, and how to run it again. The test scenes, the evaluator and every raw result live in [app/scenarios/](../app/scenarios/README.md). This page is the summary.

**The test set:** 22 scripted scenes (11 harmful, 9 harmless including hard cases, 2 school and work), voiced by synthetic voices over party, bar, street and TV noise. Each is streamed through the real agents in the same 4-second chunks the phone sends. Alerts are always forced to dry run.

## Detection: does it ask "Are you OK?" when it should, and only then?

| What's heard | Who judges it | Started | Harmful asked | Needless | Check-in (median) | Result file |
|---|---|---|---|---|---|---|
| **Whisper chunks, Muse Voice Transcribe for the last minute (the app today)** | **Muse Spark 1.3 Analyst + Muse Spark 1.1 Decider** | **20 of 22** | **9 of 11** | **0 of 9** | **5.4 s** | [20261101-0823-agents](../app/scenarios/results/20261101-0823-agents.md) |
| The script, word for word (perfect hearing) | the same Muse agents | 22 of 22 | 11 of 11 | 0 of 9 | 6.2 s | [20261101-1104-agents-script](../app/scenarios/results/20261101-1104-agents-script.md) |
| Muse Voice Transcribe, whole recording | the same Muse agents | 19 of 22 | 10 of 11 | 0 of 9 | 9.5 s | [20261101-1109-agents-muse-whole](../app/scenarios/results/20261101-1109-agents-muse-whole.md) |
| The script, word for word | phrase list and fixed rules (baseline) | 22 of 22 | 10 of 11 | 2 of 9 | 9.1 s | [20261101-1111-phrases-script](../app/scenarios/results/20261101-1111-phrases-script.md) |

Given perfect hearing, the Muse agents got all 11 harmful scenes and raised no false alarm. The phrase list, on the same words, raised two: a horror film quoted ("I'll kill you") and someone else's story retold.

## Notice mode: the harassment reviewer

| Model | 40 public EEOC training cases | Our 16 cases | Median time |
|---|---|---|---|
| **Muse Wonder 1.0 (chosen)** | **40 of 40** | **16 of 16** | 4.5 s |
| Muse Spark 1.3 | 38 of 40 | 16 of 16 | 5.4 s |
| Muse Spark 1.1 | 36 of 40 | 16 of 16 | 2.3 s |

Result files: `app/scenarios/results/2026103*-notice*.md`.

## Voice lock: only her voice stops it or says "I'm OK"

ECAPA-TDNN voiceprints, scored per sentence as the app does: 61 owner sentences and 70 from 15 other voices.

| Measure | Value |
|---|---|
| Closest other voice | 0.328 |
| Bar to stop or say "I'm OK" | 0.36 (no other voice passed it) |
| Bar to start ("Watch me") | 0.20, accepted her in 18 of 19 scenes |
| The old model (WavLM-SV) | similar female voices scored 0.88–0.92, as high as the owner; replaced |

## Latency: every stage, timed with the app's own code

`latency.py` runs each stage the way the app does, on the test scenes: the local stages 50 times, the Meta Model API stages 20 times after a warm-up. A call that fails or falls back (to the fixed rules, or to the alert template) counts as a failure, not as a time. Results: [results/latency-20261103-2336.md](results/latency-20261103-2336.md), with every raw timing in the JSON next to it.

| Stage | Where | median | p90 | p95 | max | failed |
|---|---|---|---|---|---|---|
| Whisper base, one 4 s chunk | this machine | 0.34 s | 0.35 s | 0.35 s | 0.36 s | 0 of 50 |
| ECAPA voiceprint, one sentence | this machine | 26.9 ms | 29.9 ms | 30.4 ms | 33.7 ms | 0 of 50 |
| Phrase list, a whole scene | this machine | 0.1 ms | 0.2 ms | 0.2 ms | 0.2 ms | 0 of 50 |
| Muse Voice Transcribe 1.0, the last minute | Meta Model API | 3.82 s | 4.74 s | 5.88 s | 5.88 s | 0 of 20 |
| Analyst, Muse Spark 1.3 | Meta Model API | 7.41 s | 8.77 s | 9.54 s | 9.54 s | 0 of 20 |
| Decider, Muse Spark 1.1 | Meta Model API | 3.07 s | 4.33 s | 5.26 s | 5.26 s | 0 of 20 |
| Check-in path: transcribe, then Analyst, then Decider | Meta Model API | 14.33 s | 16.33 s | 17.11 s | 17.11 s | 0 of 20 |
| Alert text, Muse Spark 1.3 | Meta Model API | 6.25 s | 7.73 s | 7.93 s | 7.93 s | 2 of 20 (template used) |
| Notice review, Muse Wonder 1.0 | Meta Model API | 4.78 s | 7.00 s | 8.82 s | 8.82 s | 0 of 20 |

Measured 2026-11-03 on an Apple Silicon Mac, CPU only. Earlier, on 2026-10-31, the Analyst took 2.6–4.1 s and the Decider about 2 s ([app/README.md](../app/README.md)); the Meta Model API's speed varies by time of day. Whisper on a whole 4 s chunk measured 0.29 s on 2026-11-01 (`results/20261101-0806-stt.md`).

What it means in use: the on-device loop (Whisper, the voiceprint, the phrase list) answers within the 4-second chunk, online or offline. A check-in that needs the Muse agents waits for three calls in a row, about 14 s of model time; if the API is off or fails, the fixed rules ask on the phrase-list score alone. The alert never waits on a model: the writer has a 10 s limit and the template takes over.

## Run it again

```bash
./benchmarks/run.sh            # phrase-list baseline only: no keys needed
./benchmarks/run.sh --agents   # also the Muse agents, the Notice reviewer and the latency run (MODEL_API_KEY in .env)
cd app && uv run python ../benchmarks/latency.py --runs=20   # the latency run alone
```

New results land in `app/scenarios/results/` (accuracy) and `benchmarks/results/` (latency) as JSON plus a Markdown table. The first run renders the scenes (a few minutes; it needs the `scenarios` dependency group).

**Limits.** The scenes were written by the people who built the app, the voices are synthetic, and each row is a single run. Model calls vary between runs by about a scene. Use these numbers to compare versions, not as a claim about real-world accuracy.
