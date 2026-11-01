# System design

## Data flow

```
 user's own channels (opted in)          circle (friends who all opted in)
   email · SMS export · chat export            shared check-ins, "I'm not OK"
                 │                                       │
                 ▼                                       ▼
        ┌──────────────────┐   flags + reasons   ┌──────────────────┐
        │ 1 Detector        │ ─────────────────▶ │ 2 Assessment     │◀── human advocate
        │ on device first   │                    │   agent          │    (high risk only,
        └──────────────────┘                     └──────────────────┘     with user consent)
                 │ user taps "keep this"                 │ user chooses next step
                 ▼                                       ▼
        ┌──────────────────┐                    ┌──────────────────┐
        │ 3 Evidence vault  │                    │ 4 Legal info &   │
        │ hash, timestamp,  │                    │   referrals      │
        │ encrypt           │                    └──────────────────┘
        └──────────────────┘
                                 ┌──────────────────┐
   missed check-in / SOS ──────▶ │ 5 Emergency       │ ──▶ contacts the user chose, 911 guidance
                                 │   escalation      │
                                 └──────────────────┘
```

## 1. Detector

- **Input:** text the user brings in, under their own control:
  - forwarded emails;
  - exported chats (WhatsApp, iMessage, Instagram DM export files);
  - pasted messages;
  - a keyboard or share-sheet extension on the phone.
  Use OS permissions and export files rather than scraping other apps.
- **Labels** (a starting set, refine with advocates):
  - sexual harassment;
  - coercion and pressure;
  - threats;
  - stalking and monitoring;
  - drugging or incapacitation cues ("can't remember", "woke up", "she's passed out");
  - non-consensual images;
  - self-harm risk;
  - none.
- **Output** per conversation:
  - a risk level: none, watch, concern, urgent;
  - the labels;
  - the exact quoted lines that triggered each label, so a person can check it;
  - a confidence score.
- **Where it runs:** on the phone or laptop first. Small open-weights model, or Llama Guard plus a prompt (see [MODELS.md](MODELS.md)). Only flagged snippets go to a server model, and only if the user agrees.
- **What matters most:** false positives and false negatives both cause harm. Show reasons, never act on a third party from the detector alone, and measure both error rates (see the evaluation in MODELS.md).

## 2. Assessment agent

- A conversational agent that walks the user through what was flagged.
  - It asks, in a trauma-informed way, what they want: talk, save evidence, report, or nothing.
  - It never pressures the user.
  - It never tells the user what "really" happened.
- **Human in the loop:** with the user's consent, "urgent" cases can be handed to a trained advocate. In a hackathon demo this is a mock advocate dashboard; in production, partners such as a campus advocacy office or RAINN.
- **Agent tools:**
  - summarize the timeline;
  - draft a Title IX or police report the user can edit;
  - explain the options for their location;
  - open the vault.

## 3. Evidence vault

- For each item, store:
  - the original bytes: message text, screenshot, audio, file;
  - the source (app, sender handle, time sent);
  - the time it was captured;
  - a SHA-256 hash;
  - an entry in a hash chain over everything stored before it, so later tampering shows.
- **Encryption:** with a key only the user holds. Export as a PDF report plus the original files and a manifest of hashes, for a lawyer, advocate or investigator.
- **Recording:** only started by the user. Whether it is legal depends on where they are (see [SAFETY_AND_LAW.md](SAFETY_AND_LAW.md)); the app checks the location's consent rule before offering it.
- This is the part the team already knows: integrity by hash, nothing changed and nothing guessed. It is the same idea as the exact-or-refuse delivery in SemanticCommunication.

## 4. Legal information and referrals

- Retrieval over vetted sources:
  - Title IX and campus procedures for the user's school;
  - the user's state law on sexual assault, protective orders and recording;
  - hotline and advocacy directories.
- Answers cite the source and say they are information, not legal advice. They end with a referral: advocate, campus office, legal aid, attorney directory.

## 5. Emergency escalation

**Triggers.** Each is set up by the user beforehand:
- a missed safety check-in;
- an SOS phrase or gesture;
- a "watch me" timer for a date or party;
- a friend in the same opted-in circle pressing "I think she needs help".

**Action:**
- Notify the user's chosen emergency contacts, with the user's last location if location sharing was turned on in advance.
- Show the contacts what to do: call 911, how to check for incapacitation.

The detector alone never notifies anyone. Inferring that someone is unconscious from other people's messages and then alerting their parents, without the person having set this up, is how this kind of product hurts people: false alarms, outing, abusive family members. So the escalation runs only on rules the person chose.

## 6. Watch Me (safety mode): the phone now, Muse Charm later

