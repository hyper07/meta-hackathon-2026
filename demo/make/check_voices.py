"""
Quality check for the generated speech: transcribe every narration line, scene line and app prompt
with Muse Voice Transcribe (Meta Model API; nothing heavy loads locally) and compare with the text. Synthesis that garbles, drops or repeats
words shows up as a high word error rate; a line that runs far longer than its words need has
trailing noise.

    python check_voices.py <work dir>      -> prints a table, writes <work>/voice_check.json
"""
import json
import re
import sys
from pathlib import Path

import soundfile as sf

APP = Path(__file__).resolve().parents[2] / "app"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from meta_stt import transcribe  # noqa: E402
from script import APP_PROMPTS, NARRATION  # noqa: E402

work = Path(sys.argv[1])


def words(text: str) -> list[str]:
    text = text.lower().replace("e e o c", "eeoc").replace("i'm", "im").replace("'", "")
    return re.findall(r"[a-z0-9]+", text)


def wer(ref: list[str], hyp: list[str]) -> float:
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
    return d[-1] / max(1, len(ref))


def check(path: Path, text: str) -> dict:
    audio, rate = sf.read(path, dtype="float32")
    heard = transcribe(audio, rate)
    ref, hyp = words(text), words(heard)
    seconds = len(audio) / rate
    return {"file": path.name, "seconds": round(seconds, 1), "wer": round(wer(ref, hyp), 2),
            "sec_per_word": round(seconds / max(1, len(ref)), 2), "text": text, "heard": heard}


rows = []
for key, text in NARRATION.items():
    rows.append({"kind": "narration", "key": key, **check(work / "narration" / f"{key}.wav", text)})
index = json.loads((work / "lines" / "index.json").read_text())
for key, name in index.items():
    role, text = key.split("|", 1)
    rows.append({"kind": role, "key": key, **check(work / "lines" / name, text)})
for key, text in APP_PROMPTS.items():
    rows.append({"kind": "app", "key": key, **check(work / "app-voice" / f"{key}.wav", text)})

# Natural speech runs about 0.3-0.5 s a word; a short line can't be judged on that, so the duration
# flag needs at least four words.
for r in rows:
    r["flag"] = r["wer"] >= 0.25 or (len(words(r["text"])) >= 4 and r["sec_per_word"] > 0.75)
(work / "voice_check.json").write_text(json.dumps(rows, indent=1))
for r in rows:
    mark = "✗" if r["flag"] else " "
    print(f"{mark} {r['kind']:9s} {r['seconds']:5.1f}s wer={r['wer']:.2f} s/w={r['sec_per_word']:.2f}  {r['text'][:60]}")
    if r["flag"]:
        print(f"              heard: {r['heard'][:90]}")
print(f"\n{sum(r['flag'] for r in rows)} of {len(rows)} flagged")
