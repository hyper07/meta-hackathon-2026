"""
Run the pipeline from the voice check to the finished video, one step at a time, and report each
step's peak memory (the whole thing has to stay well under 40 GB on the build machine).

    TTS_PY=<tts venv python> VIDEO_PY=<video venv python> python refresh.py <work dir> [take ...]

Steps: check voices (Muse Voice Transcribe as judge) -> regenerate flagged lines -> remix the scenes
whose lines changed -> re-record those takes, plus any named on the command line -> compose -> copy
into demo/. Narration and app prompts never need a re-take.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
APP_PY = str(ROOT / "app" / ".venv" / "bin" / "python")
TTS_PY, VIDEO_PY = os.environ["TTS_PY"], os.environ["VIDEO_PY"]
work = Path(sys.argv[1]).resolve()
forced = set(sys.argv[2:])
sys.path.insert(0, str(HERE))
from script import ENROLL, SCENES, STOP_LINE  # noqa: E402

sys.path.insert(0, str(ROOT / "app"))
from scenarios.scenes import SCENES as ALL_SCENES  # noqa: E402

TAKE_OF_SCENE = {"party-drink": "party", "stranger-stop": "lock", "office-hours": "notice"}


def run(label, cmd, cwd=None):
    """Run one step under /usr/bin/time -l and report its peak resident memory."""
    print(f"\n== {label}", flush=True)
    proc = subprocess.run(["/usr/bin/time", "-l", *cmd], cwd=cwd, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    peak = re.search(r"(\d+)\s+maximum resident set size", out)
    kept = [l for l in out.splitlines() if l.strip() and not re.search(r"warn|deprecat|pkg_resources|Sampling|sdpa|PerthNet|WeightNorm|LSTM|Redirects|real |user |sys |page|faults|swaps|block|messages|signals|context|instructions|cycles|resident|footprint", l, re.I)]
    print("\n".join(kept[-25:]))
    print(f"-- peak memory {int(peak.group(1)) / 2**30:.1f} GB" if peak else "-- peak memory unknown", flush=True)
    if proc.returncode:
        raise SystemExit(f"{label} failed with exit {proc.returncode}")


def takes_for(keys):
    """Which recorded takes a changed line invalidates."""
    takes = set()
    by_text = {}
    for sid, roles in SCENES.items():
        for line in next(s for s in ALL_SCENES if s.id == sid).lines:
            by_text.setdefault(f"{roles[line[0]]}|{line[1]}", set()).add(TAKE_OF_SCENE[sid])
    for key in keys:
        if "|" not in key:
            continue
        role, text = key.split("|", 1)
        if role == "owner" and text in ENROLL:
            takes.add("enroll")
        if role == "owner" and text == STOP_LINE:
            takes.add("notice")
        takes |= by_text.get(key, set())
    return takes


run("check voices", [APP_PY, str(HERE / "check_voices.py"), str(work)])
flagged = [r["key"] for r in json.loads((work / "voice_check.json").read_text()) if r["flag"]]
if flagged:
    run(f"regenerate {len(flagged)} flagged line(s)", [TTS_PY, str(HERE / "regen_voices.py"), str(work), *flagged])
takes = takes_for(flagged) | forced
if takes & {"party", "lock", "notice", "enroll"}:
    run("remix scenes", [APP_PY, str(HERE / "audio.py"), "scenes", str(work)])
    order = [t for t in ("enroll", "party", "lock", "notice") if t in takes]
    run(f"record {', '.join(order)}", [VIDEO_PY, str(HERE / "record.py"), str(work), *order])
run("compose", [VIDEO_PY, str(HERE / "compose.py"), str(work), str(work / "out" / "watch-me-demo.mp4")])
for name in ("watch-me-demo.mp4", "watch-me-demo.srt"):
    shutil.copy(work / "out" / name, ROOT / "demo" / name)
print("\ncopied to demo/", flush=True)
