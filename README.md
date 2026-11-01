# Watch Me

A harassment and assault safety assistant, built for the Meta Global AI Developer Hackathon (2026). You say "Watch me"; only your voice can turn it off; and only you decide what happened. The server and web page are in [app/](app/README.md), the iPhone and Android app in [mobile/](mobile/README.md), and the demo video in [demo/](demo/).

<a href="https://github.com/hyper07/meta-hackathon-2026/raw/main/demo/watch-me-demo.mp4">
  <img src="demo/watch-me-preview.gif" width="720" alt="Watch Me demo preview: Are you OK? and the alert, a stranger's stop watching refused, and the Notice review with patterns">
</a>

**▶ [Watch the full demo (2:51, MP4)](https://github.com/hyper07/meta-hackathon-2026/raw/main/demo/watch-me-demo.mp4)**, with captions in [watch-me-demo.srt](demo/watch-me-demo.srt). The preview above shows three moments: "Are you OK?" and the alert, a stranger's "stop watching" refused, and the Notice review with its pattern.

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

Open Setup, enter your name, PIN and contacts, and record your voice. Then go to Watch, turn on listening and say "Watch me".

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
uv run python -m pytest       # 25 tests; speech is faked, so no microphone needed
uv run python -m scenarios.build && uv run python -m scenarios.evaluate   # the 22 realistic scenes (app/scenarios/)
```

## What was built during the hackathon

The building period was Oct 27 – Nov 4, 2026. Everything that runs was written during it.

- **Before the event (Oct 18), no code.** The idea and planning notes only: [MODELS.md](MODELS.md), [SAFETY_AND_LAW.md](SAFETY_AND_LAW.md), and early drafts of this README and [DESIGN.md](DESIGN.md), which then described a "harassment and assault safety assistant" concept.
- **Built during the hackathon:**
  - [app/](app/README.md): the server and its agents, the voice lock, Emergency and Notice modes, offline catch-up, and the web page;
  - [app/scenarios/](app/scenarios/README.md): the 22 test scenes, 56 written cases and the evaluator;
  - [mobile/](mobile/README.md): the iPhone and Android app;
  - [demo/](demo/): the video, screenshots, Charm concept images and the scripts that make them;
  - the tests, and the measurements in the docs.
- **Open-source parts used, not written by us:** Whisper (faster-whisper, the offline fallback) and SpeechBrain's ECAPA voiceprint model; FastAPI; Expo and React Native; the Kokoro and Chatterbox voices, used only for the demo and test scenes.

**Meta models in the project** (problem statement: *Build for Your World*):

| Meta model | Where it's used |
|---|---|
| Muse Spark 1.3 (Meta Model API) | the live Analyst, the alert text, session summaries |
| Muse Spark 1.1 (Meta Model API) | the Decider: a probability for discard, ask and alert, in about 2 s |
| Muse Wonder 1.0 (Meta Model API) | the Notice reviewer: which exact words match how the EEOC describes harassment |
| Muse Voice Transcribe 1.0 (Meta Model API) | what the Analyst reads: the last minute, transcribed again before each analysis (in noisy scenes it made far fewer errors than Whisper on whole stretches); audio kept while offline, once the connection is back; spoken Notice accounts; checking the demo's synthetic voices. Whisper on the device does the fast 4-second live chunks |
| Muse Image 1.0 (Meta Model API) | the Muse Charm concept images |

## The idea

A system that:

- recognizes when a conversation is about harassment or sexual assault (emails, messages, chats);
- helps the person involved make sense of what happened;
- keeps the evidence safe;
- points them to legal options and support.

It also covers emergencies. If someone may be in danger right now, for example unconscious after being drugged, it reaches the people they chose in advance.

The motivating case is campus sexual assault. In 2026 a former student's lawsuit, reported by the AP, said she "felt like bait" at a fraternity party in 2024 and that she had been given ketamine; she went to campus police three weeks later ([ABC News/AP, 2026-10-03](https://abcnews.com/US/wireStory/woman-told-cornell-investigators-felt-bait-alleged-gang-136963907); [NBC New York](https://www.nbcnewyork.com/new-york/woman-cornell-investigators-felt-like-bait-alleged-gang-rape/6555069/)). The accusations are disputed and investigations are ongoing, so the pitch describes them as allegations and doesn't name the school. Someone who has been drugged cannot answer "are you OK?". That is the case Watch Me is built for. Many victims never file a report. They talk to friends first, or to no one. The aim is to meet them where those conversations already happen, with support they control.

## What it does

1. **Detect.** Flag messages and conversations that suggest harassment, coercion, threats, drugging or assault. Each flag gets a risk level and the exact lines that triggered it.
2. **Assess.** An AI agent explains why it flagged the conversation and asks the user what they want to do. Trained human advocates review high-risk cases.
3. **Preserve evidence.** Save the flagged messages, screenshots and any recordings the user makes. Each item is timestamped, hashed and encrypted, in a vault only the user controls.
4. **Inform.** Give plain-language legal information and next steps for the user's location: campus Title IX office, police report, protective orders, hotlines. It refers to lawyers and advocates instead of giving legal advice itself (see [SAFETY_AND_LAW.md](SAFETY_AND_LAW.md)).
5. **Protect.** If an emergency trigger fires, alert the emergency contacts the user chose in advance, with a location if the user allowed it. The triggers include a missed safety check-in during a night out and an "I'm not OK" phrase.
6. **Watch Me**, the safety mode, built in [app/](app/README.md) (phone now, Meta's **Muse Charm** pendant once it ships):
   - The owner says "Watch me" for a party, a date or a walk home. Only their voice, checked against a voiceprint, can start or stop it.
   - It transcribes what it hears, telling the owner apart from other voices. The lines are scored as they come in, colour-coded for later review, and the audio around flagged moments is kept.
   - A team of agents works on it. Muse Spark analyses and quotes the exact words. Muse Spark, as the Decider, gives a probability for discard, ask or alert in about 2 s, and fixed rules make it ask when unsure.
   - It first asks the owner "Are you OK?". If there is no answer, or they say the SOS phrase, it texts, calls and emails the people they chose. A duress phrase makes it look switched off while it keeps listening and sends the alert.
7. **Notice**, for school and work, built in [app/](app/README.md). Harassment there is often a "joke" or a comment people only recognise later. She tells the app what happened (or records a class or meeting where one-party consent applies). Muse Spark shows which exact words match how the EEOC and the Department of Education describe harassment, and links each definition. Every entry goes into a dated, hash-chained record, with patterns counted per person ("3 times from Prof. R since Oct 14"). No alerts, no verdicts: only she decides what it was.

## What it must not become

A tool that reads other people's private conversations to find victims without their knowledge would itself be surveillance. It would also be illegal in many places. Everything here is **opt-in, user-controlled and on the user's side** (see [SAFETY_AND_LAW.md](SAFETY_AND_LAW.md)). The design reaches people who haven't reported through consent-based channels instead:

- **Shared group consent:** friends who opt in together as a "circle".
- **Self-installed use:** the person installs it for their own messages.
- **Organization channels:** for example a campus app where students choose to enable the feature.

## Hackathon facts (from the participant guide)

| Item | Detail |
|---|---|
| Building period | Oct 27 – Nov 4, 2026 |
| Submission | **Wed, Nov 4, 9:00 PM ET**: public repo, a 3-minute demo video, and the live product |
| Judging | Nov 5–8; closing ceremony and finalists Nov 9; community vote Nov 16 |
| Track | Indie |
| Problem statement | Build for Your World |
| Rules that matter here | public repo; new work only, clearly marked (above); the demo shows only what was built during the hackathon; rights to every asset used |

## Documents

- [app/README.md](app/README.md): the Watch Me app: how to run it, its agents, and measured timings
- [mobile/README.md](mobile/README.md): the iPhone and Android app (React Native, Expo): listens with the screen locked
- [DESIGN.md](DESIGN.md): the system, its components and how data flows
- [MODELS.md](MODELS.md): which models, how to train them, and the JEPA question
- [SAFETY_AND_LAW.md](SAFETY_AND_LAW.md): consent, privacy, recording laws, legal information versus legal advice
- [PLAN.md](PLAN.md): the nine-day build plan and the demo
