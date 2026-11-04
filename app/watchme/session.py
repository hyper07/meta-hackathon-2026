"""
One owner, one Watch Me session, and the agents that share it.

    phone mic ──4 s chunks──▶ Listener ──text, voice match──▶ Gatekeeper ── start / stop / OK / SOS
                                   │
                                   ▼ (only while watching)
                               Scribe ◀── every line, score and decision, hash-chained
                                   │
                    phrase list ───┤ instant score; colours the line for review
                                   ▼ marked, loud, or every 30 s
                               Analyst (Muse Spark) ── categories, exact quotes, reason
                                   ▼ score ≥ trigger
                               Decider (Muse Spark + rules) ── discard / ask / urgent ask
                                   ▼ ask
                               Check-in ── "Are you OK?" ── "I'm OK" in her voice, "Get help", or nothing
                                   ▼ no answer, "not OK", SOS or duress phrase, phone gone
                               Messenger (Muse Spark writes, Twilio + SMTP send)

Speech-to-text, each where it measured best: Whisper on this machine for the live 4-second chunks (fast;
tight clips for the voice lock), and Muse Voice Transcribe for whole stretches: the last minute each time
the Analyst runs, and audio kept while offline once the connection is back.

Offline: Whisper, the voiceprint, the phrase list and the rules are all local, so the check-in loop keeps
working without the network. What needs the model API (the Analyst, the Notice review) is queued with
its transcript and time, and every chunk of audio is kept meanwhile. When the connection is back, the
catch-up loop has Muse Voice Transcribe transcribe the kept audio again, then runs the queued analyses
on Muse's transcript, appending to the same hash-chained logs.

The session outlives the browser connection on purpose: if the phone drops off
while watching (battery, network, someone takes it), that counts as a missed
check-in.

Notice mode (school, work) runs the same Listener, Scribe and Analyst, but the
Decider only notes: no "Are you OK?", no alert for a dropped phone. The SOS and
duress phrases still alert, since saying one is never an accident. When she
stops, the transcript goes to notice.review() and into the notice book.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from collections import deque
from typing import Awaitable, Callable

import numpy as np
import soundfile as sf

from . import commands, decider, lexicon, messenger, muse, notice, speech, store
from .config import settings

Send = Callable[[dict], Awaitable[None]]

CONTEXT_SECONDS = 60

# Location. A fix older than this is "last known" in the alert, and Watch Me asks the phone for a fresh one.
FRESH_FIX_S = 60
# After an alert, while still watching, her contacts get her new position when she has moved this far,
# at most this often, for this long.
UPDATE_MOVED_M, UPDATE_EVERY_S, UPDATE_FOR_S = 150, 120, 3600


def distance_m(a: dict, b: dict) -> float:
    """Great-circle distance between two fixes, in metres."""
    la1, la2 = math.radians(a["lat"]), math.radians(b["lat"])
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(math.radians(b["lon"] - a["lon"]) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def map_link(fix: dict) -> str:
    return f"https://maps.google.com/?q={fix['lat']:.6f},{fix['lon']:.6f}"


def location_line(fix: dict | None, now: float | None = None) -> str | None:
    """The line the app itself adds to every alert, so the model can never drop or cut the link."""
    if not fix:
        return None
    age = (now or time.time()) - fix["at"]
    when = "now" if age < FRESH_FIX_S else \
        f"last known, at {time.strftime('%H:%M', time.localtime(fix['at']))}, {max(1, round(age / 60))} min ago"
    accuracy = f", within {fix['accuracy']:.0f} m" if fix.get("accuracy") else ""
    return f"Location ({when}{accuracy}): {map_link(fix)}"


PLANS = ("auto", "open", "hosted", "local")
DEFAULT_PLAN = settings.model_plan if settings.model_plan in PLANS else "auto"


def apply_plan(profile: dict) -> None:
    """The model plan she chose in Setup (for cost), or the server's default."""
    plan = profile.get("model_plan")
    settings.model_plan = plan if plan in PLANS else DEFAULT_PLAN