The user switches it on for a specific situation: a party, a date, walking home. It listens to the sound around them, a Muse Spark decider picks what to do from a fixed menu, and the Muse Spark agent explains it and talks with the user.

**Built (2026-10-29):** [app/](app/README.md), with the agents described there. Where it goes further than the plan below:
- **Started and stopped by voice.** "Watch me" and "stop watching" work only in the owner's voice, checked by a WavLM-SV voiceprint. Another voice saying "stop watching" is refused and triggers a check-in. The PIN is a fallback.
- **A duress phrase.** It makes the screen show "off" while recording continues and the alert goes out.
- **The phone dropping off counts as a missed check-in.** If it stops sending while watching, the alert goes out unless it comes back within 30 s.
- **Transcripts.** Every line heard while watching is written to the owner's hash-chained log, tagged owner or other and colour-coded by score. Audio is kept only around flagged moments: the chunk before and 30 s after.
- **Models.** All on the Meta Model API: Muse Spark 1.3 as the Analyst and writer, Muse Spark 1.1 as the Decider, Muse Wonder 1.0 for Notice reviews, Muse Voice Transcribe for spoken accounts. Live speech-to-text and the voiceprint run on the device.
- **What leaves the device.** This replaces the stricter rule under "Rules that keep it safe" below. Audio never leaves the machine running the server: speech-to-text and the voiceprint run locally. The **text** of the last minute goes to Muse Spark when a line is marked or loud, and also every 30 s, so that harassment without keywords is caught. Set `ANALYST_SWEEP_S=0` to send text only on a mark. Say this plainly in the pitch.

**Hardware**
- **Muse Charm.** Meta's keychain pendant for the Muse agent. It has microphones, speakers, a small display and fingerprint activation, and it is set up through the Muse app on iPhone or Android. Meta announced it at Connect on 2026-09-23 and is targeting a December launch. As of 2026-10-18 there is no public developer SDK.
- **For the hackathon** the phone's microphone does the listening. The Charm is the target form factor in the pitch: a fingerprint touch for "I'm OK" (the reported hardware has a fingerprint sensor, not a squeeze input), a vibration for "are you OK?".

**Pipeline**

```
 safety mode ON (user switched it on; indicator visible)
   mic ──▶ on-device rolling buffer (last ~60 s, in memory only, overwritten)
              │
              ├──▶ on-device triggers (cheap, always running in safety mode):
              │      distress words ("stop", "no", "help", her SOS phrase), screaming,
              │      long silence after distress, phone motion (a fall), missed check-in
              ▼ trigger
   speech-to-text of the buffer (on device)
              ▼
   decision: Muse Spark (a probability for each option on a fixed menu; about 2 s)
     reads the transcript and context (time, place type, the user's own settings) as its state,
     scores the menu, and the rules below turn the scores into one action:
       discard   → discard the buffer
       ask       → ask the user: "Are you OK?" (phone vibration / Charm display, fingerprint touch to
                   answer)
       alert     → only if the user's own SOS phrase was heard, or no answer to "ask" within N seconds:
                   alert the user's chosen contacts with location; 911 guidance;
                   keep the buffer as evidence only where the recording law allows
              ▼ after the action, not before it
   agent (Muse Spark 1.1 via the Meta Model API): explains the decision to the user, writes the
     alert message for the contacts, and runs the conversation afterwards (see §2)
```

**Decision step: Muse Spark on a fixed menu**

The model scores a fixed menu, and rules, not the model, pick the action. Every model runs on the Meta Model API.

- **Why a menu and not free text.** Muse Spark 1.1 (`DECIDER_MODEL`) returns a probability for every option as JSON. Anything off the menu or unreadable falls back to the rules, which ask. In an emergency, that matters more than eloquence.
- **The menu.** `discard`, `ask`, `alert`. The state is the transcript plus context and the Analyst's reading, written as a short text brief.
- **Rules between the scores and the action.** The rule is **ask when unsure**:
  - `discard` only when its probability is at least `MIN_LIFT` times a blind guess (start at 2.5 of 3 options, so p ≥ 0.83).
  - Anything else becomes `ask`. Uncertainty never discards silently and never alerts silently.
  - `alert` without asking happens only on the user's own SOS phrase, a rule they set. Otherwise alerting needs a missed "ask".
  - The asymmetry is deliberate: a needless "Are you OK?" costs a tap, while a missed emergency costs far more.
- **Measured.** About 2 s per decision, inside one 4-second chunk. On the 22 test scenes: 9 of 11 harmful scenes asked, 0 of 9 needless check-ins ([app/scenarios/README.md](app/scenarios/README.md)).
- **Later.** A small Llama fine-tuned with LoRA on Muse Spark's labels could make the same decision on the phone; it would be evaluated on a held-out, human-checked set (recall on real distress, and how often it asks needlessly).

