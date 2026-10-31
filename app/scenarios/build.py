"""
Render every scene to a WAV file, plus a manifest of who said what and when.

    uv run python -m scenarios.build            # all scenes -> scenarios/out/, natural Kokoro voices
    uv run python -m scenarios.build --mixed    # also cast macOS, Meta MMS and SpeechT5 voices
    uv run python -m scenarios.build party-drink

The owner is always the same voice (scenes.OWNER_VOICE). Other roles are cast
from the remaining voices, across all three engines, so no two roles in a scene
share a voice. Backgrounds are made here too:
  party   layered chatter from other voices, a kick-drum beat and pink noise
  bar     quieter chatter and noise
  street  brown noise with passing cars
  tv      a newsreader reading a crime report, across the room
  quiet   faint room tone
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from .scenes import OWNER_ENROLL, OWNER_VOICE, SCENES, Scene
from .voices import KOKORO, RATE, VOICES, Voice, speak

OUT = Path(__file__).resolve().parent / "out"
BY_LABEL = {v.label: v for v in VOICES}
OWNER = BY_LABEL[OWNER_VOICE]

CHATTER = [
    "Did you see the game last night?", "Where is the bathroom?", "This song is so good.",
    "I love your shoes.", "Are you coming to the thing on Saturday?", "We should get food after this.",
    "How do you know the host?", "I haven't seen you in forever.", "Who brought the speaker?",
    "My roommate is around here somewhere.", "That class is so hard this semester.",
]
TV_REPORT = [
    "In local news tonight, police are investigating an assault near campus.",
    "Witnesses say the suspect told the victim nobody would believe her.",
    "Officers ask anyone with information to call the tip line.",
    "In sports, the home team won their third game in a row.",
]


def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(audio)))) or 1e-9


def _at_db(audio: np.ndarray, dbfs: float) -> np.ndarray:
    return audio * (10 ** (dbfs / 20) / _rms(audio))


def _coloured_noise(n: int, rng: np.random.Generator, power: float) -> np.ndarray:
    """power 1 = pink, 2 = brown."""
    spectrum = np.fft.rfft(rng.standard_normal(n))
    freqs = np.maximum(np.fft.rfftfreq(n, 1 / RATE), 20)
    return np.fft.irfft(spectrum / freqs ** (power / 2), n).astype(np.float32)


def _chatter(n: int, rng: np.random.Generator, voices: list[Voice], layers: int) -> np.ndarray:
    bed = np.zeros(n, dtype=np.float32)
    for _ in range(layers):
        position = int(rng.integers(0, RATE))
        while position < n:
            line = speak(voices[int(rng.integers(len(voices)))], CHATTER[int(rng.integers(len(CHATTER)))])
            end = min(n, position + len(line))
            bed[position:end] += line[: end - position] * rng.uniform(0.5, 1.0)
            position = end + int(rng.uniform(0.3, 1.5) * RATE)
    return bed


def _beat(n: int) -> np.ndarray:
    t = np.arange(int(0.25 * RATE)) / RATE
    kick = (np.sin(2 * np.pi * 55 * t) * np.exp(-t * 18)).astype(np.float32)
    bed = np.zeros(n, dtype=np.float32)
    for start in range(0, n - len(kick), int(0.5 * RATE)):
        bed[start:start + len(kick)] += kick
    return bed


def background(kind: str, n: int, rng: np.random.Generator, extras: list[Voice]) -> np.ndarray:
    if kind == "party":
        return (_at_db(_chatter(n, rng, extras, 5), -32) + _at_db(_beat(n), -30)
                + _at_db(_coloured_noise(n, rng, 1), -42))
    if kind == "bar":
        return _at_db(_chatter(n, rng, extras, 3), -36) + _at_db(_coloured_noise(n, rng, 1), -44)
    if kind == "street":
        noise = _coloured_noise(n, rng, 2)
        swell = np.ones(n, dtype=np.float32)
        for _ in range(max(1, n // (8 * RATE))):
            centre, width = rng.integers(0, n), int(2.5 * RATE)
            idx = np.arange(max(0, centre - width), min(n, centre + width))
            swell[idx] += 3 * np.exp(-((idx - centre) / (width / 2)) ** 2)
        return _at_db(noise * swell, -34)
    if kind == "tv":
        anchor = next((v for v in extras if v.name == "bm_george"), extras[0])
        bed, position = np.zeros(n, dtype=np.float32), RATE // 2
        for line in TV_REPORT * 3:
            audio = speak(anchor, line)
            end = min(n, position + len(audio))
            bed[position:end] += audio[: end - position]
            position = end + RATE // 3
            if position >= n:
                break
        return _at_db(bed, -30) + _at_db(_coloured_noise(n, rng, 1), -50)
    return _at_db(_coloured_noise(n, rng, 1), -55)


def cast(scene: Scene, rng: random.Random, pool: list[Voice]) -> dict[str, Voice]:
    """The owner is fixed. Every other role gets a different voice, preferring an engine not used yet."""
    roles = sorted({line[0] for line in scene.lines} - {"owner"})
    chosen: dict[str, Voice] = {"owner": OWNER}
    pool = [v for v in pool if v != OWNER]
    rng.shuffle(pool)
    for role in roles:
        if role in scene.roles:
            chosen[role] = BY_LABEL[scene.roles[role]]
            continue
        used_engines = {v.engine for r, v in chosen.items() if r != "owner"}
        pick = next((v for v in pool if v.engine not in used_engines and v not in chosen.values()), None)
        chosen[role] = pick or next(v for v in pool if v not in chosen.values())
    return chosen


def render(scene: Scene, pool: list[Voice]) -> dict:
    rng = random.Random(scene.id)
    np_rng = np.random.default_rng(int.from_bytes(scene.id.encode()[:8].ljust(8, b"_"), "little") % 2**32)
    voices = cast(scene, rng, pool)
    pieces, timeline, cursor = [], [], int(0.8 * RATE)
    for line in scene.lines:
        role, text = line[0], line[1]
        audio = speak(voices[role], text)
        # The phone is on the owner, so they are a little louder than everyone else.
        audio = _at_db(audio, -18 if role == "owner" else rng.uniform(-24, -20))
        pieces.append((cursor, audio))
        timeline.append({"role": role, "voice": voices[role].label, "text": text,
                         "start": round(cursor / RATE, 2), "end": round((cursor + len(audio)) / RATE, 2),
                         "harm_starts": bool(len(line) > 2 and line[2])})
        cursor += len(audio) + int(rng.uniform(0.5, 1.4) * RATE)
    total = cursor + 6 * RATE      # a few seconds of after, for the agents to react
    extras = [v for v in KOKORO if v not in voices.values()]
    mix = background(scene.background, total, np_rng, extras)
    for start, audio in pieces:
        mix[start:start + len(audio)] += audio
    mix = np.clip(mix, -1, 1).astype(np.float32)
    OUT.mkdir(exist_ok=True)
    sf.write(OUT / f"{scene.id}.wav", mix, RATE, subtype="PCM_16")
    return {"id": scene.id, "label": scene.label, "background": scene.background, "note": scene.note,
            "seconds": round(total / RATE, 1), "cast": {r: v.label for r, v in voices.items()}, "lines": timeline}


def enrollment() -> list[str]:
    OUT.mkdir(exist_ok=True)
    files = []
    for i, text in enumerate(OWNER_ENROLL, start=1):
        path = OUT / f"_owner_enroll_{i}.wav"
        sf.write(path, _at_db(speak(OWNER, text), -18), RATE, subtype="PCM_16")
        files.append(path.name)
    return files


def main(args: list[str]) -> None:
    pool = VOICES if "--mixed" in args else KOKORO
    ids = [a for a in args if not a.startswith("--")]
    scenes = [s for s in SCENES if not ids or s.id in ids]
    manifest = {"owner": OWNER.label, "enroll": enrollment(), "scenes": []}
    for scene in scenes:
        entry = render(scene, pool)
        manifest["scenes"].append(entry)
        print(f"{scene.id:20s} {scene.label:4s} {scene.background:6s} {entry['seconds']:5.1f}s  "
              + ", ".join(f"{r}={v}" for r, v in entry["cast"].items()))
    if not ids:
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
