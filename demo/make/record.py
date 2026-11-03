"""
Step 4 (video env): start a demo server with its own data, seed it, and record the four segments.

    python record.py <work dir>                 # everything, from a fresh profile
    python record.py <work dir> party lock      # redo some segments, keeping the enrolled profile

Needs <work>/audio/*.wav from audio.py. The server runs on port 8778 with short check-in timers.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parents[1] / "app"
work = Path(sys.argv[1]).resolve()
only = sys.argv[2:]
data = work / "server-data"
fresh = not only or not (data / "profile.json").exists()
if fresh:
    subprocess.run(["rm", "-rf", str(data)])
    data.mkdir(parents=True)
    (data / "profile.json").write_text(json.dumps({
    "name": "Alex", "pin": "2468", "sos_phrase": "purple elephant", "duress_phrase": "", "voiceprint": None,
        "contacts": [{"name": "Sam", "phone": "+12125550100", "email": "sam@example.com", "call": True, "relation": "friend", "default": True},
                     {"name": "Mom", "phone": "+12125550101", "email": "", "call": True, "relation": "mom", "default": False}]}, indent=2))
want = lambda name: not only or name in only
if "enroll" in only and not fresh:   # the setup take must start with no voiceprint on screen
    profile = json.loads((data / "profile.json").read_text())
    profile["voiceprint"] = None
    (data / "profile.json").write_text(json.dumps(profile, indent=2))
# Redoing the notice take starts the notice book over, so the live review is the third entry about the same person.
reseed = fresh or "notice" in only
if "notice" in only:
    subprocess.run(["rm", "-rf", str(data / "notice")])

env = {**os.environ, "DATA_DIR": str(data), "CHECKIN_TIMEOUT_S": "12", "URGENT_CHECKIN_TIMEOUT_S": "10"}
server = subprocess.Popen([str(APP / ".venv/bin/uvicorn"), "watchme.main:app", "--host", "127.0.0.1", "--port", "8778"],
                          cwd=APP, env=env, stdout=open(work / "server.log", "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(90):
        try:
            urllib.request.urlopen("http://127.0.0.1:8778/api/status")
            break
        except Exception:
            time.sleep(1)

    def post(path, body):
        req = urllib.request.Request("http://127.0.0.1:8778" + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req).read())

    # Two earlier Notice entries about the same professor, so the live one makes a pattern of three.
    if reseed:
        post("/api/notice/debrief", {"setting": "school", "who": "Prof. R", "where": "after lecture", "when": "2026-10-14T15:10",
         "text": "After lecture Professor R stopped me and said that sweater really suits my figure, and that I should "
                 "wear it to office hours more often. I laughed it off and left."})
        post("/api/notice/debrief", {"setting": "school", "who": "Prof. R", "where": "email", "when": "2026-10-22T21:40",
             "text": "Professor R emailed me at 9:40 at night: Your midterm was disappointing, but I think we can find a way to "
                     "fix that. Come by my office after hours on Friday when it is quiet. Do not mention this to the TA."})

    def record(name, wav, steps):
        subprocess.run([sys.executable, str(HERE / "recorder.py"), str(work), name, str(work / "audio" / wav), json.dumps(steps)], check=True)

    def sessions():
        folder = data / "sessions"
        return set(p.name for p in folder.iterdir()) if folder.exists() else set()

    def stopped_by_voice(session):
        records = [json.loads(l) for l in (data / "sessions" / session / "log.jsonl").read_text().splitlines()]
        return any(r["kind"] == "stop" and "PIN" not in (r.get("detail") or "") for r in records)

    def record_session(name, wav, steps, tries=4, voice_stop=False):
        """A scene take must start a Watch Me session by voice (her "Watch me" over noise is sometimes misheard
        on the first chunk) and, when the scene ends with her "Stop watching", be stopped by her voice too: the
        video never shows the screen being used to start or stop it. Otherwise the take is a dud: reset and
        record it again."""
        for attempt in range(1, tries + 1):
            before = sessions()
            record(name, wav, steps)
            new = sorted(sessions() - before)
            ok = bool(new) and (not voice_stop or stopped_by_voice(new[-1]))
            reset()
            if ok:
                print(f"{name}: session {new[-1]}", flush=True)
                return
            print(f"{name}: {'not stopped by her voice' if new else 'no session started'} (attempt {attempt} of {tries})", flush=True)
        raise SystemExit(f"{name}: no good take in {tries} tries")

    def reset():
        record("reset", "enroll.wav", [["wait", 1], ["js", 'sendJson({type:"stop_pin", pin:"2468"})'], ["wait", 1.5]])

    if want("enroll"):
        record("enroll", "enroll.wav", [
            ["wait", 1], ["js", 'document.querySelector("[data-tab=setup]").click()'], ["wait", 0.8],
            ["js", 'document.querySelector(".enroll-card").scrollIntoView({behavior:"smooth", block:"center"})'], ["wait", 1.5],
            ["mark", "rec1"], ["js", '$("recSample").click()'], ["wait", 10],
            ["mark", "done"], ["wait", 1]])
    assert json.loads((data / "profile.json").read_text()).get("voiceprint"), "no voiceprint: record the enroll segment first"

    if want("party"):
        record_session("party", "party-drink.wav", [["wait", 1.2], ["mark", "mic"], ["js", '$("micButton").click()'], ["wait", 54], ["mark", "end"]])
    if want("lock"):
        record_session("lock", "stranger-stop.wav", [["wait", 1.2], ["mark", "mic"], ["js", '$("micButton").click()'], ["wait", 30], ["mark", "end"]])
    if want("notice"):
        record_session("notice", "office-hours.wav", [
            ["wait", 1.0], ["mark", "mode"], ["js", 'document.querySelector("#modeSwitch [data-mode=notice]").click()'], ["wait", 1.5],
            ["mark", "mic"], ["js", '$("micButton").click()'], ["wait", 44],
            ["mark", "stopped"], ["js", 'state'], ["wait", 9],
            ["mark", "tab"], ["js", 'document.querySelector("[data-tab=notice]").click()'], ["wait", 1.5],
            ["js", '$("ntResult").scrollIntoView({behavior:"smooth"})'], ["wait", 5],
            ["mark", "label"], ["js", '(() => { const b=document.querySelector(".nt-label"); if (b) b.scrollIntoView({behavior:"smooth", block:"center"}); return !!b })()'], ["wait", 1.5],
            ["js", '(() => { const b=document.querySelector(".nt-label"); b.querySelector("[data-k=who]").value="Prof. R"; b.querySelector("[data-k=where]").value="office hours"; return 1 })()'], ["wait", 1.2],
            ["js", '(() => { document.querySelector(".nt-label button").click(); return 1 })()'], ["wait", 2.5],
            ["mark", "patterns"], ["js", '$("ntPatterns").scrollIntoView({behavior:"smooth"})'], ["wait", 6],
            ["mark", "end"]], voice_stop=True)
finally:
    server.terminate()

# What happened in each session, for choosing the cuts.
for folder in sorted((data / "sessions").iterdir()):
    records = [json.loads(l) for l in (folder / "log.jsonl").read_text().splitlines()]
    t0 = records[0]["t"]
    print(f"\n== {folder.name}")
    for r in records:
        if r["kind"] in ("segment", "update"):
            print(f"{r['t'] - t0:5.1f} {r['kind']:9s} {r.get('speaker', ''):6s} {r.get('score', '')!s:5s} {(r.get('text') or r.get('reason') or '')[:70]}")
        else:
            print(f"{r['t'] - t0:5.1f} {r['kind']:9s} {(r.get('detail') or r.get('action') or '')[:90]}")
