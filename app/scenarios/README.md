# Scenarios: realistic test scenes for Watch Me

Twenty-two scripted scenes:
- **Speakers:** each is voiced by natural neural voices (Kokoro-82M). The owner is always the same woman's voice, `af_heart`.
- **Background:** each is mixed over party, bar, street, TV or quiet noise.
- **Evaluation:** each is streamed through the real agents in the same 4-second chunks the phone sends.

They are the test set for detection and the voice lock, and audio for the demo video.

```bash
cd app
uv sync --all-groups
uv run python -m scenarios.build                    # renders scenarios/out/*.wav + manifest.json
uv run python -m scenarios.evaluate                 # the agents as configured in .env
uv run python -m scenarios.evaluate --phrases-only  # baseline: phrase list and fixed rules
uv run python -m scenarios.evaluate party-drink     # one scene
```

The evaluator always forces alerts to dry run: it never texts or calls anyone, whatever is in `.env`. Results go to `results/` as JSON plus a Markdown table.

## The scenes

[scenes.py](scenes.py) has 11 harmful scenes, 9 harmless ones and 2 notice scenes (school and work; see Notice mode below). The harmless ones include deliberate hard cases:

| Harmful (should ask "Are you OK?") | Harmless (should not) |
|---|---|
| drink pressure, then "I feel dizzy" · unwanted touching · "don't tell anyone, nobody will believe you" · followed on the way home · others talking about her while she can't respond · pressure on a date with few keywords · street harassment · **a stranger says "stop watching"** · a rideshare driver going the wrong way · a former partner's threat · drugging symptoms | banter ("stop it, that's hilarious") · flirting · retelling a horror film ("I'll kill you") · a crime report on TV · retelling someone else's experience · board-game trash talk · a gym trainer ("don't stop") · ordering food · walking home with a friend |

**Limits:**
- The lines were written by the people building the app, not by advocates.
- The voices are synthetic.
- n is 20.

Use the numbers to compare versions of the app, not as a claim about real-world accuracy.

## Results (2026-11-01, realistic voices)

Agents, all on the Meta Model API (reasoning low): Muse Voice Transcribe re-hears the last minute for the Analyst, Muse Spark 1.3 is the Analyst, Muse Spark 1.1 the Decider. Whisper transcribes the live 4-second chunks. 22 scenes, with a sentence cut off at the end of a chunk held for the next one.

| | Phrase list and fixed rules | Agents |
|---|---|---|
| Started by the owner's "Watch me" | 20 of 22 | 20 of 22 |
| Harmful scenes with an "Are you OK?" | 8 of 11 | **9 of 11** |
| Harmless scenes with a needless check-in | 2 of 9 ("movie-talk", "retelling") | **0 of 9** |
| First harmful line to check-in | median 9.1 s, worst 13.1 s | median 5.4 s, worst 13.1 s |
| School and work scenes without a check-in | 2 of 2 | 2 of 2 |

Full tables: `results/20261031-1749-phrases.md` and `results/20261101-0823-agents.md`. Times are on the scenes' own clock, one step per 4-second chunk; the model calls' own time is not added. In real use, Muse Voice Transcribe adds about 3.4 s (median) to each analysis and the Analyst about 3 s.

**The two misses:**
- **they-talk-about-her.** Party chatter overlaps her "Watch me", so the start bar refuses it and the session never starts.
- **date-pressure.** Quiet pressure with no phrase-list words ("don't make this weird", "just stay a little longer"). The Analyst runs on a phrase-list flag, a loud sound or every 30 s (`ANALYST_SWEEP_S`), and this scene ends before the first sweep.

**A 15-second sweep** (`ANALYST_SWEEP_S=15`):
- date-pressure gets a check-in 8.2 s after the pressure starts.
- In the same run, "retelling" (her telling a friend what happened to someone else) also got a needless check-in. It scored 0.80 both times, and with the 30 s sweep the Decider discarded it.
- It also means twice as many Meta API calls while watching.

The default stays at 30 s until more runs show whether the needless check-in is caused by the shorter sweep or is just run-to-run variation.

**Holding a cut-off sentence** (`HOLD_MAX_S`, on by default). A sentence still going at the end of a 4-second chunk is held and transcribed with the next chunk, so commands and voiceprints see whole sentences. On the 22 scenes (2026-10-31, `results/20261031-1245-agents.md`):
- 20 of 22 started;
- 9 of 11 harmful scenes got an "Are you OK?", and 0 of 9 harmless scenes got a needless one;
- median 5.0 s from the first harmful line to the check-in.

So holding cost no detection, and party-drink's check-in came at 2.2 s.

**Runs vary.** On noise before speech, Whisper sometimes loops ("wait, wait, wait…") and retries with random sampling, so the same scene can transcribe differently from one run to the next. For example, party-drink's "Watch me" was missed in one of four runs. Compare versions over several runs, not one.

## Which model for which agent

Every agent can use a different model (`ANALYST_MODEL`, `REVIEWER_MODEL`, `WRITER_MODEL`, `STT_ENGINE`). We measured the Muse models the Meta Model API offers for each job (2026-10-31):

