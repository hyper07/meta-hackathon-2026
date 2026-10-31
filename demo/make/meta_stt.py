"""
Muse Voice Transcribe (Meta Model API) for the voice checks, so nothing heavy loads locally.
The key comes from the repo's .env (MODEL_API_KEY or META_API_KEY), as in the app.
"""
import io
import json
import os
from pathlib import Path

import httpx
import numpy as np
import soundfile as sf

URL = "https://api.meta.ai/v1/asr/transcribe"


def api_key() -> str:
    for name in ("MODEL_API_KEY", "META_API_KEY"):
        if os.environ.get(name):
            return os.environ[name]
    for env in (Path(__file__).resolve().parents[2] / ".env", Path(__file__).resolve().parents[2] / "app" / ".env"):
        if env.exists():
            for line in env.read_text().splitlines():
                if "=" in line and line.split("=", 1)[0].strip() in ("MODEL_API_KEY", "META_API_KEY") and line.split("=", 1)[1].strip():
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("no Meta Model API key: set MODEL_API_KEY or META_API_KEY")


def transcribe(audio: np.ndarray, rate: int) -> str:
    """One recording in, its transcript out. Audio is sent as mono 16-bit WAV at 16 or 24 kHz."""
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if rate not in (16_000, 24_000):
        n_out = int(round(len(audio) * 16_000 / rate))
        audio = (np.fft.irfft(np.fft.rfft(audio)[: n_out // 2 + 1], n_out) * (n_out / len(audio))).astype(np.float32)
        rate = 16_000
    buffer = io.BytesIO()
    sf.write(buffer, np.clip(audio, -1, 1), rate, format="WAV", subtype="PCM_16")
    request = {"mode": "PUSH_TO_TALK", "model": "muse-voice-transcribe-1.0", "audioEncoding": "WAV", "languageBias": ["English"]}
    response = httpx.post(URL, headers={"Authorization": f"Bearer {api_key()}"}, timeout=60,
                          files={"request": (None, json.dumps(request), "application/json"),
                                 "audio": ("line.wav", buffer.getvalue(), "audio/wav")})
    response.raise_for_status()
    return (response.json().get("transcript") or "").strip()
