"""
Re-synthesize the lines check_voices.py flagged (TTS env). Each gets up to four tries; the one whose
Muse Voice Transcribe transcript is closest to the text wins. Chatterbox is stochastic, so a retry usually fixes a
dropped or garbled word.

    python regen_voices.py <work dir> [key ...]    keys: a narration key, "role|text", or an app prompt key
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import torchaudio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meta_stt import transcribe  # noqa: E402
from script import APP_PROMPTS, EMOTION, NARRATION  # noqa: E402

work = Path(sys.argv[1])
keys = sys.argv[2:] or [r["key"] for r in json.loads((work / "voice_check.json").read_text()) if r["flag"]]
from chatterbox.tts import ChatterboxTTS  # noqa: E402

model = ChatterboxTTS.from_pretrained(device="mps")
REFERENCES = json.loads((work / "refs" / "voices.json").read_text())
APP_VOICE_DIR = Path(__file__).resolve().parents[2] / "app" / "static" / "voice"


def words(text):
    text = text.lower().replace("e e o c", "eeoc").replace("i'm", "im").replace("'", "")
    return re.findall(r"[a-z0-9]+", text)


def wer(ref, hyp):
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
    return d[-1] / max(1, len(ref))


def best_take(text, prompt=None, exaggeration=0.5, tries=4):
    best = None
    for attempt in range(tries):
        wav = model.generate(text, audio_prompt_path=prompt, exaggeration=exaggeration, cfg_weight=0.5)
        audio = wav.squeeze(0).cpu().numpy()
        heard = transcribe(audio, model.sr)
        score = (wer(words(text), words(heard)), len(audio))
        print(f"   try {attempt + 1}: wer={score[0]:.2f} {len(audio) / model.sr:.1f}s  heard: {heard.strip()[:70]}", flush=True)
        if best is None or score < best[0]:
            best = (score, wav)
        if score[0] == 0:
            break
    return best[1], best[0][0]


narr = json.loads((work / "narration" / "lines.json").read_text())
index = json.loads((work / "lines" / "index.json").read_text())
for key in keys:
    print(key)
    if key in NARRATION:
        wav, score = best_take(NARRATION[key])
        torchaudio.save(str(work / "narration" / f"{key}.wav"), wav.cpu(), model.sr)
        narr["seconds"][key] = round(wav.shape[-1] / model.sr, 2)
    elif key in APP_PROMPTS:
        wav, score = best_take(APP_PROMPTS[key], str(work / "refs" / "app.wav"), exaggeration=0.4)
        for folder in (work / "app-voice", APP_VOICE_DIR):
            torchaudio.save(str(folder / f"{key}.wav"), wav.cpu(), model.sr, encoding="PCM_S", bits_per_sample=16)
    elif "|" in key:
        role, text = key.split("|", 1)
        wav, score = best_take(text, str(work / "refs" / f"{role}.wav"), exaggeration=EMOTION.get(text, 0.5))
        name = f"{role}-{REFERENCES[role]}-{hashlib.sha1(text.encode()).hexdigest()[:8]}.wav"
        torchaudio.save(str(work / "lines" / name), wav.cpu(), model.sr)
        index[key] = name
    else:
        print("   unknown key"); continue
    print(f"   kept wer={score:.2f}", flush=True)
    # Saved after every line, so an interrupted run keeps what it finished.
    (work / "narration" / "lines.json").write_text(json.dumps(narr, indent=2))
    (work / "lines" / "index.json").write_text(json.dumps(index, indent=2))
