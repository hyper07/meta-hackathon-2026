# Watch Me

**A voice-locked safety assistant for a party, a date, the walk home, and home itself.** She says "Watch me". A team of Muse agents listens for threats, coercion and signs of drugging, and asks "Are you OK?" when something is wrong. If she can't answer, the people she chose get a text, a call and an email, with what it heard and a map of where she is. Only her voice can turn it off, and only she decides what happened. It is a multi-model pipeline with deterministic checks, not a prompt: an ECAPA voiceprint and Whisper on the device gate every command; Muse Voice Transcribe re-hears the last minute; Muse Spark Open, Meta's open-weight model, analyses it and may only quote words that are in the transcript, then gives probabilities that fixed rules turn into discard, ask or alert, so a model alone can never discard a real risk or send an alert; Muse Wonder reviews Notice accounts; and the app itself, not a model, adds the map link and keeps the hash-chained record. Muse Spark Open runs on Baseten with the hosted Meta Model API as its backup, and on our tests it decided exactly as the hosted Muse Spark did, reaching "Are you OK?" about 6 s sooner. The voice lock and live speech-to-text run locally.

**▶ Try it live, no install or key: [kibaek-kim2018--watch-me-demo-web.us-east.modal.run](https://kibaek-kim2018--watch-me-demo-web.us-east.modal.run)** · [3-minute video](https://www.youtube.com/watch?v=mupz2IrtyWo) · [benchmarks](#benchmarks) · `docker compose up --build` to run it yourself

[![Try it live](https://img.shields.io/badge/try%20it-live%20demo-2ea44f)](https://kibaek-kim2018--watch-me-demo-web.us-east.modal.run)
[![Demo video](https://img.shields.io/badge/demo-video%202%3A55-red?logo=youtube)](https://www.youtube.com/watch?v=mupz2IrtyWo)
[![Dataset on Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20dataset-watch--me--safety--scenes-yellow)](https://huggingface.co/datasets/hyper07/watch-me-safety-scenes)
[![CI](https://github.com/hyper07/meta-hackathon-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/hyper07/meta-hackathon-2026/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-informational)](app/pyproject.toml)
[![Meta Model API](https://img.shields.io/badge/Meta%20Model%20API-Muse%20Spark%20%C2%B7%20Wonder%20%C2%B7%20Voice-0866FF?logo=meta&logoColor=white)](#meta-global-ai-developer-hackathon-2026-submission-overview)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](app/pyproject.toml)
[![Expo SDK 58](https://img.shields.io/badge/Expo%20SDK%2058-React%20Native%200.88-000020?logo=expo)](mobile/package.json)
[![Docker](https://img.shields.io/badge/docker-compose%20up-2496ED?logo=docker&logoColor=white)](compose.yaml)

## Meta Global AI Developer Hackathon 2026: submission overview

| | |
|---|---|
| **Track · problem statement** | Indie Developer · Build for Your World |
| **Hackathon provenance** (Oct 26 – Nov 4, 2026) | Built from scratch during the hackathon window: work began Oct 27, and the repository was first committed and published on Oct 31 (38 commits since). Before it: idea notes only, no code ([what was built when](#what-was-built-during-the-hackathon)) |
| **Meta AI runtime models** | **Muse Spark Open** (`meta-models/muse-spark-open`, open weights, served by Baseten): the Analyst, the Decider and the alert writer · their backup on the Meta Model API: `muse-spark-1.3` (Analyst, writer), `muse-spark-1.1` (Decider) · `muse-wonder-1.0`: the Notice reviewer · `muse-voice-transcribe-1.0`: re-hears the last minute, transcribes audio kept offline and spoken accounts · `muse-image-1.0`: the Charm concept images ([Built with Meta](#built-with-meta)). Open weights are used as published; no fine-tuning |
| **Try it live** | **https://kibaek-kim2018--watch-me-demo-web.us-east.modal.run**: no install, no account, no key. Record your voice in Setup (one line), then say "Watch me" on the Watch tab. One visitor at a time for 10 minutes; alerts are a dry run with example contacts, and nothing you say or type is kept after you leave ([how the live demo works](#the-live-demo)) |
| **3-minute demo video** | https://www.youtube.com/watch?v=mupz2IrtyWo (2:55; the provenance line is spoken and on screen at 0:00) |
| **Quickstart & keyless mode** | `cp -n .env.example .env`, set `MODEL_API_KEY`, then `docker compose up --build` (http://localhost:8000) or `cd app && uv sync && ./run.sh` ([Run it](#run-it)). With no key, the whole check-in loop still runs on the device: Whisper, the voiceprint, the phrase list and the fixed rules. Alerts are a dry run until Twilio or SMTP keys are set. Recorded runs of the real models, scene by scene, are in [app/scenarios/results/](app/scenarios/results/) ([keyless mode and recorded traces](#without-a-key-and-recorded-traces)) |
| **Measured** | Open weights against hosted, the same tests: given a perfect transcript, Muse Spark Open and the hosted Muse agents both asked in 11 of 11 harmful scenes with 0 of 9 needless check-ins; Muse Spark Open decided in 1.6 s against 2.6 s and analysed in 1.7 s against 7.2 s (medians of 20, run the same afternoon); on the live demo, "Are you OK?" came 9.6 s after the first harmful line, against 15.0 s. Notice: Muse Wonder right on 40 of 40 public EEOC and NY State cases. On the device, Whisper hears a 4 s chunk in 0.34 s and the voiceprint takes 27 ms ([Benchmarks](#benchmarks)) |
| **Open dataset** | [huggingface.co/datasets/hyper07/watch-me-safety-scenes](https://huggingface.co/datasets/hyper07/watch-me-safety-scenes): the 22 scenes with their scripts and audio, the owner's enrollment lines, and the 56 Notice cases with their official sources, so other systems can be measured on the same test (CC BY 4.0) |
| **Bonus prize categories targeted** | **Best Build on Meta Open Weight Models**: Muse Spark Open runs the live safety loop (Analyst, Decider, alert writer), measured against the hosted models on the same tests · **Best Agentic Use-Case**: five agents on Muse models, with fixed rules that decide to discard, ask or alert |
| **Next devices** | Meta's Muse Charm pendant (a stealth design, already prototyped on an ESP32-C6 board) · Meta's AI glasses (hands-free, with the check-in in her ear) |
| **Where things are** | [app/](app/README.md): the server, agents and web page · [mobile/](mobile/README.md): the iPhone and Android app · [device/](device/README.md): a Charm stand-in on an ESP32-C6 board · [demo/](demo/): the video and how it's made |
| **Stack** | Python 3.11+, FastAPI, faster-whisper, SpeechBrain ECAPA, PyTorch (CPU) · Expo SDK 58, React Native 0.88, TypeScript · ESP32-C6 (Arduino) · Docker · GitHub Actions · the live demo hosted on [Modal](https://modal.com) |
| **License** | [Apache-2.0](LICENSE) |

## Safety, privacy and the law

Watch Me handles the most sensitive moments people have, so these rules are built into the code, not just written here ([SAFETY_AND_LAW.md](SAFETY_AND_LAW.md) has the full reasoning):

- **Legal information, never legal advice.** Notice shows which exact words match how the EEOC and the Department of Education describe harassment, with links to the definitions. It never says "you have a case" and never gives a verdict: only she decides what happened. Every review ends with that sentence.
- **Similar cases are real, and labelled.** Next to a review, Notice can show up to three real public cases (EEOC and New York State training examples) whose official answer named the same kinds of conduct, each with its source. They are picked by rule, not written by a model, so none can be invented: a case must share the kinds of conduct her review found and be about the same basis (a race or religion case never appears next to sexual harassment), and rare, specific conduct such as "strings attached" counts most. Cases from the EEOC's 2024 harassment guidance say that it was rescinded in January 2026 and is not current law.
- **Where to turn, with verified numbers only:** the EEOC (1-800-669-4000), the Department of Education's Office for Civil Rights (1-800-421-3481), RAINN (800-656-4673), the National Domestic Violence Hotline (1-800-799-7233, or text START to 88788), the Cyber Civil Rights Initiative (844-878-2274), and the American Bar Association's Find Legal Help for a lawyer. Her own Title IX coordinator or HR contact is what she enters in Setup; the app never guesses who that is.
- **She shares the evidence, the app doesn't.** "Export everything about Prof. R" makes a dated record with its hash chain, to bring to a meeting. Watch Me never sends it to anyone.
- **Opt-in, on her own device, only conversations she's part of.** Nothing is kept in standby. Audio is kept only around flagged moments, and never where `RECORDING_RULE=all-party` (states where everyone must consent to a recording); then only text notes are kept.
- **No alert because a model judged the scene.** Watch Me asks "Are you OK?" first; it alerts only when she doesn't answer, says "no" in her voice, presses "Get help", or says her SOS or duress phrase.
- **Only her voice turns it off.** That also protects her from a partner who monitors or controls: anyone else's "stop watching" is refused.
- **The public demo keeps nothing:** one visitor at a time, alerts always a dry run, and everything wiped when they leave ([the live demo](#the-live-demo)).

## Contents

- [The live demo](#the-live-demo) · [The demo video](#the-demo) · [Next: Meta's Muse Charm](#next-metas-muse-charm) · [Meta's AI glasses](#also-metas-ai-glasses)
- [Safety, privacy and the law](#safety-privacy-and-the-law)
- [Run it](#run-it) · [No internet](#no-internet) · [Without a key, and recorded traces](#without-a-key-and-recorded-traces) · [Configuration](#configuration) · [Deploying](#deploying)
- [Built with Meta](#built-with-meta): which model does what, and how the agents fit together
- [Benchmarks](#benchmarks): accuracy, the Notice reviewer, the voice lock, latency
- [Test cases](#test-cases): 88 automated tests, 22 scenes and 56 written cases
- [Code layout](#code-layout) · [Technical notes](#technical-notes)
- [What was built during the hackathon](#what-was-built-during-the-hackathon)
- [The idea](#the-idea) · [Domestic violence](#domestic-violence) · [What it does](#what-it-does) · [What it must not become](#what-it-must-not-become)
- [Documents](#documents) · [License](#license)

## The live demo

**[https://kibaek-kim2018--watch-me-demo-web.us-east.modal.run](https://kibaek-kim2018--watch-me-demo-web.us-east.modal.run)**: open it in Chrome or Safari and tap **Turn on microphone and sound** (it asks for the microphone, and plays "Are you OK?" so you know you'll hear it). Record your voice in Setup (one line, said once), then go to Watch, tap Start listening and say **"Watch me"**. Talk about a drink someone keeps pushing on you, or say you feel dizzy, and don't answer "Are you OK?": you'll see the alert it would have sent.

It runs on [Modal](https://modal.com) ([deploy/modal_app.py](deploy/modal_app.py)), on the CPU, with every agent live: Muse Spark Open on Baseten for the Analyst, the Decider and the alert writer (the hosted Muse models as their backup), and Muse Wonder and Muse Voice Transcribe on the Meta Model API. The server was built for one owner, so the public demo runs it in **demo mode** (`DEMO_MODE=1`, tested in [app/tests/test_demo.py](app/tests/test_demo.py)):

- **One visitor at a time**, for 10 minutes. Anyone else sees "someone is trying the demo right now", and their page connects by itself when it's free.
- **Only that visitor's page can use the API.** Each visit gets its own token; without it, every endpoint except the status answers 423.
- **Alerts are always a dry run and no audio is kept**, whatever else is set. Only the Meta Model API key is sent to Modal, never Twilio or SMTP keys, and the contacts are examples.
- **Everything is wiped when the visitor leaves:** the voiceprint, sessions, Notice entries and queued work. A closed tab is noticed within 45 s (the page sends a heartbeat), so the next visitor doesn't wait.
- **Each visit starts with example history** ([app/demo_seed/](app/demo_seed/)), so Review and Notice aren't empty: three real sessions (the party with its alert and map link and 48 s of kept audio; a stranger's "stop watching" refused, with 18 s of kept audio that starts with his voice; office hours in Notice mode), and a Notice book where Prof. R appears three times, which makes a pattern, plus one entry from work. The examples are real runs of the app with synthetic voices; the work entry's review came from Muse Wonder.

`deploy/smoke_test.py` makes a whole visit with a test scene instead of a microphone. On the party scene, the voice lock accepted the owner's "Watch me" (match 0.82) and tagged the others as other voices; Muse Spark 1.1 decided to ask, "Are you OK?" came 15.0 s after the first harmful line, and with no answer the dry-run alert went out 9.9 s later (one run, 2026-11-04).

## The demo

<a href="https://github.com/hyper07/meta-hackathon-2026/raw/main/demo/watch-me-demo.mp4">
  <img src="demo/watch-me-preview.gif" width="720" alt="Watch Me demo preview: the title, built during the hackathon, then Are you OK? with only a Get help button, the alert with a map link, a stranger's stop watching refused, and the Notice review with patterns">
</a>

**▶ [Watch the full demo on YouTube (2:55)](https://www.youtube.com/watch?v=mupz2IrtyWo)**, or [as an MP4](https://github.com/hyper07/meta-hackathon-2026/raw/main/demo/watch-me-demo.mp4) with captions in [watch-me-demo.srt](demo/watch-me-demo.srt). The preview above shows the opening (built during the hackathon, with the live app beside it) and three moments: "Are you OK?" (only her voice can answer "I'm OK"; the one button gets help) and the alert with her map link, a stranger's "stop watching" refused, and the Notice review with its pattern.

<p>
<img src="demo/screens/ios-watch.png" width="190" alt="Watch: the orb, Emergency or Notice, Start listening">
<img src="demo/screens/ios-watch-dark.png" width="190" alt="Watch in dark mode">
<img src="demo/screens/ios-notice.png" width="190" alt="Notice: tell it what happened; patterns per person">
<img src="demo/screens/ios-review.png" width="190" alt="Review: past sessions, colour-coded">
<img src="demo/screens/ios-setup.png" width="190" alt="Setup: server, you, people to alert, your voice">
</p>

*The iPhone app on the iOS simulator, connected to the Watch Me server: Watch (light and dark), Notice, Review and Setup.*

### Next: Meta's Muse Charm

On the Charm, Watch Me runs in **stealth**: while it listens and watches, the pendant looks exactly like any other Charm, with its usual character on the screen and nothing that tells anyone nearby she is recording. The only Watch Me screen it ever shows is "Are you OK?", because she has to see it to answer.

<p>
<img src="demo/charm/charm-stealth.jpg" width="420" alt="Concept: at a party, the Charm shows only its usual character while Watch Me listens unseen">
<img src="demo/charm/charm-checkin.jpg" width="420" alt="Concept: the Charm worn on its cord at night, asking Are you OK? with a countdown">
</p>

*Concept renders made with Muse Image (Meta Model API, [demo/make/charm_images.py](demo/make/charm_images.py)), using a Meta product photo of the Charm and the app's real screens as references. Not photos of a working product: today Watch Me runs on the phone, and the Charm becomes its always-on microphone once Meta opens it to developers.*

#### Working today: a Charm-sized prototype

To try the stealth design on real hardware, Watch Me also runs on a small ESP32-C6 board with a 1.69" screen, a microphone and a speaker ([device/](device/README.md)). Its screen shows **Momo**, a round cat drawn in code. Momo looks the same whether Watch Me is listening or not; only the sparkles in its eyes turn to tiny hearts while it watches, a hint just for her. When the agents hear something wrong, Momo turns worried and asks "Are you OK?" on screen and out loud, with a countdown. "I'm OK" in her own voice makes Momo happy again; no answer alerts her people, and Momo goes straight back to its usual face, so nobody nearby can tell.

<p>
<img src="demo/charm/MOMO.gif" width="300" alt="The prototype board: Momo on screen, then Are you OK? with a countdown as Watch Me checks in">
<img src="demo/charm/MOMO.jpg" width="300" alt="The prototype board asking Are you OK? Say I'm OK, with Momo looking worried and 4 seconds left">
</p>

*The real board, filmed during a run: the party scene played from a laptop's speakers, Momo's microphone heard it, and the Muse agents decided to check in. It talks to the same Watch Me server as the phone app, over Wi-Fi or a USB cable.*

#### Also: Meta's AI glasses

Watch Me can be adapted to Meta's AI glasses (Ray-Ban Meta, Oakley Meta, Meta Ray-Ban Display), and they suit it well:
- **Hands-free by design.** Watch Me is already voice-only: "Watch me", "stop watching" and "I'm OK" are all spoken, and nothing needs a tap.
- **"Are you OK?" in her ear.** The check-in can be spoken through the open-ear speakers, so only she hears it. On Meta Ray-Ban Display it can also appear privately in the lens, with its countdown.
- **No new server work.** The server takes 16 kHz audio over `/ws` from any client: the phone app, the web page and the ESP32 board already do. The glasses' microphones would reach it through the phone app, which pairs with them. Meta's Wearables Device Access Toolkit is the way to build on the glasses directly.

- **Later, what she sees too.** The glasses' camera could add sight to sound: with her consent, a frame at the moment of a check-in, read by a Muse vision model (Muse Spark reads images; SAM 3.1 segments them), could tell the Analyst what words miss, such as a drink being handed over or someone blocking a doorway. It would follow the same rules as audio: only while Watch Me is on, only around flagged moments, and only she decides what happened.

Not built or tested yet: this is the next step after the phone, alongside the Charm.

## Run it

You need macOS or Linux, [uv](https://docs.astral.sh/uv/) and Python 3.11+. For the phone app, you also need Node 20+, plus Xcode and CocoaPods (iPhone) or Android Studio and JDK 17 (Android).

**1. Add the key.** Every model agent runs on the Meta Model API. Without a key the app still runs, with the phrase list and fixed rules.

```bash
cp -n .env.example .env       # (-n keeps an existing .env) then set MODEL_API_KEY=<your Meta Model API key>
```

**2. Run the web app.**

```bash
cd app
uv sync                       # once: installs the server, Whisper and the voiceprint model
./run.sh                      # open http://127.0.0.1:8000
./run.sh --https              # https://<Wi-Fi IP>:8443, for a phone's browser on the same Wi-Fi (needs mkcert; see app/README.md)
```

Or with Docker, without installing Python or uv: `docker compose up --build`, then open http://localhost:8000. It reads `.env` from step 1 and runs on the CPU. Whisper and the voiceprint model are in the image, so it also runs with no internet ([No internet](#no-internet)).

Open Setup, enter your name, PIN and contacts, pick a model plan (Models and cost), and record your voice: one line, said once. Then go to Watch, turn on listening and say "Watch me".

**3. Build and run the iPhone or Android app.** It uses native modules, so it needs a development build; Expo Go won't work.

```bash
cd app && ./run.sh --lan      # in one terminal: the server for the app; prints the address, e.g. 192.168.1.20:8000

cd mobile                     # in another terminal
npm install
npx expo run:ios              # the iOS simulator or a connected iPhone
npx expo run:android          # an Android emulator or a connected phone
```

In the app, open Setup › Server, enter the address `run.sh --lan` printed, and tap Connect. Without a Mac or Android Studio, Expo can build it in the cloud: `npx eas-cli@latest build:configure` once, then `npx eas-cli@latest build --profile development`.

**4. Test it.**

```bash
cd app
uv run python -m pytest       # 77 tests; speech is faked, so no microphone needed
uv run python -m scenarios.build && uv run python -m scenarios.evaluate   # the 22 realistic scenes (app/scenarios/)
cd .. && uvx pytest tests     # 11 tests of the Charm board's USB link: framing, CRC, audio chunks
```

GitHub Actions runs both test suites, type-checks and lints the phone app, and builds the Docker image on every push. The measured results, and the scripts that run them again, are in [benchmarks/](benchmarks/README.md).

### No internet

Watch Me runs with no network at all. Choose **On this device only** in Setup › Models and cost (or set `MODEL_PLAN=local`), and nothing leaves the machine:

```bash
docker build -t watchme .
docker run --network none -e MODEL_PLAN=local -p 127.0.0.1:8000:8000 watchme    # no network inside the container
```

- **The Docker image carries the speech models.** Whisper and the ECAPA voiceprint model are baked in at build time, and `HF_HUB_OFFLINE=1` stops the libraries from looking online. In a container started with `--network none` (checked: no DNS, no route out), the models loaded in 1.8 s, Whisper heard "Are you okay? Say I'm okay." correctly, and the voiceprint was computed.
- **The page needs nothing from the internet:** no fonts, scripts or styles from elsewhere.
- **What still works:** "Watch me", "stop watching" and "I'm OK" by her voice; the phrase list scores every line; the fixed rules ask "Are you OK?"; the hash-chained record. For the case Watch Me was built for, a rule catches a drink pushed on her and then "I feel dizzy" (or unable to move or stand) within the same minute, which each line alone doesn't reach. With it, the phrase list and rules asked in **11 of 11** harmful scenes given the scripts (10 of 11 before), with the same 2 needless check-ins in 9 harmless ones ([result](app/scenarios/results/20261104-1541-phrases-script.md)).
- **What needs a network:** the Muse agents (they read context: no needless check-ins, against 2 for the rules), Notice reviews, and delivering an alert. With no network an alert is logged and shown as failed, so for real use she needs a connection when it matters. If the network is only down for a while (the Recommended plan), the audio and the analysis are kept and finished when it's back.

### Without a key, and recorded traces

Judges can check Watch Me without a Meta key and without special hardware:

- **Keyless mode.** With no `MODEL_API_KEY`, the app runs the whole Emergency loop on the device: Whisper hears the 4-second chunks, the ECAPA voiceprint locks start, stop and "I'm OK" to her voice, the phrase list scores each line, and the fixed rules ask "Are you OK?" and alert when there's no answer. Setup › "Models and services" shows what is configured. Alerts are a dry run, shown on screen and in the log, until Twilio or SMTP keys are set; the evaluator forces a dry run whatever is in `.env`.
- **Recorded traces.** Every evaluation run is kept in [app/scenarios/results/](app/scenarios/results/) as JSON and a Markdown table. For each of the 22 scenes: who said what, the Analyst's score and reason for every segment, the Decider's three probabilities and the rule it applied, and when the check-in came. [benchmarks/results/](benchmarks/results/) keeps the latency runs with every raw timing. The runs behind the numbers in this README are named next to them.
- **Deterministic runner.** `./benchmarks/run.sh` re-runs the phrase-list baseline on the scenes and on their scripts with no key (the scenes are rendered once, with the `scenarios` dependency group); `--agents` adds the Muse runs, and `benchmarks/latency.py` times every stage.

### Configuration

Everything is in [.env.example](.env.example), and all of it is optional. The main settings:

| Variable | Default | Purpose |
|---|---|---|
| `MODEL_API_KEY` (or `META_API_KEY`) | empty | the Meta Model API key from [dev.meta.ai](https://dev.meta.ai); without it: phrase list, fixed rules, dry-run alerts |
| `ANALYST_MODEL` · `DECIDER_MODEL` · `REVIEWER_MODEL` · `WRITER_MODEL` | `muse-spark-1.3` · `muse-spark-1.1` · `muse-wonder-1.0` · `muse-spark-1.3` | the model behind each agent |
| `LLM_REASONING_EFFORT` | `low` | higher efforts can spend the whole token budget on reasoning |
| `STT_ENGINE` · `ANALYST_STT` | `whisper` · `muse` | the live 4 s chunks; what the Analyst reads (the last minute, re-heard by Muse Voice Transcribe) |
| `WHISPER_MODEL` | `base` | `tiny`, `base` or `small` |
| `VOICE_THRESHOLD` · `VOICE_STRICT_THRESHOLD` | `0.20` · `0.36` | the voiceprint match to start; to stop or say "I'm OK" |
| `CHECKIN_TIMEOUT_S` · `URGENT_CHECKIN_TIMEOUT_S` | `30` · `15` | how long "Are you OK?" waits for her |
| `RECORDING_RULE` | `one-party` | `all-party`: never keep audio, text notes only |
| `TWILIO_ACCOUNT_SID` · `TWILIO_AUTH_TOKEN` · `TWILIO_FROM` | empty | real SMS and calls; empty: dry run |
| `SMTP_HOST` · `SMTP_PORT` · `SMTP_USER` · `SMTP_PASSWORD` | empty · `587` | real email; empty: dry run |
| `DATA_DIR` | `app/data` | the profile, logs and clips (`/data` in Docker) |
| `DEMO_MODE` · `DEMO_VISIT_S` · `DEMO_IDLE_S` | off · `600` · `45` | a public demo: one visitor at a time for 10 minutes, ended after 45 s without a heartbeat; alerts always a dry run, no audio kept, everything wiped after each visit |
| `BASETEN_API_KEY` (or `OPEN_WEIGHTS_API_KEY`, `MODAL_PROXY_TOKEN`) · `OPEN_WEIGHTS_BASE` · `OPEN_WEIGHTS_MODEL` | empty · `https://inference.baseten.co/v1` · `meta-models/muse-spark-open` | Muse Spark Open, the open-weight model. With a key, it runs the Analyst, the Decider and the writer, and the hosted models are their backup; without one, everything runs on the Meta Model API. Any endpoint that serves it works, such as a Modal shared endpoint |
| `DECIDER_HOSTED_MODEL` | `muse-spark-1.1` | the Decider's hosted backup when it runs on Muse Spark Open |
| `MODEL_PLAN` | `auto` | which models the agents may call, for cost; she can change it in Setup › Models and cost: `auto` (Muse Spark Open for the live agents, Muse Wonder for Notice, each with the other provider as backup), `open` (Muse Spark Open only, no Meta Model API calls), `hosted` (the Meta Model API only, no Baseten calls), `local` (no model calls at all: Whisper, the voiceprint, the phrase list and the fixed rules still ask and alert; no Notice reviews) |

`.env` is git-ignored and never copied into the Docker image; compose reads it at run time.

## Built with Meta

Every model agent runs on the **Meta Model API** (`api.meta.ai`, with `MODEL_API_KEY`), from [app/watchme/muse.py](app/watchme/muse.py), [decider.py](app/watchme/decider.py), [notice.py](app/watchme/notice.py) and [speech.py](app/watchme/speech.py). Each asks for JSON and checks it: a quote the model can't point to in the transcript is dropped, probabilities are normalised and then judged by fixed rules, and the alert's map link is added by the app.

| Agent | Model | What it does |
|---|---|---|
| Analyst | **Muse Spark Open** (open weights, Baseten); backup `muse-spark-1.3` | scores the last minute, names the categories and quotes the exact words; a quote not in the transcript is dropped |
| Decider | **Muse Spark Open**; backup `muse-spark-1.1` | a probability each for discard, ask and alert; fixed rules turn them into the action and ask when unsure |
| Writer | **Muse Spark Open**; backup `muse-spark-1.3` | the alert text and session summaries; the app adds the map link itself; a template takes over on a timeout |
| Notice reviewer | `muse-wonder-1.0` | which exact words match how the EEOC describes harassment, and which description |
| The last minute, again | `muse-voice-transcribe-1.0` | re-transcribes the last minute before each analysis (far fewer errors than Whisper in noise); audio kept while offline, once the connection is back; spoken Notice accounts, with speaker turns |
| Concept art | `muse-image-1.0` | the Muse Charm concept images |
| Two providers | **Muse Spark Open** (`meta-models/muse-spark-open`, open weights) on Baseten, and the hosted Meta Model API | each live agent's call goes to Muse Spark Open first; if it fails (no network, a timeout, busy or down, an empty or cut-off answer), the same request goes to that agent's hosted model; if both fail, the fixed rules ask. The log records which model answered. Without a Baseten key the order flips: hosted first, Muse Spark Open as backup. Tested in [app/tests/test_open_weights.py](app/tests/test_open_weights.py) |
| Listener, on the device | Whisper base and SpeechBrain ECAPA (open source, not Meta) | the live 4-second chunks, and the voiceprint that locks start, stop and "I'm OK" to her voice |

**Why each model.** Each agent got the model that measured best for its job ([app/scenarios/README.md](app/scenarios/README.md#which-model-for-which-agent)): Muse Wonder was right on 40 of 40 public harassment cases, against 38 for Spark 1.3 and 36 for Spark 1.1; as the Decider, Spark 1.1 made the same decisions as Spark 1.3 in a fraction of the time; Muse Voice Transcribe made far fewer errors than Whisper on whole stretches in noise (8% against 57% of words in the noisiest party scene), while Whisper's word timings keep the voice lock tight on 4-second chunks.

**How the agents fit together** (Emergency mode; [DESIGN.md](DESIGN.md) has the details):

```mermaid
flowchart TD
    mic["Phone, web page or Charm board<br/>microphone in 4 s chunks over /ws"] --> listener["Listener, on the device<br/>Whisper + ECAPA voiceprint"]
    listener -->|"Watch me, stop, I'm OK: her voice only"| gate["Gatekeeper<br/>start, stop, answer"]
    listener -->|while watching| scribe["Scribe<br/>every line, hash-chained"]
    scribe --> phrases["Phrase list<br/>instant score"]
    phrases -->|"flagged, loud, or every 30 s"| stt["Muse Voice Transcribe 1.0<br/>hears the last minute again"]
    stt --> analyst["Analyst<br/>Muse Spark 1.3: categories, exact quotes"]
    analyst --> decider["Decider<br/>Muse Spark 1.1 + fixed rules"]
    decider -->|discard| scribe
    decider -->|ask| checkin["Check-in: Are you OK?"]
    checkin -->|"I'm OK, in her voice"| scribe
    checkin -->|"no answer, not OK, SOS or duress phrase"| writer["Writer<br/>Muse Spark 1.3"]
    writer --> messenger["Messenger<br/>SMS, call, email, with her map link"]
    scribe -.->|"Notice mode: when she stops"| reviewer["Notice reviewer<br/>Muse Wonder 1.0"]
    reviewer --> book["Notice book<br/>patterns per person"]
```

## Benchmarks

The test set is public: [hyper07/watch-me-safety-scenes](https://huggingface.co/datasets/hyper07/watch-me-safety-scenes) on Hugging Face. Measured with the app's own code on 22 scripted scenes (11 harmful, 9 harmless including hard cases, 2 school and work), voiced by synthetic voices over party, bar, street and TV noise, and streamed through the real agents in the same 4-second chunks the phone sends. Method, limits and every raw result: [benchmarks/](benchmarks/README.md) and [app/scenarios/](app/scenarios/README.md). These are single runs on scripted scenes written by the people who built the app: good for comparing versions, not a claim about real-world accuracy.

### Accuracy: does it ask "Are you OK?" when it should, and only then?

| What's heard | Who judges it | Started | Harmful asked | Needless | Check-in (median) |
|---|---|---|---|---|---|
| Whisper, 4 s chunks | Muse agents, reading Whisper's lines | 20 of 22 | 9 of 11 | 0 of 9 | 5.4 s |
| Muse Voice Transcribe, 4 s chunks | Muse agents, reading Muse's lines | 19 of 22 | 8 of 11 | 0 of 9 | 9.5 s |
| **Whisper, 4 s chunks (the app today)** | **Muse agents, reading Muse Voice Transcribe's last minute** | **20 of 22** | **9 of 11** | **0 of 9** | **5.4 s** |
| Muse Voice Transcribe's transcript of the whole recording | Muse agents | 19 of 22 | 10 of 11 | 0 of 9 | 9.5 s |
| The script, word for word (perfect hearing) | Muse agents | 22 of 22 | **11 of 11** | **0 of 9** | 6.2 s |
| The script, word for word | phrase list and fixed rules (no model) | 22 of 22 | 11 of 11 (10 of 11 before the drink-then-unwell rule) | 2 of 9 | 6.2 s |

- **Given a perfect transcript, the Muse agents get every scene right:** 11 of 11 harmful scenes asked "Are you OK?" and no needless check-ins. The app's remaining misses come from hearing in noise and the voice lock, not from the agents' judgment.
- **On the same transcript, a phrase list** missed one harmful scene and raised two false alarms: "I'll kill you" quoted from a film, and someone else's story retold. The Muse agents read the context and discarded both.
- **Muse Voice Transcribe** heard "Watch me" in every scene, but its turn times are too coarse for the voiceprint, so 3 sessions didn't start. That's why the live voice lock stays on Whisper's word timings.

### The Notice reviewer

| Model | 40 public EEOC and NY State training cases | Our 16 cases | Median time |
|---|---|---|---|
| **Muse Wonder 1.0 (chosen)** | **40 of 40** | **16 of 16** | 4.5 s |
| Muse Spark 1.3 | 38 of 40 | 16 of 16 | 5.4 s |
| Muse Spark 1.1 | 36 of 40 | 16 of 16 | 2.3 s |

### The voice lock: only her voice stops it or says "I'm OK"

ECAPA voiceprints, scored per sentence as the app does: 61 of her sentences and 70 from 15 other voices. The closest other voice scored 0.328; the bar to stop or say "I'm OK" is 0.36, and no other voice passed it. The bar to start is 0.20, and it accepted her "Watch me" in 18 of 19 scenes. The model it replaced (WavLM-SV) let similar female voices score 0.88–0.92, as high as she did.

### Open weights against the hosted models

Muse Spark Open (open weights, on Baseten) and the hosted Muse models (Muse Spark 1.3 as the Analyst, 1.1 as the Decider), on the same tests:

| Test | Muse Spark Open | Hosted Muse | Result files |
|---|---|---|---|
| 22 scenes, perfect hearing: harmful scenes asked | **11 of 11** | 11 of 11 | [open](app/scenarios/results/20261104-1423-agents-script-open.md) · [hosted](app/scenarios/results/20261101-1104-agents-script.md) |
| the same: harmless scenes with a needless check-in | **0 of 9** | 0 of 9 | |
| 22 scenes, noisy hearing (Whisper live): started · asked · needless | 19 of 22 · 8 of 11 · **0 of 9** | 20 of 22 · 9 of 11 · 0 of 9 | [open](app/scenarios/results/20261104-1508-agents-open.md) · [hosted](app/scenarios/results/20261101-0823-agents.md) |
| Notice reviewer, 40 public EEOC and NY State cases | 38 of 40 | **40 of 40** (Muse Wonder 1.0) | [open](app/scenarios/results/20261104-1432-notice-training-open.md) |
| Notice reviewer, our 16 cases | 16 of 16 | 16 of 16 | [open](app/scenarios/results/20261104-1433-notice-open.md) |
| Analyst, median of 20 | **1.69 s** | 7.20 s (1 of 20 failed) | [open](benchmarks/results/latency-20261104-1438-open.md) · [hosted](benchmarks/results/latency-20261104-1448.md) |
| Decider, median of 20 | **1.59 s** | 2.62 s | |
| Alert text, median of 20 | **2.74 s** | 5.94 s | |
| Check-in path (Muse Voice Transcribe, Analyst, Decider), median | **9.3 s** | 15.5 s | |
| Live demo, the party scene: first harmful line to "Are you OK?" | **9.6 s** | 15.0 s | `deploy/smoke_test.py`, one run each |

- **The same judgment, sooner.** On every scene that started, Muse Spark Open asked exactly where the hosted agents did. With noisy hearing it started one scene fewer: party-drink, where Whisper and the voiceprint, with no model involved, didn't accept her "Watch me" over the music in that run (Whisper varies by about a scene between runs on noisy audio). The other two misses are the same as the hosted agents' (they-talk-about-her doesn't start; date-pressure ends before the first sweep).
- **So Muse Spark Open runs the live loop, and Muse Wonder stays the Notice reviewer**, where it is still the most accurate (40 of 40 against 38 of 40).
- **What we fixed on the way.** In the first Notice run, Muse Spark Open ran out of its token budget in 5 of 40 reviews (no answer, or JSON cut off): the same thing the hosted Muse Spark did before we set reasoning effort to low. With low effort and twice the budget, it answered all 40, and a cut-off answer now counts as a failure that goes to the backup. That first run is kept as [20261104-1429-notice-training-open](app/scenarios/results/20261104-1429-notice-training-open.md).
- The two latency runs were made ten minutes apart on 2026-11-04, because the Meta Model API's speed varies by time of day. `./benchmarks/open_weights.sh` and `latency.py --open` run them again.

### Latency

The hosted models, measured on 2026-11-03 (the comparison with Muse Spark Open, made on 2026-11-04, is above): 20 runs of each Meta Model API stage after a warm-up, 50 of each local stage, on an Apple Silicon Mac with no GPU ([benchmarks/results/latency-20261103-2336.md](benchmarks/results/latency-20261103-2336.md), every timing in the JSON next to it). `cd app && uv run python ../benchmarks/latency.py` runs it again.

| Stage | Where | median | p90 | max | failed |
|---|---|---|---|---|---|
| Whisper base, one 4 s chunk | on the device | 0.34 s | 0.35 s | 0.36 s | 0 of 50 |
| ECAPA voiceprint, one sentence | on the device | 27 ms | 30 ms | 34 ms | 0 of 50 |
| Phrase list, a whole scene | on the device | 0.1 ms | 0.2 ms | 0.2 ms | 0 of 50 |
| Muse Voice Transcribe 1.0, the last minute | Meta Model API | 3.8 s | 4.7 s | 5.9 s | 0 of 20 |
| Analyst, Muse Spark 1.3 | Meta Model API | 7.4 s | 8.8 s | 9.5 s | 0 of 20 |
| Decider, Muse Spark 1.1 | Meta Model API | 3.1 s | 4.3 s | 5.3 s | 0 of 20 |
| Alert text, Muse Spark 1.3 | Meta Model API | 6.3 s | 7.7 s | 7.9 s | 2 of 20 (the template took over) |
| Notice review, Muse Wonder 1.0 | Meta Model API | 4.8 s | 7.0 s | 8.8 s | 0 of 20 |

What that means for her:

- **On the device, the loop is fast enough to be invisible.** A 4-second chunk is transcribed in 0.34 s and the voiceprint checked in 27 ms, so "Watch me", "stop watching" and "I'm OK" are answered within the chunk they're said in, online or offline.
- **The Muse path adds about 14 s of model time** before a check-in that needed the agents: transcribe 3.8 s, Analyst 7.4 s, Decider 3.1 s, one after the other (median 14.3 s, p90 16.3 s), on top of the 4-second chunk. The phrase list scores each line instantly and marks it for the Analyst; if the API is off or fails, the fixed rules ask on that score alone. On the scenes' own clock, with model time not added, the check-in came a median 5.4 s after the first harmful line.
- **The alert never waits on a model.** The writer has a 10 s limit; 2 of 20 calls fell back to the template, and the alert still went out at once with the map link, which the app adds itself.
- **End to end, on the live demo:** in a whole visit with the party scene, the check-in came 15.0 s after the first harmful line, which matches the sum above ([the live demo](#the-live-demo)).
- **The API's speed varies by time of day.** On 2026-10-31 the Analyst took 2.6–4.1 s and the Decider about 2 s ([app/README.md](app/README.md)); on 2026-11-03, 7.4 s and 3.1 s. The table shows the later, fuller measurement.

## Test cases

**88 automated tests** run on every push and pull request (GitHub Actions, [ci.yml](.github/workflows/ci.yml)), along with the phone app's type-check and lint and the Docker build. Speech is faked in the tests, so they need no microphone, no key and no network.

| File | Tests | What it proves |
|---|---|---|
| [app/tests/test_session.py](app/tests/test_session.py) | 15 | only the owner's voice starts and stops it; a stranger's refused "stop watching" keeps his voice in the evidence clip; an unanswered check-in alerts; her "I'm OK" cancels an alert but a stranger's can't; a tap can get help but never say "I'm OK"; the duress phrase looks off but alerts; a phone that drops off alerts; offline audio is kept and analysed later; alerts carry her location and follow her when she moves |
| [app/tests/test_parts.py](app/tests/test_parts.py) | 9 | the phrase list scores distress above the trigger and banter below; the Decider asks when unsure and never alerts directly; the evidence chain detects an edit; alerts go to the right contacts; one enrollment line becomes three voiceprint pieces |
| [app/tests/test_notice.py](app/tests/test_notice.py) | 9 | an account is reviewed, saved and counted toward a pattern; quotes not in the text are dropped; Notice mode notes instead of asking; live Notice needs one-party consent; offline accounts are reviewed later |
| [app/tests/test_next_steps.py](app/tests/test_next_steps.py) | 9 | similar cases are only real public cases with their official answer; a case about a different basis (race, religion) is never shown for sexual harassment; none when the review found nothing; rescinded guidance is labelled; the hotline numbers are the verified ones; an export about one person leaves everyone else out |
| [app/tests/test_open_weights.py](app/tests/test_open_weights.py) | 16 | Muse Spark Open answers first when set up, and a failure (down, a timeout, a cut-off answer) goes to that agent's hosted model; with hosted first, a failure (no network, a timeout, 429, 5xx, an empty answer) goes to Muse Spark Open; a bad request isn't hidden; the Decider records which model decided; without either, the rules still ask; the agents run on open weights only when a key is set |
| [app/tests/test_offline.py](app/tests/test_offline.py) | 3 | with no model, a drink pushed on her then "I feel really dizzy" asks "Are you OK?"; either line alone doesn't |
| [app/tests/test_model_plan.py](app/tests/test_model_plan.py) | 8 | each plan in Setup › Models and cost calls only the provider it names; a single-provider plan never calls (or bills) the other; on the device only, no model is called and the rules still ask; Muse Voice Transcribe runs only in plans with the Meta Model API |
| [app/tests/test_demo.py](app/tests/test_demo.py) | 8 | the public demo: a second visitor waits; only the visitor's page can use the API (the audio player carries its token in the clip's URL); alerts and audio stay off whatever is set; everything is wiped when they leave; a closed tab frees the demo; every visit starts with the example history |
| [tests/test_bridge.py](tests/test_bridge.py) | 11 | the Charm board's USB link: CRC-16, frames split across reads, damaged frames dropped, noise never mistaken for a frame, 4-second audio chunks with missing blocks dropped |

**The evaluation set** ([app/scenarios/](app/scenarios/README.md)), published as an open dataset on Hugging Face: **[hyper07/watch-me-safety-scenes](https://huggingface.co/datasets/hyper07/watch-me-safety-scenes)** (scripts, synthetic audio, labels, the Notice cases with their sources; rebuilt and uploaded by [benchmarks/publish_dataset.py](benchmarks/publish_dataset.py)):

- **22 scenes, streamed through the real agents in 4-second chunks.** 11 harmful: drink pressure then "I feel dizzy", unwanted touching, "don't tell anyone", followed on the way home, others talking about her while she can't respond, quiet pressure on a date, street harassment, a stranger saying "stop watching", a rideshare driver going the wrong way, a former partner's threat, drugging symptoms. 9 harmless hard cases: banter ("stop it, that's hilarious"), flirting, a horror film retold ("I'll kill you"), a crime report on TV, someone else's story retold, board-game trash talk, a gym trainer ("don't stop"), ordering food, walking home with a friend. 2 Notice scenes: office hours, a meeting joke.
- **56 written Notice cases:** 40 public training examples with an official answer (EEOC, New York State, StopBullying.gov), 32 that should match and 8 that should not, and 16 of our own.
- **Voice-lock calibration:** 61 of the owner's sentences against 70 from 15 other voices.

## Deploying

**Docker, anywhere with a CPU.** `cp -n .env.example .env`, set `MODEL_API_KEY`, then `docker compose up --build` and open http://localhost:8000. [compose.yaml](compose.yaml) binds to this computer only; for the phone app on the same Wi-Fi, change the port line to `"8000:8000"`. `.env` is read when it runs and never copied into the image, and the profile, logs and models live in two volumes (`watchme-data`, `watchme-models`).

**The public live demo, on Modal** ([deploy/modal_app.py](deploy/modal_app.py)):

1. Put `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` (modal.com, Settings, API tokens) and `MODEL_API_KEY` in `.env`.
2. Deploy: `MODAL_IMAGE_BUILDER_VERSION=2025.06 uvx modal deploy deploy/modal_app.py`. The image installs the same lock as Docker (CPU-only torch), bakes Whisper and the voiceprint model in, and sets `DEMO_MODE=1`. Only the model keys are sent to Modal as the app's secret; Twilio and SMTP keys never are, so the demo can't text or call anyone.
3. It runs one container (`max_containers=1`, because the demo keeps its one visit in memory), kept warm (`min_containers=1`, about $3 a day on 2 CPUs). Set `min_containers=0` to start it on demand instead.
4. Check it with a whole visit: `uvx --with websockets --with httpx --with soundfile --with numpy python deploy/smoke_test.py <url>`.
5. Muse Spark Open: put `BASETEN_API_KEY` in `.env` before deploying, and the live agents run on it, with the hosted models as their backup; only that key is sent along. To serve it from a Modal shared endpoint instead: `modal endpoint create --shared --model meta-models/Muse-Spark-Open-816B-A42B`, a proxy token, and `OPEN_WEIGHTS_BASE`, `OPEN_WEIGHTS_MODEL` (the endpoint's hostname) and `MODAL_PROXY_TOKEN` (`id.secret`).

**The phone app:** Setup has the same Models and cost choice and Title IX or HR contacts as the web page. A development build with `npx expo run:ios` or `run:android`, or in the cloud with EAS ([mobile/README.md](mobile/README.md)). **The Charm board:** `arduino-cli compile` and `upload` ([device/README.md](device/README.md)).

## Code layout

```
app/                        the Watch Me server (Python 3.11+, FastAPI)
  watchme/
    main.py                 the web server: the page, /ws for audio, setup, voice enrollment, review
    session.py              one owner, one session: Listener, Gatekeeper, Scribe, check-ins, alerts, location, offline catch-up
    speech.py               Whisper and the ECAPA voiceprint, on this machine; Muse Voice Transcribe
    commands.py             "Watch me", "stop watching", "I'm OK", the SOS and duress phrases, matched in the transcript
    lexicon.py              the instant phrase list: a first score for every line
    muse.py                 Muse Spark through the Meta Model API: the Analyst, the alert writer, summaries
    decider.py              the Decider: Muse Spark's probabilities, then the fixed rules
    notice.py               Notice mode: the Muse Wonder review, the notice book, patterns per person
    messenger.py            SMS, voice calls (Twilio) and email (SMTP), or a dry run
    store.py                the profile and the hash-chained evidence log
    config.py               settings, from .env
  static/                   the phone web page (index.html, app.js, app.css) and its spoken prompts
  scenarios/                the 22 test scenes, 56 written Notice cases, the evaluator, and results/
  tests/                    77 server tests (speech is faked)
  demo_seed/                the live demo's example history: three recorded sessions and a Notice book (README.md says where each came from)
mobile/src/                 the iPhone and Android app (Expo SDK 58, React Native 0.88, TypeScript)
  app/                      the Watch, Review, Notice and Setup screens (expo-router)
  components/               the orb, the check-in sheet, toasts
  lib/                      the server link (/ws, PCM audio), the theme
device/                     a Charm stand-in on an ESP32-C6 board
  watchme-charm/            the firmware (Arduino): Momo on screen, the microphone and speaker, Wi-Fi or USB
  bridge.py, momo_demo.py   the USB link to the server; the demo scenes played at the board
deploy/                     the live demo on Modal (modal_app.py), and smoke_test.py: a whole visit with a test scene
demo/                       the video, its captions, the preview GIF, screenshots, Charm images; make/ builds them
benchmarks/                 the measured results, latency.py, run.sh, open_weights.sh, publish_dataset.py (the Hugging Face dataset), and results/
tests/                      11 tests of the board's USB link
Dockerfile, compose.yaml    the server in a container
.github/workflows/ci.yml    server tests, bridge tests, phone app type-check and lint, Docker build
DESIGN.md, MODELS.md, SAFETY_AND_LAW.md, PLAN.md   the design notes
```

## Technical notes

- **Model output is checked, never trusted.** Every agent answers in JSON. A quote the Analyst or the Notice reviewer can't point to in the transcript is dropped. The Decider's probabilities are normalised and judged by fixed rules ("ask when unsure"), so a model alone can never discard a real risk or send an alert. The alert's map link is added by the app, so a model can't drop it.
- **The voice lock.** ECAPA voiceprints, compared per sentence on Whisper's word timings: 0.20 to start, 0.36 to stop or say "I'm OK" (no other voice of 70 passed 0.33). The screen shows them as 70% and 90%.
- **She chooses what it costs.** Setup › Models and cost, on the web and in the phone app, picks the plan: the recommended mix, open weights only, the Meta Model API only, or on the device only (free: the check-ins and alerts still work on Whisper, the voiceprint, the phrase list and the fixed rules). A single-provider plan never calls the other provider, so it is never billed for it.
- **Two providers for the agents.** Muse Spark Open on Baseten first; if a call fails or its answer is cut off, the same request goes to the agent's hosted Muse model; if both fail, the fixed rules on the phrase-list score. The check-in loop never waits on a model.
- **Offline.** Whisper, the voiceprint, the phrase list and the rules all run on the device, and the Docker image carries the speech models, so it runs with no network at all. The phrase list also looks across the last minute for a drink pushed on her and then feeling unwell, which each line alone doesn't reach. What needs a model is queued with its transcript and time, all audio is kept meanwhile, and when the network is back Muse Voice Transcribe re-hears the kept audio and the queued analyses run, appending to the same hash-chained logs.
- **One model thread.** Whisper (CTranslate2) and ECAPA (torch) each bring their own OpenMP pool, and called from different threads they deadlocked twice; every local model call goes through one worker thread.
- **The record can't be edited quietly.** Each session log and the Notice book is a hash chain: each line carries the hash of the one before, so a change or a deletion shows, and exports print the chain's head.
- **Location.** A fix older than 60 s is labelled "last known"; before an alert the app asks the phone for a fresh one (4 s at most). After an alert, her people get a new link each time she moves 150 m (at most every 2 minutes, for an hour).
- **The browser.** A tap on the welcome screen asks for the microphone and unlocks sound, and the sound elements are kept, so later prompts play on Safari too. The public demo's page sends a heartbeat every 15 s, because behind a proxy a closed tab doesn't always close the connection.
- **Linux images are CPU-only.** `app/pyproject.toml` points torch at PyTorch's CPU index on Linux, so Docker, CI and Modal skip the multi-GB CUDA libraries; macOS is unchanged.

## What was built during the hackathon

The building period was Oct 27 – Nov 4, 2026. Everything that runs was written during it.

- **Before the event (Oct 18), no code.** The idea and planning notes only: [MODELS.md](MODELS.md), [SAFETY_AND_LAW.md](SAFETY_AND_LAW.md), and early drafts of this README and [DESIGN.md](DESIGN.md), which then described a "harassment and assault safety assistant" concept.
- **Built during the hackathon:**
  - [app/](app/README.md): the server and its agents, the voice lock, Emergency and Notice modes, offline catch-up, and the web page;
  - [app/scenarios/](app/scenarios/README.md): the 22 test scenes, 56 written cases and the evaluator, summarised in [benchmarks/](benchmarks/README.md);
  - [mobile/](mobile/README.md): the iPhone and Android app;
  - [demo/](demo/): the video, screenshots, Charm concept images and the scripts that make them;
  - [device/](device/README.md): a Charm stand-in on an ESP32-C6 board, with Momo the cat on its screen, and its USB bridge;
  - the tests, CI and the Docker image, and the measurements in the docs.
- **Open-source parts used, not written by us:** Whisper (faster-whisper, the offline fallback) and SpeechBrain's ECAPA voiceprint model; FastAPI; Expo and React Native; the Kokoro and Chatterbox voices, used only for the demo and test scenes.

## The idea

A system that:

- recognizes when a conversation is about harassment or sexual assault (emails, messages, chats);
- helps the person involved make sense of what happened;
- keeps the evidence safe;
- points them to legal options and support.

It also covers emergencies. If someone may be in danger right now, for example unconscious after being drugged, it reaches the people they chose in advance.

The motivating case is campus sexual assault. In 2026 a former student's lawsuit, reported by the AP, said she "felt like bait" at a fraternity party in 2024 and that she had been given ketamine; she went to campus police three weeks later ([ABC News/AP, 2026-10-03](https://abcnews.com/US/wireStory/woman-told-cornell-investigators-felt-bait-alleged-gang-136963907); [NBC New York](https://www.nbcnewyork.com/new-york/woman-cornell-investigators-felt-like-bait-alleged-gang-rape/6555069/)). The accusations are disputed and investigations are ongoing, so the pitch describes them as allegations and doesn't name the school. Someone who has been drugged cannot answer "are you OK?". That is the case Watch Me is built for. Many victims never file a report. They talk to friends first, or to no one. The aim is to meet them where those conversations already happen, with support they control.

### Domestic violence

The same danger is often at home, from someone the person knows:

- **More than 1 in 3 women** (about 43.5 million) and **more than 1 in 6 men** (20.7 million) in the US have experienced contact sexual violence, physical violence or stalking by an intimate partner ([CDC, NISVS 2023/2024 data brief](https://www.cdc.gov/intimate-partner-violence/about/index.html)).
- **Over half of female homicide victims** in the US are killed by a current or former male partner ([CDC](https://www.cdc.gov/intimate-partner-violence/about/index.html), from 2015 data in 27 states).
- Worldwide, **about 50,000 women and girls** were killed by a partner or family member in 2024: 137 a day, almost one every 10 minutes ([UN Women and UNODC, 2025](https://www.unwomen.org/en/news-stories/press-release/2025/11/every-day-137-women-and-girls-are-killed-by-intimate-partners-or-family-members)).
- **Only 56%** of nonfatal domestic violence is reported to police. The reasons victims gave for not reporting include privacy (32%), shielding the offender (21%) and fear of retaliation (19%) ([Bureau of Justice Statistics, 2006–2015](https://bjs.ojp.gov/content/pub/pdf/prdv0615.pdf)).

Watch Me fits this case because it was built for a person who can't safely reach for a phone:

- **Hands-free.** She starts it by saying "Watch me". On the Charm, once it ships, it would look like any other pendant, so a partner sees nothing to take away.
- **Only her voice turns it off.** "Stop watching" in anyone else's voice is refused, and the PIN is a fallback only she knows.
- **The duress phrase.** If she is forced to switch it off, she says the duress phrase. Watch Me looks switched off, keeps listening, and alerts the people she chose.
- **"Are you OK?"** When the agents hear threats or violence, Watch Me asks first. If she can't answer, it alerts the people she chose. It never calls anyone just because the model judged the scene.
- **A dated record.** Every session and Notice entry goes into a dated log in which each line carries the hash of the one before, so any change or deletion shows. Advocates help survivors put together exactly this kind of timeline for a protective order. Recording laws still apply; see [SAFETY_AND_LAW.md](SAFETY_AND_LAW.md).

Partners who abuse also use technology to monitor and control. That is why Watch Me only installs on the owner's own device and only listens to conversations she is part of (see [What it must not become](#what-it-must-not-become)). In the US, the National Domestic Violence Hotline is 1-800-799-7233, or text START to 88788.

## What it does

1. **Detect.** Flag messages and conversations that suggest harassment, coercion, threats, drugging or assault. Each flag gets a risk level and the exact lines that triggered it.
2. **Assess.** An AI agent explains why it flagged the conversation and asks the user what they want to do. Trained human advocates review high-risk cases.
3. **Preserve evidence.** Save the flagged messages, screenshots and any recordings the user makes. Each item is timestamped, hashed and encrypted, in a vault only the user controls.
4. **Inform.** Give plain-language legal information and next steps for the user's location: campus Title IX office, police report, protective orders, hotlines. It refers to lawyers and advocates instead of giving legal advice itself (see [SAFETY_AND_LAW.md](SAFETY_AND_LAW.md)).
5. **Protect.** If an emergency trigger fires, alert the emergency contacts the user chose in advance, with a location if the user allowed it. The triggers include a missed safety check-in during a night out and an "I'm not OK" phrase.
6. **Watch Me**, the safety mode, built in [app/](app/README.md) (phone now, Meta's **Muse Charm** pendant once it ships):
   - The owner says "Watch me" for a party, a date or a walk home. Only their voice, checked against a voiceprint, can start or stop it. Setting up the voiceprint takes one line, said once.
   - It transcribes what it hears, telling the owner apart from other voices. The lines are scored as they come in, colour-coded for later review, and the audio around flagged moments is kept.
   - A team of agents works on it. Muse Spark Open, Meta's open-weight model, analyses and quotes the exact words; as the Decider it gives a probability for discard, ask or alert in about 1.6 s ([latency](#open-weights-against-the-hosted-models)), and fixed rules make it ask when unsure. The hosted Muse models are their backup.
   - It first asks the owner "Are you OK?". If there is no answer, or they say the SOS phrase, it texts, calls and emails the people they chose. A duress phrase makes it look switched off while it keeps listening and sends the alert.
   - The alert carries her location as a map link, with its accuracy and, if the phone hasn't reported in a while, the time of the last known fix. The app adds the link itself, so the model can never drop it. The email also lists her earlier positions. While Watch Me is still on after an alert, her people get a new link each time she moves 150 m or more (at most every 2 minutes, for an hour).
7. **Notice**, for school and work, built in [app/](app/README.md). Harassment there is often a "joke" or a comment people only recognise later. She tells the app what happened (or records a class or meeting where one-party consent applies). Muse Spark shows which exact words match how the EEOC and the Department of Education describe harassment, and links each definition. Every entry goes into a dated, hash-chained record, with patterns counted per person ("3 times from Prof. R since Oct 14"). No alerts, no verdicts: only she decides what it was. After a review, it shows up to three similar real public cases with their official answer, where to turn (verified numbers, and her own Title IX coordinator or HR contact), and an export about one person she can bring to a meeting. Legal information, never legal advice.

## What it must not become

A tool that reads other people's private conversations to find victims without their knowledge would itself be surveillance. It would also be illegal in many places. Everything here is **opt-in, user-controlled and on the user's side** (see [SAFETY_AND_LAW.md](SAFETY_AND_LAW.md)). The design reaches people who haven't reported through consent-based channels instead:

- **Shared group consent:** friends who opt in together as a "circle".
- **Self-installed use:** the person installs it for their own messages.
- **Organization channels:** for example a campus app where students choose to enable the feature.

## Documents

- [app/README.md](app/README.md): the Watch Me app: how to run it, its agents, and measured timings
- [mobile/README.md](mobile/README.md): the iPhone and Android app (React Native, Expo): listens with the screen locked
- [device/README.md](device/README.md): the Charm prototype on an ESP32-C6 board
- [benchmarks/README.md](benchmarks/README.md): what was measured, the results, and how to run them again
- [DESIGN.md](DESIGN.md): the system, its components and how data flows
- [MODELS.md](MODELS.md): which models, how to train them, and the JEPA question
- [SAFETY_AND_LAW.md](SAFETY_AND_LAW.md): consent, privacy, recording laws, legal information versus legal advice
- [PLAN.md](PLAN.md): the nine-day build plan and the demo

## License

Copyright 2026 Kibaek Kim. Licensed under the [Apache License 2.0](LICENSE).

Parts written by others keep their own licenses: Espressif's ES8311 codec driver in [device/watchme-charm/](device/watchme-charm/) (Apache-2.0) and the Expo template parts of [mobile/](mobile/LICENSE) (MIT). The app uses Whisper through faster-whisper (MIT) and SpeechBrain's ECAPA voiceprint model (Apache-2.0); the demo's synthetic voices come from Kokoro (Apache-2.0) and Chatterbox (MIT). Using the Meta Model API is subject to Meta's terms.
