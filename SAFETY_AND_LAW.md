# Safety, consent and law

This product handles the most sensitive data people have. The design choices below are what make it helpful rather than harmful. Judges and any real partner, such as a campus office or an advocacy group, will look for them first.

## Consent and whose data it is

- **Opt-in only.** The user brings in their own conversations. Group features need every member of the circle to opt in.
- **No covert scanning of others.** Reading other people's private messages to find victims who haven't come forward is surveillance. It can break wiretap and computer-access laws and platform terms, and it takes away the victim's control, which is the thing recovery depends on. Reach people who haven't reported by being where they already talk, with their permission: the self-installed app, opted-in friend circles, campus distribution.
- **The user decides every step:** what is saved, whether anyone is told, whether to report. The system suggests, and the user chooses.
- **Emergency contacts are chosen in advance by the user.** Do not notify parents by default. Adults may not want parents told, and for some people family is the danger.

## Privacy and security

- **Processing:** on the device first. Send only what is needed to a server, and only with the user's consent.
- **Encryption:** the evidence vault is encrypted with a key only the user holds. Log access, and make deletion real.
- **Data use:** no training on users' data without explicit, separate consent.
- **Data handling:** minimize what is collected, set retention limits, and have a breach plan.
- **Minors:** under-18 users bring parental-consent and mandatory-reporting rules into play. A hackathon MVP should be **18+**, such as college students.

## Recording laws (check before offering recording)

- **US:**
  - Most states are **one-party consent**: you may record a conversation you are part of. New York is one-party.
  - About a dozen states are **all-party (two-party) consent**, including California, Florida, Illinois, Maryland, Massachusetts, Pennsylvania and Washington. There, recording others without their consent can be a crime and may make the evidence unusable.
- **Outside the US:** the rules differ, for example Korea, EU GDPR and the UK.
- **Product rule:** before offering to record, the app looks up the consent rule for the user's location and explains it. It never records people who are not part of the conversation.

(Verify the state list against a current source before the demo; laws change.)

## Listening to the sound around the user (safety mode)

- **Recording is different from listening.** Listening in memory and discarding is a much smaller step than recording. Keeping audio that includes other people falls under wiretap and eavesdropping laws:
  - In one-party consent places, recording is generally allowed for conversations **the user is part of**.
  - All-party consent states may require everyone's consent.
  - Recording conversations the user is not part of is generally prohibited everywhere.
- **The legal grey zone.** If the user is unconscious, whether they still count as "a party" to a conversation around them is unsettled. Get a lawyer's view before claiming the saved audio is admissible.
- **What the app does:**
  - it keeps sound in a rolling memory buffer;
  - it saves the buffer only on a trigger, and only where the location's rule allows;
  - it shows when it is listening;
  - it never sends ambient audio to a server unless a trigger fired.

## Notice mode (school and work)

- **Debrief first.** "Tell me what happened" only uses the owner's own account, typed or spoken. Nobody else is recorded, and the spoken audio is transcribed and dropped. This is the default way in.
- **Live listening at school or work** records classmates, professors, coworkers. It is refused when `RECORDING_RULE=all-party`, and the screen points to the debrief instead. Many employers and schools also have their own recording policies; the app can't check those.
- **No biometrics of other people.** Only the owner's voiceprint is stored. Illinois's BIPA and similar laws regulate storing voiceprints, so people are named by the owner, by hand, with a name only she recognises.
- **Information, not a verdict.** Each match names a type in the EEOC's own words with a link (eeoc.gov/harassment, eeoc.gov/sexual-harassment, eeoc.gov/retaliation, and the per-characteristic pages). The app never says "you were harassed" or that anyone is guilty. It quotes the EEOC's point that isolated, minor incidents are usually not illegal but frequent or severe ones are, which is why it keeps a dated record.
- **The EEOC's status, 2026.** The EEOC rescinded its 2024 harassment guidance in January 2026, and says its harassment pages are under review. Title VII and the court decisions behind it are unchanged. The app links only the live pages, and uses the rescinded guidance only as a source of test scenarios.
- **Online abuse:** under the Take It Down Act, platforms must remove intimate images shared without consent within 48 hours of a request; if they don't, report it at TakeItDown.ftc.gov (FTC, September 2026). StopNCII.org helps block copies.
- **Deadlines it mentions** are general and sourced: EEOC charges generally within 180 days (longer where state law extends it); the Department of Education's Office for Civil Rights generally within 180 days of the last incident. Title IX regulations have changed between administrations, so the app points to the school's Title IX coordinator rather than quoting rules.

## Legal information versus legal advice

- Only licensed lawyers may give **legal advice**, meaning advice applied to a person's specific situation. Doing it without a licence is the unauthorized practice of law.
- The app gives **legal information**:
  - what the options are: Title IX, police report, protective order;
  - deadlines;
  - what evidence helps;
  - where to get help.
- Every answer cites its source and offers a referral: campus advocate, legal aid, attorney directory, a hotline such as RAINN in the US.
- For Title IX, explain who on campus is a **mandatory reporter**. Telling some staff starts a process; confidential resources, such as counselling or some advocates, do not. Victims often don't know this.

## Harm cases to design against

| Risk | Mitigation |
|---|---|
| False alarm notifies people wrongly | the detector never notifies anyone by itself; alerts come only from user-set rules |
| Abuser uses the app to monitor a partner | install on own device only; no remote reading of others; show when monitoring is active |
| Evidence altered or doubted | hash chain, timestamps, original files kept |
| Model says something hurtful or wrong | trauma-informed prompts, cited sources, escalation to humans, red-team the prompts |
| Data breach | encryption, minimal data, user-held keys |

## Hackathon note

State these choices in the submission: a short "Safety and consent" section and a slide. They show the team understands the domain, and judges score production readiness on the Startup track.
