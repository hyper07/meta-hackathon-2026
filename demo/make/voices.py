"""
Step 2 (TTS env): speak the narration and every scene line with Chatterbox (Resemble AI, MIT).
The narrator is Chatterbox's own voice; each character clones a Kokoro reference from step 1.
Chatterbox adds an inaudible watermark marking the audio as AI-generated.

    python voices.py <work dir>
"""
import hashlib
import json
import sys
from pathlib import Path

import torchaudio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script import EMOTION, ENROLL, NARRATION, STOP_LINE  # noqa: E402

work = Path(sys.argv[1])
from chatterbox.tts import ChatterboxTTS  # noqa: E402

model = ChatterboxTTS.from_pretrained(device="mps")

# Already-made audio is kept, so changing one voice or one line only re-synthesizes that part.
(work / "narration").mkdir(parents=True, exist_ok=True)
old = json.loads((work / "narration" / "lines.json").read_text()) if (work / "narration" / "lines.json").exists() else {"lines": {}, "seconds": {}}
seconds = {}
for key, text in NARRATION.items():
    path = work / "narration" / f"{key}.wav"
    if path.exists() and old["lines"].get(key) == text:
        seconds[key] = old["seconds"][key]
        continue
    wav = model.generate(text, exaggeration=0.5, cfg_weight=0.5)
    torchaudio.save(str(path), wav.cpu(), model.sr)
    seconds[key] = round(wav.shape[-1] / model.sr, 2)
    print(f"narration {key:8s} {seconds[key]:5.1f}s", flush=True)
(work / "narration" / "lines.json").write_text(json.dumps({"lines": NARRATION, "seconds": seconds}, indent=2))

lines = json.loads((work / "scene_lines.json").read_text())   # written by step 1: [{"ref": ..., "text": ...}]
lines += [{"ref": "owner", "text": t} for t in ENROLL + [STOP_LINE]]
(work / "lines").mkdir(exist_ok=True)
index_path = work / "lines" / "index.json"
index = json.loads(index_path.read_text()) if index_path.exists() else {}
# A line is keyed by role and text, and the file name carries the reference voice, so a role recast re-synthesizes.
REFERENCES = json.loads((work / "refs" / "voices.json").read_text())
for line in lines:
    key = f"{line['ref']}|{line['text']}"
    name = f"{line['ref']}-{REFERENCES[line['ref']]}-{hashlib.sha1(line['text'].encode()).hexdigest()[:8]}.wav"
    if index.get(key) == name and (work / "lines" / name).exists():
        continue
    wav = model.generate(line["text"], audio_prompt_path=str(work / "refs" / f"{line['ref']}.wav"),
                         exaggeration=EMOTION.get(line["text"], 0.5), cfg_weight=0.5)
    torchaudio.save(str(work / "lines" / name), wav.cpu(), model.sr)
    index[key] = name
    print(f"line {line['ref']:9s} {wav.shape[-1] / model.sr:4.1f}s  {line['text']}", flush=True)
index_path.write_text(json.dumps(index, indent=2))
