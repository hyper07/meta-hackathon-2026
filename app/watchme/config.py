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


def _shown(model: str) -> str:
    return "muse-spark-open (open weights)" if model == "open" else model


def _open_first(hosted: str) -> str:
    """The live agents run on Muse Spark Open when it's set up (a key for it), else on the hosted model."""
    return "open" if _env("OPEN_WEIGHTS_API_KEY", "BASETEN_API_KEY", "MODAL_PROXY_TOKEN") else hosted


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", default=str(APP_DIR / "data"))))

    # Every model agent runs on the Meta Model API (variable names as in Meta's legal-agent-workshop;
    # OpenAI-compatible Chat Completions).
    meta_api_key: str | None = field(default_factory=lambda: _env("MODEL_API_KEY", "META_API_KEY"))
    # Muse Spark Open: Meta's open-weight model, served by Baseten Model APIs (OpenAI-compatible), or by any
    # endpoint that serves it (a Modal shared endpoint: OPEN_WEIGHTS_BASE=https://inference.us-west.modal.direct/v1,
    # OPEN_WEIGHTS_MODEL=<its hostname>, MODAL_PROXY_TOKEN). When it's set up, it runs the live agents (the
    # Analyst, the Decider, the alert writer) and the hosted Muse models are their backup: on the 22 scenes it
    # decided exactly as they did, and reached "Are you OK?" about 6 s sooner (benchmarks/README.md). When an
    # agent runs on the hosted API instead, Muse Spark Open is its backup. "open" as a model name means it.
    open_weights_base: str = field(default_factory=lambda: _env("OPEN_WEIGHTS_BASE", default="https://inference.baseten.co/v1"))
    open_weights_key: str | None = field(default_factory=lambda: _env("OPEN_WEIGHTS_API_KEY", "BASETEN_API_KEY", "MODAL_PROXY_TOKEN"))
    open_weights_model: str = field(default_factory=lambda: _env("OPEN_WEIGHTS_MODEL", default="meta-models/muse-spark-open") or "")
    meta_api_base: str = field(default_factory=lambda: _env("MODEL_API_BASE_URL", "META_API_BASE", default="https://api.meta.ai/v1"))
    meta_model: str = field(default_factory=lambda: _env("MODEL_API_MODEL", "META_MODEL", default="muse-spark-1.3"))
    # Muse Spark reasons before it answers. "low" keeps an analysis near 3 s; the default effort
    # can spend 1,500 tokens and cut the answer off.
    reasoning_effort: str | None = field(default_factory=lambda: _env("LLM_REASONING_EFFORT", default="low") or None)

    # One model per agent role, all on the same API. The live Analyst needs speed; the Notice
    # reviewer runs afterwards and can take longer; the writer drafts alerts and summaries.
    analyst_model: str = field(default_factory=lambda: _env("ANALYST_MODEL", default="") or _open_first(""))
    # Muse Wonder was the best Notice reviewer: 40 of 40 public training cases and 16 of 16 of ours,
    # median 4.5 s, against 38 and 36 of 40 for Spark 1.3 and 1.1 (scenarios/README.md).
    reviewer_model: str = field(default_factory=lambda: _env(
        "REVIEWER_MODEL", default="muse-wonder-1.0"))
    writer_model: str = field(default_factory=lambda: _env("WRITER_MODEL", default="") or _open_first(""))

    # The Decider: Muse Spark gives a probability for discard, ask and alert; the rules in decider.py
    # pick the action. Spark 1.1 decides as well as 1.3 on the test moments and answers in ~2 s against 4-10 s.
    decider_model: str = field(default_factory=lambda: _env("DECIDER_MODEL", default="") or _open_first("muse-spark-1.1"))
    # The hosted model each live agent falls back to when Muse Spark Open fails (or runs on without it).
    decider_hosted_model: str = field(default_factory=lambda: _env("DECIDER_HOSTED_MODEL", default="muse-spark-1.1"))
    decider_min_lift: float = field(default_factory=lambda: _float("DECIDER_MIN_LIFT", 2.5))
    decider_timeout: float = field(default_factory=lambda: _float("DECIDER_TIMEOUT", 12))

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
    # Speech-to-text, each where it measured best on the 22 scenes (scenarios/README.md):
    #  * live 4-second chunks (STT_ENGINE): "whisper" on this machine, the default: faster (0.3 s against
    #    0.8 s), fewer errors on short chunks, earlier check-ins. "muse" = Muse Voice Transcribe while
    #    watching, with Whisper as the fallback. Standby is always Whisper, so no audio leaves the device.
    #  * the last minute, each time the Analyst runs (ANALYST_STT): "muse", the default with a Meta key:
    #    on whole stretches of noisy, overlapping speech it makes far fewer errors than Whisper.
    #  * audio kept while offline: Muse, once the connection is back.
    voice_api_key: str | None = field(default_factory=lambda: _env("MODEL_API_KEY", "META_API_KEY"))
    stt_engine: str = field(default_factory=lambda: _env("STT_ENGINE", default="whisper"))
    stt_timeout: float = field(default_factory=lambda: _float("STT_TIMEOUT", 6))
    analyst_stt: str = field(default_factory=lambda: _env(
        "ANALYST_STT", default="muse" if _env("MODEL_API_KEY", "META_API_KEY") else "whisper"))
    analyst_stt_timeout: float = field(default_factory=lambda: _float("ANALYST_STT_TIMEOUT", 10))
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

    # Which models the agents may call, for cost. Chosen in Setup (the owner's profile) or here:
    #   auto    as configured: Muse Spark Open for the live agents, Muse Wonder for Notice, each with the
    #           other provider as backup (the default)
    #   open    Muse Spark Open only (open weights, Baseten): no Meta Model API calls
    #   hosted  the Meta Model API only: no Baseten calls
    #   local   no model calls at all: Whisper, the voiceprint, the phrase list and the fixed rules
    model_plan: str = field(default_factory=lambda: _env("MODEL_PLAN", default="auto"))

    # A public demo (the hosted live app): one visitor at a time, for DEMO_VISIT_S at most; alerts are
    # always a dry run and no audio is kept, whatever else is set; everything is wiped when they leave.
    demo_mode: bool = field(default_factory=lambda: _env("DEMO_MODE", default="") == "1")
    demo_visit_s: float = field(default_factory=lambda: _float("DEMO_VISIT_S", 600))
    # The page sends a heartbeat every 15 s; a visit that goes quiet this long has left (a closed tab
    # doesn't always close the connection behind a proxy), and the next visitor may come in.
    demo_idle_s: float = field(default_factory=lambda: _float("DEMO_IDLE_S", 45))

    @property
    def muse_ready(self) -> bool:
        """Can the agents call a model under the chosen plan?"""
        plan = self.model_plan
        if plan == "local":
            return False
        if plan == "open":
            return self.open_ready
        if plan == "hosted":
            return bool(self.meta_api_key)
        return bool(self.meta_api_key) or self.open_ready

    @property
    def voice_ready(self) -> bool:
        """Muse Voice Transcribe is on the Meta Model API: only in the plans that use it."""
        return bool(self.voice_api_key) and self.model_plan in ("auto", "hosted")

    def agent_model(self, model: str) -> str:
        """What an agent set to model actually runs on under the chosen plan, for the screen."""
        if not self.muse_ready:
            return "off"
        if self.model_plan == "open":
            return "muse-spark-open (open weights)"
        if self.model_plan == "hosted" and model == "open":
            return self.meta_model
        return _shown(model)

    @property
    def open_ready(self) -> bool:
        return bool(self.open_weights_key and self.open_weights_model)

    @property
    def sms_ready(self) -> bool:
        return not self.demo_mode and bool(self.twilio_sid and self.twilio_token and self.twilio_from)

    @property
    def email_ready(self) -> bool:
        return not self.demo_mode and bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def keep_audio(self) -> bool:
        return not self.demo_mode and self.recording_rule != "all-party"

    def describe(self) -> dict:
        both = bool(self.meta_api_key) and self.open_ready and self.model_plan == "auto"
        return {
            "plan": self.model_plan,
            "muse_spark": self.agent_model(self.analyst_model or self.meta_model) if self.muse_ready else "off (phrase list only)",
            "reviewer": (self.agent_model(self.reviewer_model or self.meta_model) if self.muse_ready else "off"),
            "writer": self.agent_model(self.writer_model or self.meta_model) if self.muse_ready else "templates",
            "debrief_speech": "Muse Voice Transcribe" if self.voice_ready else f"Whisper {self.whisper_model}",
            "decider": self.agent_model(self.decider_model) if self.muse_ready else "off (fixed rules)",
            "backup": ("the other provider, then the fixed rules" if both else "the fixed rules"),
            "sms_and_calls": "Twilio" if self.sms_ready else "dry run",
            "email": self.smtp_host if self.email_ready else "dry run",
            "whisper": (f"Muse Voice Transcribe (Whisper {self.whisper_model} as fallback)"
                        if self.stt_engine == "muse" and self.voice_ready else f"Whisper {self.whisper_model}"),
            "analyst_speech": ("Muse Voice Transcribe, the last minute" if self.analyst_stt == "muse" and self.voice_ready
                               else "the live lines"),
            "recording_rule": self.recording_rule,
        }


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
