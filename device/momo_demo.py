"""
A demo of the Charm board to film: the scenes play from the Mac's speakers, Momo's microphone hears
them, and this prints what Watch Me decides, large enough to film next to the board.

    uvx --with pyserial --with websockets python device/bridge.py /dev/cu.usbmodem1101 > bridge.log
    python3 device/momo_demo.py <demo work dir> bridge.log [--enroll]

The work dir is the one demo/make/ builds (audio/*.wav and lines/). --enroll first plays her setup
line, so the board answers to her (synthetic) voice; without it, the voiceprint already saved is used.

  1. At a party she says "Watch me". Momo's eye sparkles turn to hearts; nothing else shows.
  2. Someone pushes a "special" drink, she feels dizzy. Momo asks "Are you OK?", out loud too.
     She can't answer, so her people are alerted (dry run), and Momo goes straight back to normal.
  3. "Stop watching", in her voice: it stops.
  4. A stranger grabs the phone and says "stop watching": refused, and Momo asks her at once.
     She answers "I'm OK" in her own voice, and Momo is relieved. Then she stops it herself.

Alerts follow the server's settings; the demo server's are dry run.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

WORK, LOG = Path(sys.argv[1]), Path(sys.argv[2])
INDEX = json.loads((WORK / "lines" / "index.json").read_text())
STOP = "Okay, I am heading out now, so you can stop watching."
OK = "I'm OK, I'm fine."

BOLD, DIM, RED, GREEN, BLUE, PINK, END = "\033[1m", "\033[2m", "\033[91m", "\033[92m", "\033[94m", "\033[95m", "\033[0m"


def line(owner_text: str) -> Path:
    return WORK / "lines" / INDEX[f"owner|{owner_text}"]


def play(path: Path, loud: float = 1.0) -> subprocess.Popen:
    return subprocess.Popen(["afplay", "-v", str(loud), str(path)])


def show(text: str, color: str = "") -> None:
    print(f"\n{color}{BOLD}{text}{END}", flush=True)


def note(text: str) -> None:
    print(f"   {DIM}{text}{END}", flush=True)


class Log:
    """Reads the bridge's log from where it is now: only what happens from here on counts."""
    def __init__(self, path: Path) -> None:
        self.file = path.open("rb")
        self.file.seek(0, 2)

    def wait(self, *needles: str, timeout: float = 60) -> str | None:
        end = time.time() + timeout
        while time.time() < end:
            raw = self.file.readline()
            if not raw:
                time.sleep(0.1)
                continue
            text = raw.decode("utf-8", "replace").strip()
            if text.startswith("server:") and any(n in text for n in needles):
                return text[len("server:"):].strip()
        return None


def main() -> None:
    log = Log(LOG)
    print(f"\n{PINK}{BOLD}   Momo  ·  Watch Me on a Charm-sized board{END}")
    note("Everything Momo hears comes from the Mac's speakers. Alerts are in dry run.")
    for n in range(5, 0, -1):
        print(f"\r   starting in {n} …", end="", flush=True)
        time.sleep(1)
    print()

    if "--enroll" in sys.argv:
        show("Setup: she says one line, once", BLUE)
        note('"Watch me. This is my voice, and only I can turn this on or off."')
        play(WORK / "audio" / "enroll.wav").wait()
        saved = log.wait("hello", "state", timeout=15)
        note("Voiceprint saved." if saved is not None else "(no answer from the server yet)")
        time.sleep(2)

    if "--skip-party" in sys.argv:   # rehearse the stranger part alone
        part_four(log)
        return

    # 1–2. The party.
    show("1 · At a party, she says \"Watch me\"", PINK)
    scene = play(WORK / "audio" / "party-drink.wav")
    if log.wait("state watching", timeout=20):
        show("   ✓ Watching. Only her voice can turn it off.", GREEN)
        note("Momo looks the same as always. Only the sparkles in its eyes are hearts now.")
    asked = log.wait("checkin", timeout=60)
    if asked:
        show("2 · \"Are you OK?\"", RED)
        note(f"Muse Spark: {asked.removeprefix('checkin').strip()}")
        note("Momo asks out loud, with a countdown. She is too dizzy to answer.")
    alert = log.wait("alert", timeout=45)
    if alert:
        show("   ✉  No answer: her people are alerted (SMS, call, email — dry run)", RED)
        note(alert.removeprefix("alert").strip())
        note("Momo goes straight back to its usual face: nobody nearby can tell.")
    scene.wait()
    time.sleep(2)

    # 3. She stops it.
    show("3 · She says \"stop watching\"", PINK)
    play(line(STOP), loud=4).wait()
    if log.wait("state standby", timeout=15):
        show("   ✓ Stopped, by her voice", GREEN)
    time.sleep(4)

    part_four(log)


def part_four(log: Log) -> None:
    # 4. A stranger tries to stop it.
    show("4 · Later, someone grabs her phone", PINK)
    scene = play(WORK / "audio" / "stranger-stop.wav", loud=2.5)   # a quieter mix than the party
    log.wait("state watching", timeout=20)
    seen = set()
    while len(seen) < 2:   # the refusal and the check-in, in whichever order they arrive
        event = log.wait("voice stop refused", "checkin", timeout=30)
        if event is None:
            break
        if event.startswith("voice") and "voice" not in seen:
            show("   ✗ \"Stop watching\", not in her voice: refused. Still listening.", RED)
        if event.startswith("checkin") and "checkin" not in seen:
            show("   \"Are you OK?\"  — asked at once", RED)
        seen.add(event.split()[0])
    if "checkin" in seen:
        time.sleep(3.5)                                   # after Momo has finished asking
        play(line(OK), loud=4).wait()
        note('She answers: "I\'m OK, I\'m fine."')
    result = log.wait("checkin_result", "alert", timeout=25)
    if result and "checkin_result" in result and result.endswith("ok") and "not ok" not in result:
        show("   ✓ \"I'm OK\", in her voice. Momo is relieved.", GREEN)
    elif result:
        note(result)
    scene.wait()
    time.sleep(1.5)
    play(line(STOP), loud=4).wait()
    if log.wait("state standby", timeout=15):
        show("   ✓ She stops it herself. Only her voice can.", GREEN)
    print(f"\n{PINK}{BOLD}   You turn it on. Only your voice turns it off. Only you decide what happened.{END}\n")


def volume(level: int | None = None) -> int:
    """The Mac's output volume (0-100); with a level, set it first."""
    if level is not None:
        subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=False)
    out = subprocess.run(["osascript", "-e", "output volume of (get volume settings)"], capture_output=True, text=True)
    return int(out.stdout.strip() or 50)


if __name__ == "__main__":
    before = volume()
    volume(70)            # loud enough for Momo's microphone across a desk
    try:
        main()
    finally:
        volume(before)
