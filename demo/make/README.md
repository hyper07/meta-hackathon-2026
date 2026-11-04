# Making the demo video

The video is a live recording of the real app. Headless Chrome runs the phone page with a scene's audio as its microphone; every frame it paints is saved. Then the frames are cut, captioned and mixed with the narration.

Everything heavy goes in a work directory outside the repo (`$WORK` below).

| Step | Script | Environment |
|---|---|---|
| 1. Reference voices and the list of scene lines | `audio.py refs $WORK` | the app's (`app/.venv`) |
| 2. Narration and scene lines in natural voices | `voices.py $WORK` | Chatterbox: `uv venv; uv pip install chatterbox-tts "setuptools<81"` |
| 2b. The app's own spoken prompts, into `app/static/voice/` | `app_voice.py $WORK` | Chatterbox |
| 3. Scene audio: the new voices over each scene's background | `audio.py scenes $WORK` | the app's |
| 4. Start a demo server, seed it, record the four segments and the services clip | `record.py $WORK` (one segment by hand: `recorder.py $WORK <name> <wav> '<steps>'`) | `uv pip install pillow imageio-ffmpeg numpy soundfile websockets` |
| 5. Cut, caption, mix, encode | `compose.py $WORK out.mp4` (`PREVIEW="2 30"` saves just those frames as PNGs) | same as step 4 |

**Quality check and retries.** `check_voices.py $WORK` transcribes every generated line with Muse Voice Transcribe (Meta Model API) and compares it with the text: a dropped, garbled or repeated word shows up as a high word error rate, and a line that runs far longer than its words need is flagged too. `regen_voices.py $WORK [key ...]` re-synthesizes the flagged lines, up to four tries each, keeping the one whose transcript is closest. This caught her "Stop watching." coming out as "Watching." (which is why her spoken stop didn't work in one take) and a stutter in a narration line.

**One command for the rest.** `TTS_PY=… VIDEO_PY=… python refresh.py $WORK [take ...]` runs check → regenerate → remix the affected scenes → re-record the affected takes (plus any named) → compose → copy into `demo/`. It runs one step at a time and prints each step's peak memory; the build machine's budget is 40 GB, and the heaviest step (Chatterbox on the GPU) uses a few GB.

**Voices:**
- **The narrator** is Chatterbox's own voice (Resemble AI, MIT licence).
- **Each character** (the owner, the person at the party, the stranger, the professor) is Chatterbox cloning a synthetic Kokoro voice, so no real person's voice is copied.
- **Background chatter** keeps Kokoro's voices.
- **Watermark:** Chatterbox adds an inaudible watermark that marks its audio as AI-generated.

**The demo server** (`record.py` does all of this):
- It runs with its own `DATA_DIR`, `CHECKIN_TIMEOUT_S=12` and `URGENT_CHECKIN_TIMEOUT_S=10`, so check-ins fit the video.
- The profile starts with no voiceprint, so the enrollment can be filmed.
- Chrome is given a made-up GPS position (a street in Brooklyn), so the alert on screen shows its map link.
- Two earlier notice entries about "Prof. R" are seeded through `/api/notice/debrief`.
- Between segments, a short "reset" recording stops the session with the PIN.
- On screen, Watch Me is only ever started, stopped and answered by her voice. A take that doesn't start on her "Watch me", or (Notice) doesn't stop on her own stop line, is recorded again; the PIN is used only in the off-camera reset.
- At the end it prints each session's log with times, which is where the cut points in `edit.json` come from.

**Cards:** the title card has the live app starting on the phone beside it, and says, on screen and in the narration, that Watch Me was built during the hackathon. The problem cards show the problem instead of the app: a news card for the lawsuit (paraphrased, with its source; the school is never named) and a chart of partner violence in the US (CDC, BJS), drawn in `compose.py` (`panel_news`, `panel_numbers`). "Under the hood" plays the `services` clip: the running app's own Models and services list, which shows Muse Spark Open. Each take first dismisses the page's microphone-and-sound welcome, as a visitor would. `CARD_PHONE` in `compose.py` sets which footage plays on which card.

**Cuts:** they live in `$WORK/edit.json`, in recording seconds (see `compose.py`). Find the moments with a contact sheet of the frames: when the check-in appears, the alert, the refusal.
