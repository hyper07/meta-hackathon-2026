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

## Speed

| Step | Time |
|---|---|
| Whisper base, one 4-second chunk on this Mac | 0.29 s |
| Muse Spark 1.1 Decider | about 2 s |
| Muse Voice Transcribe, the last minute before each analysis | 3.4 s (median) |
| Muse Voice Transcribe, a 33 s spoken Notice account | 5.4 s |

Source: [app/scenarios/README.md](../app/scenarios/README.md#which-model-for-which-agent) and `results/20261101-0806-stt.md`.

## Run it again

```bash
./benchmarks/run.sh            # phrase-list baseline only: no keys needed
./benchmarks/run.sh --agents   # also the Muse agents and the Notice reviewer (MODEL_API_KEY in .env)
```

New results land in `app/scenarios/results/` as JSON plus a Markdown table. The first run renders the scenes (a few minutes; it needs the `scenarios` dependency group).

**Limits.** The scenes were written by the people who built the app, the voices are synthetic, and each row is a single run. Model calls vary between runs by about a scene. Use these numbers to compare versions, not as a claim about real-world accuracy.