class Session:
    def __init__(self) -> None:
        self.profile = store.load_profile()
        apply_plan(self.profile)
        self.state = "standby"          # standby | watching
        self.mode = "watch"             # watch (emergency) | notice (school, work: no check-ins, no alerts)
        self.covert = False             # watching, while the screen shows standby (duress phrase)
        self.log: store.EvidenceLog | None = None
        self.recent: deque[tuple[float, str, str]] = deque()      # (t, speaker, text), last minute
        self.ring: deque[np.ndarray] = deque(maxlen=2)             # audio before a flag, for its clip
        self.minute: deque[tuple[float, np.ndarray]] = deque()     # (t, chunk) of the last minute while watching
        self.clip: list[np.ndarray] = []
        self.clip_segments: list[str] = []
        self.clip_started = 0.0         # when the clip's first sample was heard
        self.clip_offline = False       # some of it was kept while offline: Muse transcribes it later
        self.record_until = 0.0
        self.prev_text = ""
        self.held: np.ndarray | None = None   # audio of a sentence still going when its chunk ended
        self.seq = 0
        self.transcript_all: list[str] = []   # the whole session, for the notice review
        self.location: dict | None = None    # her latest fix: lat, lon, accuracy (m), at (epoch s)
        self.trail: deque[dict] = deque(maxlen=30)   # earlier fixes, for the alert email
        self.fresh_fix = asyncio.Event()
        self.alert_contacts: list[dict] = []
        self.last_sent_fix: dict | None = None
        self.last_update_at = 0.0
        self.loud_times: deque[float] = deque()
        self.stop_refused_at = 0.0
        self.last_sweep = 0.0
        self.last_ok_at = 0.0
        self.last_ok_score = 0.0
        self.last_alert_at = 0.0
        self.checkin_task: asyncio.Task | None = None
        self.checkin_reason = ""
        self.lost_task: asyncio.Task | None = None
        self.offline = False            # the model API failed; work is queued and all audio is kept
        self.catch_up_task: asyncio.Task | None = None
        self._send: Send | None = None
        self._tasks: set[asyncio.Task] = set()

    # ── connection ──────────────────────────────────────────────────────────

    async def attach(self, send: Send) -> None:
        self._send = send
        self.profile = store.load_profile()
        apply_plan(self.profile)
        if self.lost_task:
            self.lost_task.cancel()
            self.lost_task = None
            self._event("reconnected", detail="the phone came back before the timer ran out")
        await self.send({"type": "hello", "state": self.screen_state(), "profile": store.public_profile(self.profile),
                         "services": settings.describe(), "session": self.log.id if self.log else None,
                         # On the 0-1 display scale (speech.display_match), not the model's own.
                         "thresholds": {"start": 0.70, "strict": 0.90}, "mode": self.mode,
                         "offline": self.offline, "pending": len(store.read_pending())})
        if store.read_pending():
            self.start_catch_up()

    def detach(self, send: Send) -> None:
        if self._send is not send:
            return  # an older tab closing; the phone that replaced it is still here
        self._send = None
        if self.state == "watching" and self.mode == "notice":
            self._event("disconnected", detail="phone dropped off; notice mode, no alert")
        elif self.state == "watching":
            self._event("disconnected", detail=f"phone dropped off; alert in {settings.checkin_timeout_s:.0f} s unless it returns")
            self.lost_task = self._spawn(self._lost_timer())

    async def reset(self) -> None:
        """Public demo: forget the visitor who just left. Ends a session without a review or an alert,
        cancels every timer, and starts over as a fresh Session with the demo profile."""
        self.transcript_all = []                 # no Notice review for a visit that has ended
        for task in [self.checkin_task, self.lost_task, self.catch_up_task, *self._tasks]:
            if task and not task.done():
                task.cancel()
        if self.state == "watching":
            self._send = None
            self.checkin_task = self.lost_task = None
            await self.stop("demo visit ended")
        store.reset_demo()
        self.__init__()

    async def _lost_timer(self) -> None:
        await asyncio.sleep(settings.checkin_timeout_s)
        await self.escalate(f"the phone stopped sending while Watch Me was on, and did not come back within {settings.checkin_timeout_s:.0f} s")

    async def send(self, message: dict) -> None:
        if self._send is None:
            return
        try:
            await self._send(message)
        except Exception:
            self._send = None

    async def show(self, message: dict) -> None:
        """Send unless covert: in covert mode the screen must look like Watch Me is off."""
        if not self.covert:
            await self.send(message)

    def screen_state(self) -> str:
        return "standby" if self.covert else self.state

    def _spawn(self, coro) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def _event(self, kind: str, **fields) -> dict | None:
        return self.log.append(kind, **fields) if self.log else None

    # ── Listener ────────────────────────────────────────────────────────────

    async def on_audio(self, pcm: bytes) -> None:
        audio = speech.pcm16_to_float(pcm)
        if audio.size < speech.SAMPLE_RATE // 2:
            return
        now = time.time()
        loudness = speech.dbfs(audio)
        loud = loudness > settings.loud_dbfs
        self.ring.append(audio)
        if self.state == "watching":
            # The last minute of audio, for Muse Voice Transcribe when the Analyst runs.
            self.minute.append((now, audio))
            while self.minute and now - self.minute[0][0] > CONTEXT_SECONDS:
                self.minute.popleft()
        # Offline, every chunk is kept, in clips of about a minute, so nothing is lost before the analysis can run.
        recording = self.state == "watching" and settings.keep_audio and (now < self.record_until or self.offline)
        if recording:
            if not self.clip:
                self.clip_started = now - audio.size / speech.SAMPLE_RATE
            self.clip.append(audio)
            self.clip_offline = self.clip_offline or self.offline
            if self.offline and len(self.clip) * audio.size >= settings.offline_clip_s * speech.SAMPLE_RATE:
                self._close_clip()
        elif self.clip:
            self._close_clip()
        await self.show({"type": "level", "dbfs": round(loudness, 1), "recording": recording})
        if loudness < settings.silence_dbfs and self.held is None:
            return

        # A sentence that runs to the end of the chunk is probably cut off: hold its audio and
        # transcribe it with the next chunk, so commands and voiceprints see whole sentences.
        # Costs up to a chunk of delay for that sentence; HOLD_MAX_S caps it.
        if self.held is not None:
            audio = np.concatenate([self.held, audio])
            self.held = None
        pieces = await speech.run(speech.transcribe, audio, self.state == "watching")
        if speech.last_error and self.state == "watching" and not self.offline:
            # Muse Voice Transcribe couldn't be reached; Whisper made this transcript. Keep all audio from now
            # on, so Muse can transcribe it properly once the connection is back.
            await self.go_offline(f"speech-to-text: {speech.last_error}")
        seconds = audio.size / speech.SAMPLE_RATE
        if (settings.hold_max_s > 0 and pieces and seconds - pieces[-1].end < 0.6 and loudness >= settings.silence_dbfs
                and seconds - pieces[-1].start < settings.hold_max_s):
            self.held = audio[int(pieces.pop().start * speech.SAMPLE_RATE):]
        if not pieces and not (loud and self.state == "watching"):
            return
        reference = self.profile.get("voiceprint")
        reference = np.asarray(reference, dtype=np.float32) if reference else None
        heard: list[tuple[speech.Piece, float | None, list[float] | None]] = []
        for piece in pieces:
            similarity, sig = None, None
            if reference is not None:
                print_ = await speech.run(speech.voiceprint, speech.window(audio, piece))
                similarity = round(speech.similarity(print_, reference), 3)
                sig = speech.signature(print_)
            heard.append((piece, similarity, sig))

        sos, duress = self.profile.get("sos_phrase"), self.profile.get("duress_phrase")
        text = " ".join(p.text for p, _, _ in heard)
        joined = f"{self.prev_text} {text}".strip()
        found = commands.find(joined, sos, duress)
        # Each command is judged on the voice of the sentence that said it; a command split
        # across two chunks falls back to this chunk's first sentence.
        said_by = {}
        for command in found:
            said_by[command] = next((s for p, s, _ in heard if command in commands.find(p.text, sos, duress)),
                                    heard[0][1] if heard else None)
        self.prev_text = "" if found & {"start", "stop", "sos", "duress"} else text
        outcomes = await self.gatekeeper(found, said_by)

        for piece, similarity, sig in heard:
            mine = commands.find(piece.text, sos, duress) & set(outcomes)
            await self.show({
                "type": "voice", "similarity": similarity, "match": speech.display_match(similarity), "signature": sig,
                "owner": similarity is not None and similarity >= settings.voice_threshold,
                "strict": similarity is not None and similarity >= settings.voice_strict_threshold,
                "command": next(iter(mine), None), "outcome": outcomes.get(next(iter(mine), ""), None),
                # Words only while watching: in standby nothing that was said leaves the gatekeeper.
                "text": piece.text if self.state == "watching" else None,
            })

        if self.state == "watching":
            if loud:
                self.loud_times.append(now)
            if not heard:
                await self.record_segment("", None, None, loudness, loud)
            for piece, similarity, _ in heard:
                is_owner = None if similarity is None else similarity >= settings.voice_threshold
                piece_db = speech.dbfs(speech.window(audio, piece, minimum=0))
                await self.record_segment(piece.text, is_owner, similarity, piece_db, loud)

    # ── Gatekeeper ──────────────────────────────────────────────────────────

    async def gatekeeper(self, found: set[str], said_by: dict[str, float | None]) -> dict[str, str]:
        """
        Act on the commands heard, and say what happened to each one: accepted, refused or ignored.
        Two bars: VOICE_THRESHOLD to start; VOICE_STRICT_THRESHOLD to stop or to say "I'm OK",
        because anyone else doing those could switch off the owner's protection.
        """
        enrolled = bool(self.profile.get("voiceprint"))
        outcomes: dict[str, str] = {}

        def match(command: str) -> str:
            s = said_by.get(command)
            return f"voice match {s:.2f}" if s is not None else "no voice match"

        def passes(command: str, bar: float) -> bool:
            s = said_by.get(command)
            return s is not None and s >= bar

        if "duress" in found and self.state == "watching" and not self.covert:
            # Looks like stopping; keeps recording and alerts. Accepted from any voice: the phrase is secret.
            self.covert = True
            self._event("duress", detail=f"duress phrase heard ({match('duress')}); screen shows off, recording continues")
            await self.send({"type": "state", "state": "standby", "notice": "Watch Me is off."})
            self.record_until = time.time() + 300
            self._spawn(self.escalate("the duress phrase was said: Watch Me appeared to stop but kept listening"))
            return {"duress": "accepted"}

        if "sos" in found:
            if self.state != "watching":
                await self.start(f"SOS phrase ({match('sos')})")
            self._event("sos", detail=f"SOS phrase heard ({match('sos')})")
            self.record_until = time.time() + 300
            self._spawn(self.escalate("the SOS phrase was said"))
            return {"sos": "accepted"}

        if "start" in found and self.state == "standby":
            if not enrolled:
                await self.send({"type": "notice", "text": "Record your voice in Setup first, so only you can start and stop Watch Me."})
                outcomes["start"] = "ignored"
            elif passes("start", settings.voice_threshold):
                await self.start(f"\"Watch me\" in the owner's voice ({match('start')})")
                outcomes["start"] = "accepted"
            else:
                self._event("start_refused", detail=f"\"Watch me\" in another voice ({match('start')})")
                await self.send({"type": "notice", "text": f"Heard \"Watch me\", but not in your voice ({match('start')}). Not started."})
                outcomes["start"] = "refused"
            return outcomes

        if "stop" in found and self.state == "watching":
            if self.covert:
                self._event("stop_ignored", detail=f"stop said during duress mode ({match('stop')}); still watching")
                return {"stop": "ignored"}
            if passes("stop", settings.voice_strict_threshold):
                await self.stop(f"\"Stop watching\" in the owner's voice ({match('stop')})")
                return {"stop": "accepted"}
            self.stop_refused_at = time.time()
            # Someone else trying to switch it off is evidence: keep the chunk before, the one with their
            # voice, and what follows, as for any flagged line.
            self._keep_audio("stop-refused")
            close = passes("stop", settings.voice_threshold)
            self._event("stop_refused", detail=f"\"stop watching\" refused ({match('stop')}, needs "
                                               f"{settings.voice_strict_threshold:.2f}); still watching")
            await self.show({"type": "notice", "text": (
                "Not sure that was you. Say \"stop watching\" again, closer to the phone, or use your PIN."
                if close else "Only your voice can stop Watch Me. Still recording.")})
            if not close and not self.checkin_task:
                await self.start_checkin(urgent=True, reason="someone else tried to stop Watch Me")
            return {"stop": "refused"}

        if self.checkin_task and found & {"ok", "not_ok"}:
            if "not_ok" in found and said_by.get("not_ok") is not None and passes("not_ok", settings.voice_threshold):
                await self.answer_checkin(False, f"said they are not OK ({match('not_ok')})")
                return {"not_ok": "accepted"}
            if "ok" in found and passes("ok", settings.voice_strict_threshold):
                await self.answer_checkin(True, f"said \"I'm OK\" ({match('ok')})")
                return {"ok": "accepted"}
            if "ok" in found:
                self._event("ok_refused", detail=f"\"I'm OK\" not accepted ({match('ok')}, needs "
                                                 f"{settings.voice_strict_threshold:.2f})")
                return {"ok": "refused"}
        return outcomes

    async def set_mode(self, mode: str) -> None:
        """Chosen in standby. Live notice mode records other people at school or work, so only where one party's consent is enough."""
        if self.state != "standby" or mode not in ("watch", "notice"):
            return
        if mode == "notice" and not settings.keep_audio:
            await self.send({"type": "notice", "text": "Live listening at school or work needs everyone's consent where you are. "
                                                       "Use \"Tell me what happened\" on the Notice tab instead."})
            mode = "watch"
        self.mode = mode
        await self.send({"type": "mode", "mode": self.mode})

    async def start(self, how: str) -> None:
        self.state, self.covert = "watching", False
        self.log = store.EvidenceLog()
        self.recent.clear()
        self.minute.clear()
        self.transcript_all = []
        self.loud_times.clear()
        self.last_sweep = time.time()
        # The 2-minute de-duplication is within a session: an alert in the last one must not mute this one.
        self.last_alert_at = self.last_ok_at = self.last_ok_score = 0.0
        self.alert_contacts, self.last_sent_fix, self.last_update_at = [], None, 0.0
        self._event("start", detail=how, location=self.location, recording_rule=settings.recording_rule, mode=self.mode)
        await self.send({"type": "state", "state": "watching", "session": self.log.id, "mode": self.mode, "notice": (
            "Noticing. Nothing will alert anyone; you'll get a review when you stop." if self.mode == "notice"
            else "Watching. Say \"stop watching\" to end.")})

    async def stop(self, how: str) -> None:
        if self.checkin_task:
            self.checkin_task.cancel()
            self.checkin_task = None
        if self.clip:
            self._close_clip()
        self._event("stop", detail=how)
        session_id = self.log.id if self.log else None
        self.state, self.covert, self.record_until = "standby", False, 0.0
        await self.send({"type": "state", "state": "standby", "session": session_id, "notice": "Stopped. Review the session any time."})
        if self.mode == "notice" and session_id and self.transcript_all:
            self._spawn(self.notice_review(session_id, "\n".join(self.transcript_all)))

    async def notice_review(self, session_id: str, text: str) -> None:
        result = await notice.review(text)
        if result and result.get("retry"):
            # No network: keep the record now, review it when the connection is back.
            record = notice.add(text, None, setting="", who="", where="", when=time.strftime("%Y-%m-%dT%H:%M"),
                                source="session", session=session_id, pending=True)
            store.queue_pending(kind="review", record=record["id"], text=text, setting="")
            await self.go_offline(result["error"])
        else:
            record = notice.add(text, result, setting="", who="", where="", when=time.strftime("%Y-%m-%dT%H:%M"),
                                source="session", session=session_id)
        await self.send({"type": "notice_review", "record": record})

    async def stop_with_pin(self, pin: str) -> None:
        """The fallback when the voice doesn't match (a cold, a noisy room). Also the only way out of duress mode."""
        if self.state != "watching":
            return
        if not self.profile.get("pin") or pin != self.profile["pin"]:
            self._event("pin_refused", detail="wrong PIN")
            await self.show({"type": "notice", "text": "Wrong PIN. Still watching."})
            return
        await self.stop("PIN")

    async def start_with_pin(self, pin: str) -> None:
        if self.state == "standby" and self.profile.get("pin") and pin == self.profile["pin"]:
            await self.start("PIN")
        else:
            await self.send({"type": "notice", "text": "Wrong PIN."})

    # ── Scribe + Analyst ────────────────────────────────────────────────────

    async def record_segment(self, text: str, is_owner: bool | None, similarity: float | None, loudness: float, loud: bool) -> None:
        now = time.time()
        self.seq += 1
        seg = f"s{self.seq}"
        speaker = "owner" if is_owner else ("other" if is_owner is False else "unknown")
        clean = commands.strip_commands(text, self.profile.get("sos_phrase"), self.profile.get("duress_phrase"))
        hits = lexicon.scan(clean)
        if any(h.category == "incapacitation" for h in hits):
            pattern = lexicon.drugging_pattern([t for _, _, t in self.recent] + [clean])
            if pattern:
                hits.append(pattern)
        score = lexicon.score(hits, loud)
        record = self._event(
            "segment", seg=seg, speaker=speaker, similarity=similarity, text=text or "(loud sound, no words)",
            dbfs=round(loudness, 1), loud=loud, score=score, level=lexicon.level(score),
            categories=sorted({h.category for h in hits}), quotes=[h.phrase for h in hits],
            reason=("phrase list: " + ", ".join(f"\"{h.phrase}\"" for h in hits)) if hits else ("loud sound" if loud else ""),
            engine="phrases",
        )
        await self.show({"type": "segment", **record})
        if text:
            self.recent.append((now, speaker, text))
            self.transcript_all.append(f"[{speaker}] {text}")
        while self.recent and now - self.recent[0][0] > CONTEXT_SECONDS:
            self.recent.popleft()
        while self.loud_times and now - self.loud_times[0] > CONTEXT_SECONDS:
            self.loud_times.popleft()

        if score >= settings.review_mark:
            self._keep_audio(seg)
        sweep_due = settings.muse_ready and settings.analyst_sweep_s > 0 and now - self.last_sweep >= settings.analyst_sweep_s
        if score >= settings.review_mark or loud or sweep_due:
            self.last_sweep = now
            self._spawn(self.analyse(seg, score, hits))

    def _keep_audio(self, seg: str) -> None:
        """Start (or extend) a clip: the chunk before the flag, this one, and the next 30 s."""
        if not settings.keep_audio:
            return
        if not self.clip:
            self.clip = list(self.ring)
            self.clip_started = time.time() - sum(a.size for a in self.clip) / speech.SAMPLE_RATE
        self.clip_segments.append(seg)
        self.record_until = max(self.record_until, time.time() + settings.record_after_flag_s)

    def _close_clip(self) -> None:
        if not (self.log and self.clip):
            self.clip, self.clip_segments = [], []
            return
        name = f"{time.strftime('%Y%m%d-%H%M%S')}-{self.clip_segments[0] if self.clip_segments else 'clip'}.wav"
        saved = self.log.save_clip(name, np.concatenate(self.clip))
        self._event("clip", segments=self.clip_segments, started_t=round(self.clip_started, 3), **saved)
        if self.clip_offline and settings.voice_ready:
            store.queue_pending(kind="transcribe", session=self.log.id, file=saved["file"],
                                started_t=round(self.clip_started, 3), seconds=saved["seconds"])
        self.clip, self.clip_segments, self.clip_offline = [], [], False

    def transcript(self) -> str:
        return "\n".join(f"[{speaker}] {text}" for _, speaker, text in self.recent)

    async def minute_transcript(self) -> str | None:
        """
        The last minute, transcribed again by Muse Voice Transcribe in one request: on whole stretches it
        hears overlapping, noisy speech far better than Whisper does on 4-second chunks (scenarios/README.md).
        None when it isn't set up or can't be reached; the Analyst then reads Whisper's lines.
        """
        if not (settings.analyst_stt == "muse" and settings.voice_ready and settings.keep_audio and self.minute):
            return None
        audio = np.concatenate([chunk for _, chunk in self.minute])
        started = self.minute[-1][0] - audio.size / speech.SAMPLE_RATE
        try:
            pieces = await speech.run(speech.transcribe_muse, audio, "DIARIZATION", settings.analyst_stt_timeout)
        except Exception:
            return None
        turns = await self.label_turns(audio, pieces, started)
        return "\n".join(f"[{t['speaker']}] {t['text']}" for t in turns) or None

    async def label_turns(self, audio: np.ndarray, pieces: list, started: float) -> list[dict]:
        """Each Muse turn labelled owner or other by the owner's voiceprint, as the live lines are."""
        reference = self.profile.get("voiceprint")
        reference = np.asarray(reference, dtype=np.float32) if reference else None
        turns = []
        for piece in pieces:
            speaker, similarity = "unknown", None
            if reference is not None:
                print_ = await speech.run(speech.voiceprint, speech.window(audio, piece))
                similarity = round(speech.similarity(print_, reference), 3)
                speaker = "owner" if similarity >= settings.voice_threshold else "other"
            turns.append({"t": round(started + piece.start, 2), "speaker": speaker, "similarity": similarity,
                          "text": piece.text})
        return turns

    async def analyse(self, seg: str, phrase_score: float, hits: list[lexicon.Hit]) -> None:
        muse_text = await self.minute_transcript()
        transcript = muse_text or self.transcript()
        result = await muse.analyse(transcript) if transcript else None
        heard = ", ".join(f"\"{h.phrase}\"" for h in hits)
        analysis = {"score": phrase_score, "categories": sorted({h.category for h in hits}),
                    "quotes": [h.phrase for h in hits], "reason": f"heard {heard}" if hits else "a loud sound",
                    "engine": "phrases"}
        if result and "error" in result:
            self._event("analyst_error", seg=seg, detail=result["error"], queued=bool(result.get("retry")))
            if result.get("retry"):
                store.queue_pending(kind="analyse", session=self.log.id if self.log else None, seg=seg,
                                    transcript=transcript, phrase_score=phrase_score)
                await self.go_offline(result["error"])
        elif result:
            if self.offline:
                await self.go_online(0)
            analysis = {**result, "engine": "muse-spark", "phrase_score": phrase_score}
            update = self._event("update", seg=seg, score=round(result["score"], 3), level=lexicon.level(result["score"]),
                                 categories=result["categories"], quotes=result["quotes"], reason=result["reason"],
                                 engine="muse-spark", phrase_score=phrase_score,
                                 transcript_engine="muse-voice-transcribe" if muse_text else "whisper")
            await self.show({"type": "update", **update})
            if result["score"] >= settings.review_mark:
                self._keep_audio(seg)
        # The Analyst may lower the colour, but not the trigger: either score can wake the Decider.
        if max(phrase_score, analysis["score"]) >= settings.trigger_score or seg_tried_stop(self):
            await self.decide(seg, analysis)

    # ── Offline and catch-up ────────────────────────────────────────────────

    async def go_offline(self, why: str) -> None:
        first = not self.offline
        if first:
            self.offline = True
            self._event("offline", detail=f"model API unreachable ({why[:120]}); keeping all audio, analysis queued")
        # Sent every time, so the count on the bar stays current; the explanation only the first time.
        await self.show({"type": "offline", "pending": len(store.read_pending()),
                         "text": ("Offline. Still listening and checking in with the phrase list; everything is "
                                  "saved here and will be analyzed when you're back online.") if first else None})
        self.start_catch_up()

    async def go_online(self, done: int) -> None:
        self.offline = False
        speech.resume_muse()
        self._event("online", detail=f"model API reachable again; {done} queued moment(s) analyzed")
        await self.show({"type": "online", "done": done, "pending": len(store.read_pending())})

    def start_catch_up(self) -> None:
        if self.catch_up_task is None or self.catch_up_task.done():
            self.catch_up_task = self._spawn(self._catch_up_loop())

    async def _catch_up_loop(self) -> None:
        while store.read_pending():
            await asyncio.sleep(settings.catch_up_s)
            if await muse.online():
                await self.catch_up_once()

    async def catch_up_once(self) -> int:
        """Finish the queued work the network allowed. Returns how many items were completed."""
        if self.offline and self.clip:
            self._close_clip()    # the audio kept so far goes to Muse Voice Transcribe too
        # Transcripts first: the queued analyses then read Muse's transcript instead of Whisper's.
        items, done = sorted(store.read_pending(), key=lambda i: i["kind"] != "transcribe"), 0
        for item in list(items):
            log = self.log if self.log and self.log.id == item.get("session") else (
                store.EvidenceLog(item["session"]) if item.get("session") else None)
            if item["kind"] == "transcribe":
                if log and not await self.transcribe_clip(log, item):
                    break
            elif item["kind"] == "analyse":
                better = muse_transcript(log, item["queued_t"]) if log else None
                result = await muse.analyse(better or item["transcript"])
                if not result or "error" in result:
                    break
                if log:
                    update = log.append("update", seg=item["seg"], score=round(result["score"], 3), level=lexicon.level(result["score"]),
                                        categories=result["categories"], quotes=result["quotes"], reason=result["reason"],
                                        engine="muse-spark", phrase_score=item.get("phrase_score"), later=True,
                                        heard_at=item.get("queued_at"),
                                        transcript_engine="muse-voice-transcribe" if better else "whisper")
                    if log is self.log:
                        await self.show({"type": "update", **update})
            elif item["kind"] == "review":
                result = await notice.review(item["text"], item.get("setting", ""))
                if not result or "error" in result:
                    break
                notice.set_review(item["record"], result)
                await self.send({"type": "notice_review", "record": next((r for r in notice.read()["records"] if r["id"] == item["record"]), None)})
            items.remove(item)
            done += 1
        store.write_pending(items)
        if done and not items:
            await self.go_online(done)
        return done

    async def transcribe_clip(self, log: store.EvidenceLog, item: dict) -> bool:
        """Muse Voice Transcribe on a clip kept while offline, each turn labelled by the owner's voiceprint."""
        path = log.dir / "clips" / item["file"]
        if not path.exists():
            return True     # nothing to do; drop the item
        audio, _ = sf.read(path, dtype="float32")
        try:
            pieces = await speech.run(speech.transcribe_muse, audio)
        except Exception as error:
            if log is self.log:
                self._event("transcribe_error", file=item["file"], detail=f"{type(error).__name__}: {str(error)[:120]}")
            return False
        turns = await self.label_turns(audio, pieces, item["started_t"])
        heard_at = time.strftime("%H:%M:%S", time.localtime(item["started_t"]))
        log.append("transcript", file=item["file"], engine="muse-voice-transcribe", later=True,
                   heard_at=time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(item["started_t"])), turns=turns,
                   detail=f"Muse Voice Transcribe, audio kept offline from {heard_at}: "
                          + (" ".join(f"[{t['speaker']}] {t['text']}" for t in turns) or "no speech"))
        return True

    # ── Decider + Check-in ──────────────────────────────────────────────────

    async def decide(self, seg: str, analysis: dict) -> None:
        score = float(analysis.get("score", 0))
        if self.checkin_task:
            return
        if self.mode == "notice":
            self._event("noted", seg=seg, detail=analysis.get("reason") or "marked for the review")
            await self.show({"type": "noted", "seg": seg, "reason": analysis.get("reason") or ""})
            return
        recently_ok = time.time() - self.last_ok_at < settings.checkin_cooldown_s
        if recently_ok and score <= self.last_ok_score + 0.2:
            self._event("decision", seg=seg, action="skip", why=f"owner said OK {time.time() - self.last_ok_at:.0f} s ago")
            return
        context = {
            "local time": time.strftime("%a %H:%M"),
            "owner said OK": f"{time.time() - self.last_ok_at:.0f} s ago" if self.last_ok_at else "not this session",
            "loud sounds in the last minute": len(self.loud_times),
            "another voice tried to stop the app": "yes" if seg_tried_stop(self) else "no",
        }
        decision = await decider.decide(self.transcript(), analysis, context)
        self._event("decision", seg=seg, **decision)
        await self.show({"type": "decision", "seg": seg, **decision})
        if decision["action"] == "ask":
            await self.start_checkin(decision["urgent"], analysis.get("reason") or "something sounded wrong")

    async def start_checkin(self, urgent: bool, reason: str) -> None:
        if self.mode == "notice":
            # Notice mode never interrupts her: the moment is marked for the review instead.
            self._event("noted", urgent=urgent, detail=reason)
            return
        if self.checkin_task:
            # Two analyses can finish within a second of each other; the first check-in stands, so its
            # timer is never orphaned to fire "missed" after she has already answered.
            return
        timeout = settings.urgent_checkin_timeout_s if urgent else settings.checkin_timeout_s
        self.checkin_reason = reason
        self._event("checkin", urgent=urgent, timeout=timeout, detail=reason)
        await self.show({"type": "checkin", "urgent": urgent, "timeout": timeout, "reason": reason})
        await self.send({"type": "locate"})   # a fresh fix now, so an alert won't carry an old one
        self.checkin_task = self._spawn(self._checkin_timer(timeout))

    async def _checkin_timer(self, timeout: float) -> None:
        await asyncio.sleep(timeout)
        self.checkin_task = None
        self._event("checkin_missed", detail=f"no answer within {timeout:.0f} s")
        await self.escalate(f"did not answer \"Are you OK?\" within {timeout:.0f} s ({self.checkin_reason})")

    async def answer_checkin(self, ok: bool, how: str) -> None:
        if not self.checkin_task:
            return
        self.checkin_task.cancel()
        self.checkin_task = None
        self._event("checkin_answer", ok=ok, detail=how)
        await self.show({"type": "checkin_result", "ok": ok})
        if ok:
            self.last_ok_at = time.time()
            self.last_ok_score = max((s for s in self._recent_scores()), default=0.0)
        else:
            await self.escalate(f"answered that they are not OK ({how})")

    async def answer_checkin_tap(self, ok: bool, pin: str | None) -> None:
        """A tap can only ask for help. "I'm OK" is hers to say, in her own voice: a tap, or a PIN typed by
        whoever holds the phone, could dismiss a check-in for someone who can't speak for herself."""
        if ok:
            self._event("ok_refused", detail="\"I'm OK\" by tap: only her voice can say it")
            await self.show({"type": "notice", "text": "Say \"I'm OK\" in your voice. A tap can only get help."})
            return
        await self.answer_checkin(False, "tapped \"Get help\"")

    def _recent_scores(self) -> list[float]:
        if not self.log:
            return []
        records = store.read_session(self.log.id)["segments"]
        return [s.get("score", 0) for s in records if time.time() - s["t"] < CONTEXT_SECONDS]

    # ── Messenger ───────────────────────────────────────────────────────────

    async def escalate(self, why: str) -> None:
        now = time.time()
        if now - self.last_alert_at < 120:
            self._event("alert_skipped", detail=f"already alerted {now - self.last_alert_at:.0f} s ago: {why}")
            return
        self.last_alert_at = now
        self.record_until = max(self.record_until, now + 300)
        name = self.profile.get("name") or "the Watch Me user"
        heard = next((text for _, speaker, text in reversed(self.recent) if lexicon.scan(text)), "")
        if self.location and now - self.location["at"] > FRESH_FIX_S and self._send:
            # Her fix is old and the phone is still here: ask for a new one, a few seconds at most.
            self.fresh_fix.clear()
            await self.send({"type": "locate"})
            try:
                await asyncio.wait_for(self.fresh_fix.wait(), 4)
            except asyncio.TimeoutError:
                pass   # then the last known fix, with its time
        where = location_line(self.location)
        facts = {
            "name": name, "why": why, "time": time.strftime("%H:%M %Z"),
            "location_link_added_by_app": bool(where),
            "heard": heard[:160],
        }
        body = await muse.write_alert(facts)
        if where:
            body += "\n" + where
        contacts, rule = messenger.recipients(self.profile.get("contacts") or [])
        self.alert_contacts, self.last_sent_fix, self.last_update_at = contacts, self.location, time.time()
        results = await messenger.alert_all(contacts, name, body, email_extra=self.trail_text())
        self._event("alert", detail=why, message=body, results=results, location=self.location, sent_to=rule)
        await self.show({"type": "alert", "why": why, "message": body, "results": results,
                         "contacts": len(contacts), "sent_to": rule})

    def trail_text(self) -> str:
        """Her earlier positions this session, newest first, for the alert email."""
        earlier = [f for f in reversed(self.trail) if f is not self.location][:6]
        if not earlier:
            return ""
        return "Earlier positions:\n" + "\n".join(
            f"  {time.strftime('%H:%M', time.localtime(f['at']))}: {map_link(f)}" for f in earlier)

    def set_location(self, location: dict) -> None:
        try:
            lat, lon = float(location["lat"]), float(location["lon"])
        except (KeyError, TypeError, ValueError):
            return
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return
        now = time.time()
        at = now
        if isinstance(location.get("time"), (int, float)) and 0 <= now - location["time"] / 1000 < 3600:
            at = location["time"] / 1000   # when the phone took the fix, if it says
        accuracy = location.get("accuracy")
        fix = {"lat": lat, "lon": lon, "accuracy": float(accuracy) if isinstance(accuracy, (int, float)) else None,
               "at": at}
        self.location = fix
        if not self.trail or distance_m(self.trail[-1], fix) >= 25 or at - self.trail[-1]["at"] >= 60:
            self.trail.append(fix)
        self.fresh_fix.set()
        # After an alert, while still watching: tell her people when she has moved.
        if (self.state == "watching" and self.alert_contacts and now - self.last_alert_at < UPDATE_FOR_S
                and now - self.last_update_at >= UPDATE_EVERY_S
                and (not self.last_sent_fix or distance_m(self.last_sent_fix, fix) >= UPDATE_MOVED_M)):
            self.last_sent_fix, self.last_update_at = fix, now
            self._spawn(self.send_location_update(fix))

    async def send_location_update(self, fix: dict) -> None:
        name = self.profile.get("name") or "the Watch Me user"
        body = (f"Watch Me update for {name}: they have moved since the alert.\n{location_line(fix)}\n"
                f"Please call {name}. If you can't reach them, call 911.")
        results = await messenger.alert_all(self.alert_contacts, name, body, calls=False,
                                            subject=f"Watch Me location update: {name}")
        self._event("location_update", message=body, results=results, location=fix)


def seg_tried_stop(session: Session) -> bool:
    return time.time() - session.stop_refused_at < CONTEXT_SECONDS


SESSION = Session()


def muse_transcript(log: store.EvidenceLog, until: float) -> str | None:
    """The last minute before `until`, from Muse transcripts of clips kept offline, if there are any."""
    if not log.path.exists():
        return None
    turns = [turn for line in log.path.read_text().splitlines() if '"transcript"' in line
             for record in [json.loads(line)] if record["kind"] == "transcript" for turn in record["turns"]]
    lines = [f"[{t['speaker']}] {t['text']}" for t in sorted(turns, key=lambda t: t["t"])
             if until - CONTEXT_SECONDS - 5 <= t["t"] <= until + 1]
    return "\n".join(lines) or None
