"""
The two local speech models, loaded once and shared by every session.

  * Whisper (faster-whisper) turns each chunk into text, on this machine.
  * ECAPA-TDNN (speechbrain/spkrec-ecapa-voxceleb) turns a voice into a
    192-number voiceprint; the cosine similarity of two prints says how alike
    the voices are. That is how only the owner can start or stop Watch Me.
    It replaced WavLM-SV (microsoft/wavlm-base-plus-sv) on 2026-10-30: on the
    realistic scenes, WavLM let similar female voices score as high as the
    owner (0.92), while ECAPA kept every other voice below the owner's typical
    score (scenarios/README.md).

Audio everywhere in the app is mono float32 at 16 kHz.
"""

from __future__ import annotations

import asyncio
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from .config import APP_DIR, settings

SAMPLE_RATE = 16_000

# Whisper's well-known inventions on silence and noise. Dropped, never acted on.
_HALLUCINATIONS = {
    "thank you.", "thanks for watching!", "thanks for watching.", "thank you for watching.",
    "you", "bye.", "subtitles by the amara.org community", ".",
}

_lock = threading.Lock()
# Whisper (ctranslate2) and ECAPA (torch) each bring their own OpenMP thread pool. Called
# from different worker threads they can deadlock with no CPU in use, which is how the
# evaluator hung twice. Every model call goes through this one thread.
_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="speech")


async def run(fn, *args):
    """Run a speech-model function off the event loop, on the one speech thread."""
    return await asyncio.get_running_loop().run_in_executor(_worker, fn, *args)
_whisper = None
_sv = None


def dbfs(audio: np.ndarray) -> float:
    """Loudness of a chunk: 0 dBFS is full scale, silence is about -60 or lower."""
    if audio.size == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    return float(20 * np.log10(max(rms, 1e-6)))


