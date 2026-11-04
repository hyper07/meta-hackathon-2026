# The live demo's example history

Copied into every public demo visit (`DEMO_MODE=1`, see `watchme/store.py: reset_demo`), so Review and Notice
aren't empty. Every file here was made by the app itself, with synthetic voices; nothing was written by hand.

| Example | Where it came from | Audio kept |
|---|---|---|
| `sessions/20261102-205508-a3d1c5` | the party scene recorded for the demo video: drink pressure, "Are you OK?", no answer, the alert with her map link | 48.0 s around the flagged lines |
| `sessions/20261104-082521-665c22` | the stranger scene (`app/scenarios/out/stranger-stop.wav`), streamed in real time through a local server with the real Muse agents: his "stop watching" refused, the urgent check-in, no answer, the alert; then stopped with the PIN | 18.1 s, starting with the chunk with his voice |
| `sessions/20261102-195659-ddf813` | office hours in Notice mode, recorded for the video | none (Notice keeps text) |
| `notice/log.jsonl` | three entries about Prof. R (two seeded accounts and the office-hours session) and one work entry about Manager D, each reviewed by Muse Wonder 1.0 | none |

All alerts were dry runs. The hash chains are intact (`app/tests/test_demo.py` checks them).
