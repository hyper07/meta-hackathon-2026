"""
Steps 1 and 3 (app env), the audio the phone's microphone hears.

    python audio.py refs   <work dir>   # Kokoro reference clips + the list of scene lines for voices.py
    python audio.py scenes <work dir>   # mix the Chatterbox lines into each scene, over the scene's background

Scenes keep their script and background noise from app/scenarios; only the voices change. Writes 48 kHz
WAVs for Chrome's fake microphone into <work>/audio, padded with silence so the file doesn't loop mid-take.
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

APP = Path(__file__).resolve().parents[2] / "app"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scenarios import build  # noqa: E402
from scenarios.scenes import SCENES as ALL_SCENES  # noqa: E402
from scenarios.voices import _kokoro_say, _resample  # noqa: E402
from script import ENROLL, REFERENCES, SCENES, STOP_LINE  # noqa: E402

R = 16_000
mode, work = sys.argv[1], Path(sys.argv[2])
scenes = {s.id: s for s in ALL_SCENES}

if mode == "refs":
    (work / "refs").mkdir(parents=True, exist_ok=True)
    sample = ("I'm just saying, you don't have to make this a big deal. Honestly, it's fine. "
              "We can talk about it later, okay? I'll see you there.")
    for role, name in REFERENCES.items():
        sf.write(work / "refs" / f"{role}.wav", _kokoro_say(build.BY_LABEL[f"kokoro:{name}"], sample), R, subtype="PCM_16")
    (work / "refs" / "voices.json").write_text(json.dumps(REFERENCES, indent=2))   # voices.py names its files by these
    lines = [{"ref": SCENES[sid][line[0]], "text": line[1]} for sid in SCENES for line in scenes[sid].lines]
    (work / "scene_lines.json").write_text(json.dumps(lines, indent=2))
    print(len(lines), "scene lines; refs in", work / "refs")
    sys.exit()

index = json.loads((work / "lines" / "index.json").read_text())


def chatterbox(ref: str, text: str) -> np.ndarray:
    audio, rate = sf.read(work / "lines" / index[f"{ref}|{text}"], dtype="float32")
    return _resample(audio, rate, R)


def to48(audio: np.ndarray, name: str, pad_s: float = 45) -> None:
    audio = np.concatenate([audio, np.zeros(int(pad_s * R), np.float32)])
    sf.write(work / "audio" / f"{name}.wav", _resample(audio.astype(np.float32), R, 48_000), 48_000, subtype="PCM_16")


(work / "audio").mkdir(exist_ok=True)
original_speak = build.speak
for sid, roles in SCENES.items():
    scene = scenes[sid]
    by_voice = {}

    def speak(voice, text, _scene=scene, _roles=roles):
        # The scene's own roles get the Chatterbox lines; background chatter keeps its Kokoro voices.
        for role, ref in _roles.items():
            if any(l[0] == role and l[1] == text for l in _scene.lines):
                return chatterbox(ref, text)
        return original_speak(voice, text)

    build.speak = speak
    build.OUT = work / "render"
    entry = build.render(scene, build.KOKORO)
    audio, _ = sf.read(work / "render" / f"{sid}.wav", dtype="float32")
    if sid == "office-hours":   # she ends this one herself, so Notice mode reviews it
        stop = build._at_db(chatterbox("owner", STOP_LINE), -18)
        audio = np.concatenate([audio[: int((entry["lines"][-1]["end"] + 1.5) * R)], stop, np.zeros(R * 8, np.float32)])
    to48(audio, sid)
    (work / "audio" / f"{sid}.json").write_text(json.dumps(entry, indent=2))
    print(sid, f"{len(audio) / R:.1f}s", [(l["role"], l["start"]) for l in entry["lines"]])
build.speak = original_speak

segments = []
for text in ENROLL:
    a = build._at_db(chatterbox("owner", text), -18)
    segments.append(np.pad(a, (int(0.3 * R), max(0, int(6.5 * R) - len(a) - int(0.3 * R)))))
to48(np.concatenate(segments), "enroll", pad_s=0)
print("enroll", [round(len(s) / R, 1) for s in segments])