def pcm16_to_float(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0


def _load_whisper():
    global _whisper
    with _lock:
        if _whisper is None:
            from faster_whisper import WhisperModel

            _whisper = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
    return _whisper


VOICE_MODEL = "speechbrain/spkrec-ecapa-voxceleb"


def _load_sv():
    global _sv
    with _lock:
        if _sv is None:
            import torch
            from speechbrain.inference.speaker import EncoderClassifier

            _sv = (EncoderClassifier.from_hparams(source=VOICE_MODEL, savedir=str(APP_DIR / ".models" / "ecapa"),
                                                  run_opts={"device": "cpu"}), torch)
    return _sv


def warm_up() -> None:
    """Load both models before the first chunk arrives, so the first command isn't slow."""
    _load_whisper()
    _load_sv()


@dataclass
class Piece:
    """One sentence heard in a chunk, with where it sits in the chunk (seconds)."""
    start: float
    end: float
    text: str


# Which engine made the last live transcript, and why Muse wasn't used if it wasn't. Read by the
# session right after transcribe(); safe because every speech call runs on the one speech thread.
last_engine = "whisper"
last_error: str | None = None
_muse_paused_until = 0.0


def transcribe(audio: np.ndarray, watching: bool = True) -> list[Piece]:
    """
    The chunk's text, split into sentences or speaker turns with their timings. Splitting
    matters: a 4-second chunk often holds the owner and someone else, and each piece gets
    its own voiceprint, so "stop watching" is judged on the voice that said it.

    While watching: Muse Voice Transcribe first (STT_ENGINE=muse, the default with a Meta key), and
    Whisper on this machine when Muse can't be reached, so listening never stops. After a network
    failure Muse is skipped for CATCH_UP_S seconds, so each chunk doesn't wait for a dead connection.
    In standby, only Whisper on this machine: speech is checked for "Watch me" and dropped, and no
    audio leaves the device until the owner turns Watch Me on.
    """
    global last_engine, last_error, _muse_paused_until
    import time

    last_error = None
    use_muse = watching and settings.stt_engine == "muse" and settings.voice_ready
    if use_muse and time.time() >= _muse_paused_until:
        try:
            pieces = transcribe_muse(audio, timeout=settings.stt_timeout)
            last_engine = "muse"
            return pieces
        except Exception as error:   # network, timeout, 429/5xx, or a bad answer: Whisper takes over
            last_error = f"{type(error).__name__}: {str(error)[:120]}"
            _muse_paused_until = time.time() + settings.catch_up_s
    elif use_muse:
        last_error = "Muse Voice Transcribe paused after a failure"
    last_engine = "whisper"
    return transcribe_whisper(audio)


def resume_muse() -> None:
    """The network is back: try Muse again on the next chunk."""
    global _muse_paused_until
    _muse_paused_until = 0.0


def transcribe_muse(audio: np.ndarray, mode: str = "DIARIZATION", timeout: float = 30) -> list[Piece]:
    """
    Muse Voice Transcribe, one request per buffer. DIARIZATION returns speaker turns with
    start and end times (no word timings), which is what the per-piece voiceprint needs.
    The audio leaves this machine only while Watch Me is on, or for a debrief she records.
    """
    import httpx
    import soundfile as sf

    buffer = io.BytesIO()
    sf.write(buffer, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    request = {"mode": mode, "model": "muse-voice-transcribe-1.0", "audioEncoding": "WAV", "languageBias": ["English"]}
    response = httpx.post(settings.voice_url, headers={"Authorization": f"Bearer {settings.voice_api_key}"}, timeout=timeout,
                          files={"request": (None, json.dumps(request), "application/json"),
                                 "audio": ("chunk.wav", buffer.getvalue(), "audio/wav")})
    response.raise_for_status()
    turns = response.json().get("turns") or []
    pieces = [Piece(t.get("startMs", 0) / 1000, t.get("endMs", 0) / 1000, (t.get("transcript") or "").strip()) for t in turns]
    return [p for p in pieces if p.text and p.text.lower() not in _HALLUCINATIONS]


def transcribe_whisper(audio: np.ndarray) -> list[Piece]:
    model = _load_whisper()
    segments, _ = model.transcribe(
        audio,
        language=settings.whisper_language,
        vad_filter=True,
        beam_size=1,
        condition_on_previous_text=False,
        word_timestamps=True,
    )
    pieces: list[Piece] = []
    for segment in segments:
        words: list = []
        for word in segment.words or []:
            words.append(word)
            if word.word.strip().endswith((".", "?", "!")):
                pieces.append(_piece(words))
                words = []
        if words:
            pieces.append(_piece(words))
    return [p for p in pieces if p.text and p.text.lower() not in _HALLUCINATIONS]


def _piece(words) -> Piece:
    return Piece(words[0].start, words[-1].end, "".join(w.word for w in words).strip())


def window(audio: np.ndarray, piece: Piece, minimum: float = 0.8) -> np.ndarray:
    """
    The audio of one sentence, trimmed to its foreground voice, never shorter than `minimum` s.

    Whisper's word times are loose in noise: a "Watch me." that lasts 0.6 s can be stamped
    0.0-2.5 s, and a voiceprint of that window is mostly party music. The phone is on the
    owner, so the sentence is the loudest thing in its window: keep the 20 ms frames within
    12 dB of the loudest, and take the span from the first to the last of them.
    """
    a = max(0, int((piece.start - 0.1) * SAMPLE_RATE))
    b = min(len(audio), int((piece.end + 0.15) * SAMPLE_RATE))
    frame = SAMPLE_RATE // 50
    if b - a >= 4 * frame:
        frames = audio[a:a + (b - a) // frame * frame].reshape(-1, frame)
        level = 10 * np.log10(np.mean(np.square(frames, dtype=np.float64), axis=1) + 1e-12)
        loud = np.flatnonzero(level >= level.max() - 12)
        a, b = a + max(0, loud[0] - 4) * frame, min(b, a + (loud[-1] + 5) * frame)
    short = int(minimum * SAMPLE_RATE) - (b - a)
    if short > 0:
        a, b = max(0, a - short // 2), min(len(audio), b + short - short // 2)
    return audio[a:b]


def voiced(audio: np.ndarray, frame: int = 320) -> np.ndarray:
    """The audio from the first to the last frame with speech in it (louder than 5% of the peak frame)."""
    energy = np.array([np.sqrt(np.mean(audio[i:i + frame] ** 2)) for i in range(0, max(1, len(audio) - frame), frame)])
    if not energy.size or energy.max() <= 0:
        return audio[:0]
    on = np.where(energy > energy.max() * 0.05)[0]
    return audio[on[0] * frame:(on[-1] + 1) * frame]


def enrollment_pieces(audio: np.ndarray, n: int = 3) -> list[np.ndarray]:
    """One spoken line, as n half-overlapping windows of its speech: the voiceprint averages them, and how
    much they agree says whether the recording was clean."""
    speech = voiced(audio)
    width = int(len(speech) / (1 + (n - 1) * 0.5))
    return [speech[int(i * width * 0.5):int(i * width * 0.5) + width] for i in range(n)]


def signature(print_: np.ndarray, size: int = 64) -> list[float]:
    """A coarse 64-number summary of a voiceprint, for drawing it. Not enough to rebuild it."""
    groups = np.asarray(print_, dtype=np.float32)[: len(print_) // size * size].reshape(size, -1).mean(axis=1)
    groups = groups / (np.max(np.abs(groups)) or 1.0)
    return [round(float(v), 3) for v in groups]


def voiceprint(audio: np.ndarray) -> np.ndarray:
    model, torch = _load_sv()
    with torch.no_grad():
        embedding = model.encode_batch(torch.from_numpy(np.ascontiguousarray(audio, dtype=np.float32)).unsqueeze(0))
    embedding = embedding.reshape(-1).numpy().astype(np.float32)
    return embedding / (np.linalg.norm(embedding) or 1.0)


def display_match(similarity: float | None) -> float | None:
    """
    The model's similarity, put on a 0-1 scale people can read: the start bar shows as
    70% and the stop bar as 90%. ECAPA's raw scores are low numbers (the owner is often
    around 0.35), and "verified: 35%" would read as a failure.
    """
    if similarity is None:
        return None
    start, strict = settings.voice_threshold, settings.voice_strict_threshold
    if similarity < start:
        value = 0.70 * max(0.0, similarity) / start
    elif similarity < strict:
        value = 0.70 + 0.20 * (similarity - start) / (strict - start)
    else:
        value = 0.90 + 0.10 * min(1.0, (similarity - strict) / 0.15)
    return round(value, 3)


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