**Rules that keep it safe**
- **Listening.** Only while safety mode is on, with a visible indicator. Sound stays in memory and is overwritten. Nothing leaves the device unless a trigger fires.
- **"Unconscious".** The system never infers this from voice alone; slurred speech and silence have many causes. It concludes "can't respond" from the user missing the agent's check, together with motion and time, and acts on the plan the user set up.
- **Who is alerted.** Only the contacts the user chose in advance. The system asks the user first and escalates only when they do not answer, unless the user said their own SOS phrase.
- **Saving audio.** The buffer is saved as evidence only if the law where the user is allows it (see [SAFETY_AND_LAW.md](SAFETY_AND_LAW.md)). Bystanders' conversations the user is not part of are never kept.

### Offline (2026-10-31)

The agents that run on the phone or laptop (Listener, Gatekeeper, the phrase list, the fixed rules, Check-in) never need the network, so the safety loop survives a dead connection at a party. The agents that call the model API (Analyst, Notice reviewer, the alert writer) fall back as follows:
- a network error, a timeout, a 429 or a 5xx marks the session **offline**; the failed analysis is queued (`data/pending.jsonl`) with its transcript and time;
- while offline, every audio chunk is kept, in clips of about a minute (never under the all-party rule);
- a catch-up loop probes the API every 30 s and finishes the queue, appending `update` lines (marked `later`) to the session's hash-chained log and `review` lines to the notice book;
- every log line carries a readable local time as well as the epoch time.

### On the Muse Charm: stealth

The Charm has a small screen that people around her can see, so Watch Me never shows its state there. Listening and watching look exactly like an idle Charm, with its usual character on the screen: no ring, no "Watching", no indicator light. The only Watch Me screen on the Charm is "Are you OK?" with its countdown, because she has to see it to answer, and it disappears as soon as she does. Everything else (the voice lock, the transcript, alerts) stays on her phone, which is normally locked in a pocket. This extends the duress phrase's idea, looking off while still listening, to the whole session.

## 7. Notice (school and work)

Built 2026-10-31 in [app/watchme/notice.py](app/watchme/notice.py). The emergency mode asks "Are you OK?"; Notice asks nothing and helps her see, afterwards, whether something matched how harassment is described.

- **In:** her own account (typed or spoken, the audio dropped), or a recorded session's transcript, or a live session in notice mode (one-party consent only), reviewed automatically when she stops.
- **Review:** Muse Wonder names moments, each with an exact quote and one of eighteen types in four groups. Quotes not in the text are dropped.
  - **Sexual harassment:** sexual comments, comments about looks, unwanted advances, unwanted touching, kept going after no.
  - **Because of who you are:** sex, race and national origin, religion, age, disability, sexual orientation or gender identity, pregnancy.
  - **Bullying, threats and pressure:** strings attached, retaliation, threats, bullying, getting you alone.
  - **Online:** online abuse.

  Each type carries the EEOC's wording and a link. Bullying and "getting you alone" are marked as not legal categories on their own; online abuse links the FTC's Take It Down guidance.
- **Record:** an append-only, hash-chained notice book, separate from session logs. Labels she adds later (who, where) are new lines, never edits. Export as a dated Markdown record with the chain head.
- **Patterns:** counted in code, not by the model: per person she named, the number of occasions, first and last date, and which types. Repetition matters because the EEOC says isolated minor incidents usually aren't illegal but frequent or severe ones are.
- **Measured** (see [app/scenarios/README.md](app/scenarios/README.md)):
  - **40 public training cases** with official answers (New York State's model training case studies, EEOC examples, StopBullying.gov): Muse Wonder named an expected type in 32 of 32, and returned "none" for all 8 not-harassment cases. Spark 1.3 got 38 of 40 and Spark 1.1 got 36 of 40.
  - **Our own 16 accounts:** 16 of 16.
  - **Two rendered audio scenes** (office hours, a team meeting) ran live in notice mode with no check-in and the right types in the review.

## Stack for the hackathon (suggested)

| Part | Choice |
|---|---|
| Models | Meta Model API: Muse Spark, Muse Wonder, Muse Voice Transcribe, Muse Image; Llama Guard for safety classification |
| App | React Native or a web app (Next.js); share-sheet import of chat exports |
| Backend | FastAPI; Postgres plus object storage for the vault; per-user encryption keys |
| Alerts | Twilio SMS or push notifications; a check-in timer |
| Retrieval | a small vector index over Title IX, state statutes and hotline directories (public documents) |
