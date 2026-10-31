"""
Voice engines for the scenes.

  kokoro    Kokoro-82M (hexgrad, Apache-2.0): natural neural voices, US and UK English.
            The default cast: scenes should sound like real people.
  say       macOS voices: US, UK, Irish, Australian, South African, Indian English
  mms       Meta's MMS-TTS (facebook/mms-tts-eng): one voice, varied by seed and pace
  speecht5  Microsoft SpeechT5 with CMU Arctic x-vectors: seven speakers

The last three sound synthetic; build.py uses them only with --mixed.

Every engine returns mono float32 at 16 kHz. Lines are cached on disk by
(engine, voice, text), so rebuilding the scenes is fast after the first time.
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf

RATE = 16_000
CACHE = Path(__file__).resolve().parent / ".cache"


@dataclass(frozen=True)
class Voice:
    engine: str
    name: str
    gender: str   # "f" or "m": only for casting lines like "she's out cold"

    @property
    def label(self) -> str:
        return f"{self.engine}:{self.name}"


KOKORO = [
    *(Voice("kokoro", n, "f") for n in ("af_heart", "af_bella", "af_sarah", "af_jessica", "af_kore", "af_nova",
                                        "af_river", "af_aoede", "bf_emma", "bf_isabella", "bf_alice", "bf_lily")),
    *(Voice("kokoro", n, "m") for n in ("am_michael", "am_adam", "am_eric", "am_liam", "am_fenrir", "am_puck",
                                        "am_onyx", "am_echo", "bm_george", "bm_daniel", "bm_lewis", "bm_fable")),
]

LEGACY = [
    *(Voice("say", n, "f") for n in ("Samantha", "Karen", "Moira", "Tessa", "Kathy", "Tara",
                                     "Sandy (English (US))", "Shelley (English (UK))", "Flo (English (US))")),
    *(Voice("say", n, "m") for n in ("Daniel", "Rishi", "Fred", "Ralph", "Albert", "Aman",
                                     "Reed (English (US))", "Rocko (English (US))", "Eddy (English (UK))")),
    Voice("mms", "eng", "m"),
    *(Voice("speecht5", n, "f") for n in ("slt", "clb")),
    *(Voice("speecht5", n, "m") for n in ("awb", "bdl", "jmk", "ksp", "rms")),
]

VOICES = KOKORO + LEGACY


def _resample(audio: np.ndarray, rate_in: int, rate_out: int) -> np.ndarray:
    """Band-limited resampling by FFT (no scipy needed): drop what's above the new Nyquist."""
    n_out = int(round(len(audio) * rate_out / rate_in))
    spectrum = np.fft.rfft(audio)[: n_out // 2 + 1]
    return (np.fft.irfft(spectrum, n_out) * (n_out / len(audio))).astype(np.float32)


@lru_cache(maxsize=2)
def _kokoro(lang: str):
    from kokoro import KPipeline

    return KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")


def _kokoro_say(voice: Voice, text: str) -> np.ndarray:
    pipeline = _kokoro(voice.name[0])          # "a" = American, "b" = British
    speed = 0.95 + (int(hashlib.sha1(text.encode()).hexdigest()[:4], 16) % 4) * 0.05
    audio = np.concatenate([np.asarray(chunk, dtype=np.float32) for _, _, chunk in pipeline(text, voice=voice.name, speed=speed)])
    return _resample(audio, 24_000, RATE)


def _say(voice: Voice, text: str) -> np.ndarray:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "line.wav"
        subprocess.run(["say", "-v", voice.name, "--data-format=LEI16@16000", "-o", str(out), text], check=True)
        audio, rate = sf.read(out, dtype="float32")
    assert rate == RATE
    return audio


@lru_cache(maxsize=1)
def _mms():
    from transformers import AutoTokenizer, VitsModel

    return AutoTokenizer.from_pretrained("facebook/mms-tts-eng"), VitsModel.from_pretrained("facebook/mms-tts-eng").eval()


def _mms_say(voice: Voice, text: str) -> np.ndarray:
    import torch

    tokenizer, model = _mms()
    seed = int(hashlib.sha1(text.encode()).hexdigest()[:8], 16)
    torch.manual_seed(seed)
    model.speaking_rate = 1.0 + (seed % 5 - 2) * 0.05
    with torch.no_grad():
        audio = model(**tokenizer(text.lower(), return_tensors="pt")).waveform[0].numpy()
    assert model.config.sampling_rate == RATE
    return audio.astype(np.float32)


@lru_cache(maxsize=1)
def _speecht5():
    from transformers import SpeechT5ForTextToSpeech, SpeechT5HifiGan, SpeechT5Processor

    return (SpeechT5Processor.from_pretrained("microsoft/speecht5_tts"),
            SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts").eval(),
            SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan").eval())


@lru_cache(maxsize=None)
def _xvector(speaker: str) -> np.ndarray:
    """One utterance's x-vector for a CMU Arctic speaker, from the cached dataset zip."""
    from huggingface_hub import hf_hub_download

    path = hf_hub_download("Matthijs/cmu-arctic-xvectors", "spkrec-xvect.zip", repo_type="dataset")
    with zipfile.ZipFile(path) as z:
        name = sorted(n for n in z.namelist() if f"cmu_us_{speaker}_" in n and n.endswith(".npy"))[0]
        with z.open(name) as f:
            return np.load(f).astype(np.float32)


def _speecht5_say(voice: Voice, text: str) -> np.ndarray:
    import torch

    processor, model, vocoder = _speecht5()
    inputs = processor(text=text, return_tensors="pt")
    speaker = torch.from_numpy(_xvector(voice.name)).unsqueeze(0)
    with torch.no_grad():
        audio = model.generate_speech(inputs["input_ids"], speaker, vocoder=vocoder).numpy()
    return audio.astype(np.float32)


_ENGINES = {"kokoro": _kokoro_say, "say": _say, "mms": _mms_say, "speecht5": _speecht5_say}


def speak(voice: Voice, text: str) -> np.ndarray:
    key = hashlib.sha1(f"{voice.label}|{text}".encode()).hexdigest()[:16]
    cached = CACHE / f"{key}.wav"
    if cached.exists():
        return sf.read(cached, dtype="float32")[0]
    audio = _ENGINES[voice.engine](voice, text)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = (audio / peak * 0.5).astype(np.float32)
    CACHE.mkdir(exist_ok=True)
    sf.write(cached, audio, RATE, subtype="PCM_16")
    return audio
