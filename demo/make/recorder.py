"""
Step 4 (video env): record one segment of the demo. Headless Chrome opens the phone page with the given WAV
as its microphone; a CDP screencast saves every frame it paints, with times; scripted steps drive the page.

    python recorder.py <work dir> <name> <mic.wav> '<steps json>'   (server on http://127.0.0.1:8778)
steps: ["js", code] | ["wait", seconds] | ["mark", label]
Writes <work>/rec/<name>/frames/*.jpg and log.json (frame times and marks, seconds from the start).
Wrap multi-statement js in an arrow function: top-level const/let persist between steps.
"""
import asyncio
import base64
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websockets

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
URL = "http://127.0.0.1:8778/"
work, name, wav, steps = Path(sys.argv[1]), sys.argv[2], str(Path(sys.argv[3]).resolve()), json.loads(sys.argv[4])
out = work / "rec" / name
shutil.rmtree(out, ignore_errors=True)
(out / "frames").mkdir(parents=True)
profile = work / "rec" / f".chrome-{name}"
shutil.rmtree(profile, ignore_errors=True)

# A fresh DevTools port every time. With a fixed port, a take that started while the previous Chrome was
# still shutting down attached to that old instance, and so heard the old take's microphone file.
with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]

proc = subprocess.Popen([
    CHROME, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
    "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", f"--use-file-for-fake-audio-capture={wav}",
    "--autoplay-policy=no-user-gesture-required", "--disable-features=AudioServiceOutOfProcess,AudioServiceSandbox",
    "--window-size=430,932", "--force-device-scale-factor=2", "--hide-scrollbars", "--force-dark-mode", "about:blank"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def main():
    for _ in range(50):
        try:
            tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
            break
        except Exception:
            time.sleep(0.2)
    ws_url = next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page")
    async with websockets.connect(ws_url, max_size=None) as ws:
        pending, n = {}, 0
        frames, marks = [], []
        t0 = None

        async def reader():
            async for raw in ws:
                m = json.loads(raw)
                if "id" in m and m["id"] in pending:
                    pending.pop(m["id"]).set_result(m.get("result", m.get("error")))
                elif m.get("method") == "Page.screencastFrame":
                    p = m["params"]
                    path = out / "frames" / f"{len(frames):05d}.jpg"
                    path.write_bytes(base64.b64decode(p["data"]))
                    frames.append({"t": round(time.monotonic() - t0, 3) if t0 else 0.0, "file": path.name})
                    asyncio.ensure_future(call("Page.screencastFrameAck", sessionId=p["sessionId"]))

        async def call(method, **params):
            nonlocal n
            n += 1
            fut = asyncio.get_running_loop().create_future()
            pending[n] = fut
            await ws.send(json.dumps({"id": n, "method": method, "params": params}))
            return await fut

        task = asyncio.ensure_future(reader())
        await call("Emulation.setDeviceMetricsOverride", width=430, height=932, deviceScaleFactor=2, mobile=True)
        await call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
        await call("Page.enable")
        await call("Page.navigate", url=URL)
        await asyncio.sleep(2.5)
        t0 = time.monotonic()
        await call("Page.startScreencast", format="jpeg", quality=85, maxWidth=860, maxHeight=1864, everyNthFrame=1)
        for action, arg in steps:
            if action == "js":
                r = await call("Runtime.evaluate", expression=arg, awaitPromise=True, returnByValue=True)
                if r.get("exceptionDetails"):
                    print("js error:", arg[:60], r["exceptionDetails"].get("text"), file=sys.stderr)
            elif action == "wait":
                await asyncio.sleep(arg)
            elif action == "mark":
                marks.append({"label": arg, "t": round(time.monotonic() - t0, 3)})
        await call("Page.stopScreencast")
        await asyncio.sleep(0.3)
        task.cancel()
        (out / "log.json").write_text(json.dumps({"frames": frames, "marks": marks,
                                                  "end": round(time.monotonic() - t0, 3)}, indent=1))
        print(f"{name}: {len(frames)} frames over {time.monotonic() - t0:.1f}s", marks)

try:
    asyncio.run(main())
finally:
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    shutil.rmtree(profile, ignore_errors=True)