| Agent | Job | Chosen | Why |
|---|---|---|---|
| Listener (live) | speech-to-text, every 4 s | **Whisper base** on this machine | Faster (0.29 s a chunk against 0.84 s) and fewer errors on 4-second chunks (median 15% against 27%). With Muse Voice Transcribe live, check-ins came later (median 9.5 s against 5.4 s) and one fewer harmful scene asked. See [speech-to-text](#speech-to-text-whisper-on-this-machine-or-muse-voice-transcribe) below. |
| What the Analyst reads | speech-to-text of the last minute, before each analysis | **Muse Voice Transcribe**, diarization | On whole recordings it made far fewer errors than Whisper in the noisy scenes (party-grab 8% against 57%, game-night 0% against 61%) and heard 100% of the harmful lines' words. Same results as Whisper alone on the 22 scenes (9 of 11, 0 of 9), with a cleaner transcript to quote from. Also used for audio kept offline. |
| Spoken Notice account | speech-to-text of a whole recording | **Muse Voice Transcribe** | 33 s of audio in 5.4 s, with clean speaker turns (A and B) in diarization mode. No voice lock is involved. |
| Analyst (live) | score the last minute | **Muse Spark 1.3**, reasoning low | Spark 1.1 and Muse Wonder caught as many scenes (8 of 11 each, against 9 of 11). The difference was Whisper missing "Watch me" in one scene, not the Analyst. Wonder added a needless check-in ("retelling"). Spark 1.3 is the newest and had none. |
| Decider | discard, ask or alert | **Muse Spark 1.1** (Meta Model API), reasoning low | On the 22 scenes: 9 of 11 harmful scenes asked, 0 of 9 needless check-ins, median 5.4 s (`results/20261031-1614-agents.md`). It answers in about 2 s, inside one 4-second chunk. Spark 1.3 decided the same on test moments but took 4–10 s. |
| Notice reviewer | name what matched, afterwards | **Muse Wonder 1.0**, reasoning low | Results below: right on 40 of 40 public training cases and 16 of 16 of ours, median 4.5 s. |
| Writer | alert text, session summaries | Muse Spark 1.3 | Not compared; the alert has a 10 s timeout and a template fallback. |

**Notice reviewer, three models** on the 40 public training cases (`--training`) and our 16:

| Model | Public cases: should match (32) | Public cases: should not match (8) | Our 16 | Median time |
|---|---|---|---|---|
| **Muse Wonder 1.0** | **32** | **8** | **16** | 4.5 s |
| Muse Spark 1.3 | 30 | 8 | 16 | 5.4 s |
| Muse Spark 1.1 | 30 | 6 | 16 | 2.3 s |

Spark 1.3 and 1.1 both missed the two religion cases where the EEOC found remarks insensitive but not severe or pervasive (a yarmulke remark, prayers in meetings). Spark 1.1 also flagged two official "not harassment" cases: one polite ask for a date, and a coworker's own social-media posts.

## Speech-to-text: Whisper on this machine or Muse Voice Transcribe

The same 22 recordings, transcribed by both, compared with the scenes' scripts ([stt_compare.py](stt_compare.py), `uv run python -m scenarios.stt_compare`; 2026-11-01, `results/20261101-0806-stt.md`):

| | word errors (mean / median) | harmful lines' words heard | "Watch me" heard | time per request (median) |
|---|---|---|---|---|
| Whisper base, 4 s chunks | 41% / **15%** | 92% | 22 of 22 | **0.29 s** |
| Muse Voice Transcribe, 4 s chunks | 59% / 27% | **97%** | 22 of 22 | 0.84 s |
| Whisper base, whole recording | 27% / **3%** | 99% | 21 of 22 | 0.51 s |
| Muse Voice Transcribe, whole recording | 27% / 7% | **100%** | **22 of 22** | 3.4 s |

Word errors count every extra word, and in the party and TV scenes both also transcribe background voices that aren't in the script (Muse more of them), so those scenes score above 100%. The harmful lines' words are the better guide to what matters.

On whole recordings Muse was far better where people talk over each other: party-grab 8% against 57%, stranger-stop 14% against 41%, dizzy-alone 14% against 63%, game-night 0% against 61%.

The app, end to end on the 22 scenes (`results/20261031-1614-agents.md`, `20261101-0756-agents.md`, `20261101-0823-agents.md`):

| Live chunks | What the Analyst reads | Started | Harmful asked | Needless | Check-in (median) |
|---|---|---|---|---|---|
| Whisper | Whisper's lines | 20 of 22 | 9 of 11 | 0 of 9 | 5.4 s |
| Muse Voice Transcribe | Muse's lines | 19 of 22 | 8 of 11 | 0 of 9 | 9.5 s |
| **Whisper** | **Muse Voice Transcribe, the last minute** | **20 of 22** | **9 of 11** | **0 of 9** | **5.4 s** |

So each does what it measured best at. Whisper on 4-second chunks keeps check-ins fast and the voice lock tight. Muse on the whole last minute gives the Analyst the clearest transcript to quote from.

Whisper isn't deterministic on noisy audio: on the same chunk it sometimes hears an extra "Wait" in the party noise before "Watch me", which shortens that clip and lowers the voice match. So one scene's start can differ between runs.

## Notice mode

**Public training examples** ([training_cases.py](training_cases.py), `uv run python -m scenarios.notice_eval --training`). These are 40 cases with an official answer, rewritten as first-person accounts:
- **Sources:** New York State's official sexual harassment prevention training case studies (2023 and 2018); EEOC examples (the Compliance Manual on religion and on race and color, national-origin guidance, Youth@Work); and StopBullying.gov's cyberbullying examples. Some come from the EEOC's 2024 harassment guidance, which the EEOC rescinded in January 2026. It's used only as a source of realistic scenarios with a stated conclusion, not as current law, and its gender-identity examples are left out.
- **Answers:** 25 are harassment by the source's answer. 8 are not harassment at all: one polite ask for a date, an accident followed by an apology, coworkers praying in their own room, and similar. 7 more are conduct the source calls offensive but not severe or pervasive enough to be illegal. For those 7, the app should still name what the words match, since it describes conduct and leaves legality to others.
- **Coverage:** every category is covered, including race and national origin, religion, age, disability, sexual orientation, pregnancy, threats, bullying and online abuse. Most cases are workplace ones; 3 are school and 3 online.
- **Muse Wonder's result:** 32 of 32 named an expected type (all of them in 27), and 8 of 8 came back "none". Full table: `results/20261031-1245-notice-training.md`.

These are a better test than our own accounts, because someone else wrote them and decided the answers. They are still training examples, though, written to be clear-cut.

**Written accounts** ([notice_cases.py](notice_cases.py), `uv run python -m scenarios.notice_eval`): 16 short accounts, at school and at work, two of them as transcripts.

| Muse Spark 1.3 (Meta Model API), 2026-10-31 | |
|---|---|
| Should match, found with the expected type | **8 of 8**: strings attached, comments about looks, put-downs because of sex, kept going after no, retaliation, touching, sexual comments |
| Harmless hard cases that came back "none" | **8 of 8**: blunt feedback, a fair grade, no extension, mutual teasing, retelling someone else's story, praise, a normal one-on-one, planning a study session |

Full table: `results/20261031-1213-notice.md`. The model often names extra types next to the expected one, for example "getting you alone" for the office-hours invitation. That's a reasonable reading, but the eval doesn't score extras.

**Audio scenes:** `office-hours` and `meeting-joke` in [scenes.py](scenes.py) run in notice mode in `scenarios.evaluate`. In both, no check-in appeared. After the scene stopped, the review named:
- **office-hours:** strings attached, getting you alone, unwanted advances, punished for objecting;
- **meeting-joke:** comments about looks, put-downs because of sex.

The live Analyst gave neither a high score during the scene, because both are under 30 s and use no phrase-list words. The review afterwards is what catches them, which is how notice mode is meant to work.

## Voices

[voices.py](voices.py) has four engines. The default cast is **Kokoro** (hexgrad/Kokoro-82M, Apache-2.0): 24 natural American and British voices, and Whisper transcribes them word for word.

`build --mixed` adds older, more synthetic-sounding engines:
- macOS `say` voices;
- Meta's MMS-TTS (`facebook/mms-tts-eng`);
- Microsoft SpeechT5.

## How the voice lock was calibrated

Only the owner's voice may stop Watch Me or answer "I'm OK", so the threshold for those has to keep every other voice out.

**Method:** we scored each sentence exactly as the app does: Whisper's sentence, trimmed to its loudest part, then a voiceprint compared with the enrolled owner. Then we compared models on the 20 scenes:
- 61 owner sentences;
- 70 sentences from 15 other voices;
- 18 more "owner" sentences that were really background chatter overlapping her lines, left out.

| Speaker model | Bar with no other voice passing | Owner sentences below it |
|---|---|---|
| WavLM-SV (`microsoft/wavlm-base-plus-sv`) | 0.92 | about half (42 of 79, background included) |
| **ECAPA-TDNN (`speechbrain/spkrec-ecapa-voxceleb`)** | **0.33** (closest other voice: 0.328) | 18 of 61 |

**Why we switched to ECAPA.** With WavLM, three American female voices that sound like the owner scored 0.88–0.92, as high as she did. ECAPA keeps them apart better.

**The two bars** (`VOICE_THRESHOLD`, `VOICE_STRICT_THRESHOLD`):
- **Start, and tagging a line "you": 0.20.** It accepted the owner's "Watch me" in 18 of 19 scenes. A stranger passing this bar can start a session but never stop one.
- **Stop or "I'm OK": 0.36.** That's 0.03 above the closest other voice; 29 of 61 owner sentences fall below it. In a loud room, "stop watching" may take a second try. The screen says so, and a stranger's attempt still triggers a check-in.

The screen shows a 0–100% match where the start bar is 70% and the stop bar is 90% (`speech.display_match`). ECAPA's raw scores are low numbers, and "verified: 35%" would read as a failure.

**What this doesn't prove:**
- The other voices come from the same TTS model as the owner's.
- Nobody tried a recording of the owner played back (a replay attack).

Enroll real people and test with them before relying on the lock.
