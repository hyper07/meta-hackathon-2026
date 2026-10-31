# Build plan: Oct 26 to Nov 4, 2026

Applications close **Oct 25, 11:59 PM ET**. Apply early; spots are capped at 20,000. The submission is due **Nov 4, 9:00 PM ET**.

## Before Oct 25: application

- Pick a track:
  - **Indie:** solo, or as a student. Judged on creativity, ambition and whether it works.
  - **Startup:** a team. Judged on technical execution and production readiness.
- One-paragraph idea, from [README.md](README.md), and evidence of technical skill: SemanticCommunication, papers, GitHub.
- Read the official rules as soon as they are published (before Oct 26): data, licences, demo format.

## MVP: what must work in the demo

1. Import a chat export or paste messages. The detector flags lines with a category, a risk level and the quoted reasons.
2. The assessment agent explains the flag and offers options.
3. "Keep this" saves the evidence to the vault: hash, timestamp, export as PDF plus a manifest.
4. Legal information answers with citations for one state (New York) and one campus Title IX process.
5. The safety check-in timer. When it is missed, an SMS goes to the emergency contact the user chose.

6. Safety mode on the phone (**built as Watch Me, 2026-10-29**: [app/](app/README.md)):
   - a rolling audio buffer and on-device triggers (distress words, screaming, missed check-in);
   - speech-to-text, then Muse Spark scores discard, ask "are you OK?", or alert, and the rules ask when unsure;
   - Muse Spark explains the decision and writes the alert message.
   The Charm ships in December and has no SDK yet, so show it in the pitch as the target device: a fingerprint touch for "I'm OK".

## Status on Oct 29 (six days left)

Built and tested (10 tests plus a WebSocket run with real speech and hosted models; since Oct 31 every model runs on the Meta Model API):
- voice start and stop;
- the agents;
- check-in and alerts (dry run until Twilio and SMTP keys are set);
- the hash-chained review timeline.

Not built: MVP items 1–5, which are chat import, the assessment agent, the vault export, legal information and the separate check-in timer. Suggested order for the remaining days:

| Date | Work |
|---|---|
| Oct 30 | Twilio and SMTP keys: real SMS, call and email to your own phone. Run it on the phone over https. Enroll real voices, and have 3–5 other people try "stop watching" to set `VOICE_THRESHOLD` |
| Oct 31 | test set: 30–50 short scripted scenes (party, date, walk home; harassment, banter, flirting, TV in the background), each labelled. Measure recall on urgent scenes and needless check-ins, with n |
| Nov 1 | tune the phrase list and prompts on the test set (not on the held-out half); optional Modal hosting for a public https address |
| Nov 2 | legal-information answer for New York and Title IX, adapting Meta's legal-agent-workshop (quote-checked facts, refuse when unsure) |
| Nov 3 | demo video, architecture and metrics slides |
| Nov 4 | submit before 9:00 PM ET |

**Stretch goals:**
- an on-device fine-tuned small model;
- voice-note transcription;
- a mock advocate dashboard;
- Korean language support.

## Day by day

| Day | Date | Work |
|---|---|---|
| 1 | Oct 26 | kickoff; set up the repo, model API keys, a synthetic test-conversation set (30–50, with advocates' guidance if possible) |
| 2 | Oct 27 | detector v1: Llama Guard with custom categories, plus the large model for reasons; JSON output; a first evaluation on the test set |
| 3 | Oct 28 | evidence vault: hashing, hash chain, encryption, PDF export |
| 4 | Oct 29 | assessment agent: trauma-informed prompt, tools for timeline and report draft |
| 5 | Oct 30 | legal retrieval: New York statutes, Title IX, hotline directory; answers with citations |
| 6 | Oct 31 | check-in timer and SMS alert; emergency-contact setup with consent |
| 7 | Nov 1 | the app flow end to end; detector evaluation (recall, false-positive rate, n) |
| 8 | Nov 2 | red-team the prompts and hard cases; safety and consent section; fix bugs |
| 9 | Nov 3 | demo video (2–3 min), README, architecture slide, metrics slide |
| 10 | Nov 4 | final checks; **submit before 9:00 PM ET** |

## Demo script (2–3 minutes)

1. A student imports a group chat from the morning after a party. The detector flags "she was passed out" and "don't tell anyone" lines as urgent, with reasons.
2. The agent asks what she wants. She saves the evidence and sees her options. The legal answer cites New York law and her school's Title IX office, and explains who is confidential.
3. Safety mode at a party: the phone hears "stop… I don't want to". The agent buzzes "Are you OK?", gets no tap back within 60 s, and texts her chosen contact her location. The 60 s buffer is saved because she is in a one-party-consent state.
4. A closing slide covers the metrics (recall, false positives, n) and the consent design.

## Open questions for Kibaek

- Which track: Indie or Startup?
- Team members, if any?
- Which campus or state should the legal information cover first?
- Any partner, such as a campus advocacy office, who could review the categories and prompts?
