"""
A visit to the live demo, end to end, with a test scene instead of a microphone:
record the voiceprint, say "Watch me", play the party scene in real time, and don't answer "Are you OK?".
Prints what the server sends, and how long after the first harmful line the check-in came.

    uvx --with websockets --with httpx --with soundfile --with numpy \\
        python deploy/smoke_test.py https://<your app>.modal.run [scene-id]

Needs the rendered scenes (app/scenarios/out/, see benchmarks/run.sh). Alerts in the demo are a dry run.
"""
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import soundfile as sf
import websockets

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "scenarios" / "out"
URL = sys.argv[1].rstrip("/")
SCENE = sys.argv[2] if len(sys.argv) > 2 else "party-drink"
SR, CHUNK = 16_000, 4 * 16_000


def pcm16(path: Path) -> bytes:
    audio, rate = sf.read(path, dtype="float32")
    audio = audio if audio.ndim == 1 else audio.mean(axis=1)
    assert rate == SR, rate
    return (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()


async def main() -> None:
    manifest = json.loads((OUT / "manifest.json").read_text())
    scene = next(s for s in manifest["scenes"] if s["id"] == SCENE)
    harm_at = next((l["start"] for l in scene["lines"] if l.get("harm_starts")), None)
    audio = pcm16(OUT / f"{SCENE}.wav")
    events, t0 = [], None

    async with websockets.connect(URL.replace("https://", "wss://") + "/ws", max_size=None) as ws:
        hello = json.loads(await ws.recv())
        demo = json.loads(await ws.recv())
        if demo["type"] != "demo":
            raise SystemExit(f"not admitted: {demo.get('text')}")
        print(f"visit open; services: {hello['services']['muse_spark']}, decider {hello['services']['decider']}, "
              f"alerts {hello['services']['sms_and_calls']}")
        headers = {"X-Visit": demo["visit"]}
        async with httpx.AsyncClient(base_url=URL, headers=headers, timeout=60) as http:
            takes = [base64.b64encode(pcm16(p)).decode() for p in sorted(OUT.glob("_owner_enroll_*.wav"))]
            r = await http.post("/api/enroll", json={"samples": takes})
            print(f"enroll: HTTP {r.status_code}, consistency {r.json().get('consistency')}")

        async def listen() -> None:
            async for raw in ws:
                if isinstance(raw, bytes):
                    continue
                m = json.loads(raw)
                if m["type"] in ("state", "voice", "decision", "checkin", "alert", "checkin_result", "segment"):
                    at = time.monotonic() - t0 if t0 else 0.0
                    events.append((at, m))
                    text = {"segment": lambda: f"[{m.get('speaker')}] {m.get('text')}",
                            "decision": lambda: f"{m.get('action')} {m.get('probabilities')} ({m.get('engine')}, {m.get('ms')} ms)",
                            "checkin": lambda: f"\"Are you OK?\" ({m.get('reason')})",
                            "alert": lambda: f"(dry run) {m.get('results')}",
                            "voice": lambda: f"{m.get('command') or ''} {m.get('outcome') or ''} (match {m.get('match')}) {m.get('text') or ''}",
                            }.get(m["type"], lambda: m.get("state") or m.get("outcome") or "")()
                    print(f"{at:6.1f}s  {m['type']:<14} {str(text)[:110]}", flush=True)

        listener = asyncio.ensure_future(listen())
        t0 = time.monotonic()
        for i in range(0, len(audio), CHUNK * 2):           # real time: one 4-second chunk every 4 seconds
            await ws.send(audio[i:i + CHUNK * 2])
            await asyncio.sleep(4)
        deadline = time.monotonic() + 75                      # the check-in's 30 s, then the alert
        while time.monotonic() < deadline and not any(m["type"] == "alert" for _, m in events):
            await ws.send(json.dumps({"type": "ping"}))     # the page's heartbeat: still here
            await asyncio.sleep(5)
        listener.cancel()

    checkin = next((at for at, m in events if m["type"] == "checkin"), None)
    alert = next((at for at, m in events if m["type"] == "alert"), None)
    print()
    print(f"started by her voice: {any(m['type'] == 'state' and m.get('state') == 'watching' for _, m in events)}")
    if checkin is not None and harm_at is not None:
        print(f"check-in {checkin - harm_at:.1f} s after the first harmful line (at {harm_at:.1f} s in the scene)")
    print(f"alert (dry run): {'yes, ' + format(alert - checkin, '.1f') + ' s after the check-in' if alert and checkin else 'no'}")


if __name__ == "__main__":
    asyncio.run(main())
