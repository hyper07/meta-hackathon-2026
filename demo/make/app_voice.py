"""
Step 2b (TTS env): the app's own spoken prompts, in a natural voice, as files the page plays.

    python app_voice.py <work dir>

Writes app/static/voice/<name>.wav (24 kHz, 16-bit) and a copy in <work>/app-voice for the video mix.
The voice is Chatterbox cloning a synthetic Kokoro voice (refs/app.wav from audio.py), so it's nobody real.
"""
import shutil
import sys
from pathlib import Path

import torchaudio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script import APP_PROMPTS  # noqa: E402

work = Path(sys.argv[1])
out = Path(__file__).resolve().parents[2] / "app" / "static" / "voice"
out.mkdir(parents=True, exist_ok=True)
(work / "app-voice").mkdir(exist_ok=True)
from chatterbox.tts import ChatterboxTTS  # noqa: E402

model = ChatterboxTTS.from_pretrained(device="mps")
for name, text in APP_PROMPTS.items():
    wav = model.generate(text, audio_prompt_path=str(work / "refs" / "app.wav"), exaggeration=0.4, cfg_weight=0.5)
    torchaudio.save(str(out / f"{name}.wav"), wav.cpu(), model.sr, encoding="PCM_S", bits_per_sample=16)
    shutil.copy(out / f"{name}.wav", work / "app-voice" / f"{name}.wav")
    print(f"{name:12s} {wav.shape[-1] / model.sr:4.1f}s  {text}", flush=True)
