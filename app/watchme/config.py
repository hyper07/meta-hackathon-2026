"""
Settings, read once from the repo-root .env and then app/.env (app wins).

Every outside service is optional. With no keys the app still runs end to end:
the analyst falls back to the phrase list, the decider to fixed rules, and
alerts are written to the session log instead of being sent ("dry run").
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASETEN = "https://inference.baseten.co"

APP_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = APP_DIR.parent

load_dotenv(REPO_DIR / ".env")
load_dotenv(APP_DIR / ".env", override=True)


def _env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return default


def _float(name: str, default: float) -> float:
    return float(_env(name, default=str(default)))


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", default=str(APP_DIR / "data"))))

    # Muse Spark. The Meta Model API when MODEL_API_KEY is set (variable names as in
    # Meta's legal-agent-workshop); otherwise Muse Spark Open on Baseten. Both are
    # OpenAI-compatible Chat Completions.
    meta_api_key: str | None = field(default_factory=lambda: _env("MODEL_API_KEY", "META_API_KEY", "BASETEN_API_KEY"))
    meta_api_base: str = field(default_factory=lambda: _env(
        "MODEL_API_BASE_URL", "META_API_BASE",
        default="https://api.meta.ai/v1" if _env("MODEL_API_KEY", "META_API_KEY") else BASETEN + "/v1"))
    meta_model: str = field(default_factory=lambda: _env(
        "MODEL_API_MODEL", "META_MODEL",
        default="muse-spark-1.3" if _env("MODEL_API_KEY", "META_API_KEY") else "meta-models/muse-spark-open"))
    # Both reason before they answer. "low" keeps an analysis near 1.5 s on Baseten and 3 s
    # on the Meta API, where the default effort can spend 1,500 tokens and cut the answer off.
    reasoning_effort: str | None = field(default_factory=lambda: _env("LLM_REASONING_EFFORT", default="low") or None)

    # One model per agent role, all on the same API. The live Analyst needs speed; the Notice
    # reviewer runs afterwards and can take longer; the writer drafts alerts and summaries.
    analyst_model: str = field(default_factory=lambda: _env("ANALYST_MODEL", default="") or "")
    # Muse Wonder was the best Notice reviewer: 40 of 40 public training cases and 16 of 16 of ours,
    # median 4.5 s, against 38 and 36 of 40 for Spark 1.3 and 1.1 (scenarios/README.md).
    reviewer_model: str = field(default_factory=lambda: _env(
        "REVIEWER_MODEL", default="muse-wonder-1.0" if _env("MODEL_API_KEY", "META_API_KEY") else "") or "")
    writer_model: str = field(default_factory=lambda: _env("WRITER_MODEL", default="") or "")

    # The fast decision model, POST /v1/systemone: Jev, Kev (local or on Modal), or
    # Baseten's decision models, which answer the same API.
    jev_base_url: str | None = field(default_factory=lambda: _env(
        "JEV_BASE_URL", "KEV_BASE_URL", default=BASETEN if _env("BASETEN_API_KEY") else None))
    jev_api_key: str = field(default_factory=lambda: _env("JEV_API_KEY", "KEV_API_KEY", "BASETEN_API_KEY", default="local"))
    jev_model: str = field(default_factory=lambda: _env(
        "JEV_MODEL", default="decision-models/baseten-mammoth-27b-latest" if _env("BASETEN_API_KEY") and not _env("JEV_BASE_URL") else "kev-latest"))
    jev_min_lift: float = field(default_factory=lambda: _float("JEV_MIN_LIFT", 2.5))
    jev_timeout: float = field(default_factory=lambda: _float("JEV_TIMEOUT", 8))

    # Alerts.
    twilio_sid: str | None = field(default_factory=lambda: _env("TWILIO_ACCOUNT_SID"))
    twilio_token: str | None = field(default_factory=lambda: _env("TWILIO_AUTH_TOKEN"))
    twilio_from: str | None = field(default_factory=lambda: _env("TWILIO_FROM", "TWILIO_PHONE_NUMBER"))
    smtp_host: str | None = field(default_factory=lambda: _env("SMTP_HOST"))
    smtp_port: int = field(default_factory=lambda: int(_env("SMTP_PORT", default="587")))
    smtp_user: str | None = field(default_factory=lambda: _env("SMTP_USER"))
    smtp_password: str | None = field(default_factory=lambda: _env("SMTP_PASSWORD"))
    smtp_from: str | None = field(default_factory=lambda: _env("SMTP_FROM", "SMTP_USER"))

    # Listening.
    # Live speech-to-text: "whisper" (on this machine) or "muse" (Muse Voice Transcribe on the Meta
    # Model API; needs MODEL_API_KEY or META_API_KEY, not a Baseten key). Whisper stays the default
    # live: on the 22 scenes it started 20 against 18, because its word timings give the voice lock
    # tighter clips than Muse's speaker turns. Spoken Notice accounts use Muse whenever a key is set.
    stt_engine: str = field(default_factory=lambda: _env("STT_ENGINE", default="whisper"))
    voice_api_key: str | None = field(default_factory=lambda: _env("MODEL_API_KEY", "META_API_KEY"))
    voice_url: str = field(default_factory=lambda: _env("VOICE_TRANSCRIBE_URL", default="https://api.meta.ai/v1/asr/transcribe"))
    # A sentence still going at the end of a chunk is held and transcribed with the next one,
    # up to this many seconds of audio; 0 turns holding off.
    hold_max_s: float = field(default_factory=lambda: _float("HOLD_MAX_S", 10))
    whisper_model: str = field(default_factory=lambda: _env("WHISPER_MODEL", default="base"))
    whisper_language: str | None = field(default_factory=lambda: _env("WHISPER_LANGUAGE", default="en"))
    # Two bars on ECAPA similarity, because the two mistakes cost different things. Starting
    # Watch Me and tagging a line "you" can be lenient. Stopping it, or answering "I'm OK",
    # must not work for anyone else. From scenarios/, 2026-10-30 (Kokoro voices in noise, 61
    # owner sentences, 70 from 15 other voices): the closest other voice scored 0.328, so the
    # stop bar is 0.36; about half the owner's sentences clear it, so a stop in a loud room
    # may take a second try. The start bar 0.20 accepted "Watch me" in 18 of 19 scenes.
    voice_threshold: float = field(default_factory=lambda: _float("VOICE_THRESHOLD", 0.20))
    voice_strict_threshold: float = field(default_factory=lambda: _float("VOICE_STRICT_THRESHOLD", 0.36))
    silence_dbfs: float = field(default_factory=lambda: _float("SILENCE_DBFS", -50))
    loud_dbfs: float = field(default_factory=lambda: _float("LOUD_DBFS", -12))

    # Agents.
    checkin_timeout_s: float = field(default_factory=lambda: _float("CHECKIN_TIMEOUT_S", 30))
    urgent_checkin_timeout_s: float = field(default_factory=lambda: _float("URGENT_CHECKIN_TIMEOUT_S", 15))
    checkin_cooldown_s: float = field(default_factory=lambda: _float("CHECKIN_COOLDOWN_S", 60))
    review_mark: float = field(default_factory=lambda: _float("REVIEW_MARK", 0.2))
    trigger_score: float = field(default_factory=lambda: _float("TRIGGER_SCORE", 0.45))
    analyst_sweep_s: float = field(default_factory=lambda: _float("ANALYST_SWEEP_S", 30))
    record_after_flag_s: float = field(default_factory=lambda: _float("RECORD_AFTER_FLAG_S", 30))
    # Offline: while the model API can't be reached, every chunk is kept (in clips this long) and the
    # analysis is queued; the catch-up loop retries this often.
    offline_clip_s: float = field(default_factory=lambda: _float("OFFLINE_CLIP_S", 60))
    catch_up_s: float = field(default_factory=lambda: _float("CATCH_UP_S", 30))

    # "one-party": keep audio of flagged moments the owner is part of.
    # "all-party": never keep audio; keep only the text notes.
    recording_rule: str = field(default_factory=lambda: _env("RECORDING_RULE", default="one-party"))

    @property
    def muse_ready(self) -> bool:
        return bool(self.meta_api_key)

    @property
    def jev_ready(self) -> bool:
        return bool(self.jev_base_url)

    @property
    def sms_ready(self) -> bool:
        return bool(self.twilio_sid and self.twilio_token and self.twilio_from)

    @property
    def email_ready(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def keep_audio(self) -> bool:
        return self.recording_rule != "all-party"

    def describe(self) -> dict:
        return {
            "muse_spark": (self.analyst_model or self.meta_model) if self.muse_ready else "not configured (phrase list only)",
            "reviewer": (self.reviewer_model or self.meta_model) if self.muse_ready else "not configured",
            "writer": (self.writer_model or self.meta_model) if self.muse_ready else "templates",
            "debrief_speech": "Muse Voice Transcribe" if self.voice_api_key else f"Whisper {self.whisper_model}",
            "jev": self.jev_base_url if self.jev_ready else "not configured (fixed rules)",
            "sms_and_calls": "Twilio" if self.sms_ready else "dry run",
            "email": self.smtp_host if self.email_ready else "dry run",
            "whisper": "Muse Voice Transcribe" if self.stt_engine == "muse" else f"Whisper {self.whisper_model}",
            "recording_rule": self.recording_rule,
        }


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
