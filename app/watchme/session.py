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
                               Decider (Jev + rules) ── discard / ask / urgent ask
                                   ▼ ask
                               Check-in ── "Are you OK?" ── owner's voice, PIN tap, or nothing
                                   ▼ no answer, "not OK", SOS or duress phrase, phone gone
                               Messenger (Muse Spark writes, Twilio + SMTP send)

Offline: speech-to-text, the voiceprint, the phrase list and the rules are all local, so the check-in
loop keeps working without the network. What needs the model API (the Analyst, the Notice review) is
queued with its transcript and time, every chunk of audio is kept meanwhile, and a catch-up loop
finishes the work when the connection is back, appending to the same hash-chained logs.

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
import time
from collections import deque
from typing import Awaitable, Callable

import numpy as np

from . import commands, decider, lexicon, messenger, muse, notice, speech, store
from .config import settings

Send = Callable[[dict], Awaitable[None]]

CONTEXT_SECONDS = 60


class Session:
    def __init__(self) -> None:
        self.profile = store.load_profile()
        self.state = "standby"          # standby | watching
        self.mode = "watch"             # watch (emergency) | notice (school, work: no check-ins, no alerts)
        self.covert = False             # watching, while the screen shows standby (duress phrase)
        self.log: store.EvidenceLog | None = None
        self.recent: deque[tuple[float, str, str]] = deque()      # (t, speaker, text), last minute
        self.ring: deque[np.ndarray] = deque(maxlen=2)             # audio before a flag, for its clip
        self.clip: list[np.ndarray] = []
        self.clip_segments: list[str] = []
        self.record_until = 0.0
        self.prev_text = ""
        self.held: np.ndarray | None = None   # audio of a sentence still going when its chunk ended
        self.seq = 0
        self.transcript_all: list[str] = []   # the whole session, for the notice review
        self.location: dict | None = None
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
        # Offline, every chunk is kept, in clips of about a minute, so nothing is lost before the analysis can run.
        recording = self.state == "watching" and settings.keep_audio and (now < self.record_until or self.offline)
        if recording:
            self.clip.append(audio)
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
        pieces = await speech.run(speech.transcribe, audio)
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
        self.transcript_all = []
        self.loud_times.clear()
        self.last_sweep = time.time()
        # The 2-minute de-duplication is within a session: an alert in the last one must not mute this one.
        self.last_alert_at = self.last_ok_at = self.last_ok_score = 0.0
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
        self.clip_segments.append(seg)
        self.record_until = max(self.record_until, time.time() + settings.record_after_flag_s)

    def _close_clip(self) -> None:
        if not (self.log and self.clip):
            self.clip, self.clip_segments = [], []
            return
        name = f"{time.strftime('%Y%m%d-%H%M%S')}-{self.clip_segments[0] if self.clip_segments else 'clip'}.wav"
        saved = self.log.save_clip(name, np.concatenate(self.clip))
        self._event("clip", segments=self.clip_segments, **saved)
        self.clip, self.clip_segments = [], []

    def transcript(self) -> str:
        return "\n".join(f"[{speaker}] {text}" for _, speaker, text in self.recent)

    async def analyse(self, seg: str, phrase_score: float, hits: list[lexicon.Hit]) -> None:
        transcript = self.transcript()
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
                                 engine="muse-spark", phrase_score=phrase_score)
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
        items, done = store.read_pending(), 0
        for item in list(items):
            if item["kind"] == "analyse":
                result = await muse.analyse(item["transcript"])
                if not result or "error" in result:
                    break
                log = self.log if self.log and self.log.id == item["session"] else (store.EvidenceLog(item["session"]) if item["session"] else None)
                if log:
                    update = log.append("update", seg=item["seg"], score=round(result["score"], 3), level=lexicon.level(result["score"]),
                                        categories=result["categories"], quotes=result["quotes"], reason=result["reason"],
                                        engine="muse-spark", phrase_score=item.get("phrase_score"), later=True,
                                        heard_at=item.get("queued_at"))
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
        """"Get help" needs nothing. "I'm OK" by tap needs the PIN when one is set, so a grabbed phone can't dismiss it."""
        if ok and self.profile.get("pin") and pin != self.profile["pin"]:
            self._event("ok_refused", detail="tap \"I'm OK\" with a wrong PIN")
            await self.show({"type": "notice", "text": "Wrong PIN."})
            return
        await self.answer_checkin(ok, "tapped " + ("\"I'm OK\"" if ok else "\"Get help\""))

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
        facts = {
            "name": name, "why": why, "time": time.strftime("%H:%M %Z"),
            "map": (f"https://maps.google.com/?q={self.location['lat']},{self.location['lon']}" if self.location else None),
            "heard": heard[:160],
        }
        body = await muse.write_alert(facts)
        contacts, rule = messenger.recipients(self.profile.get("contacts") or [])
        results = await messenger.alert_all(contacts, name, body)
        self._event("alert", detail=why, message=body, results=results, location=self.location, sent_to=rule)
        await self.show({"type": "alert", "why": why, "message": body, "results": results,
                         "contacts": len(contacts), "sent_to": rule})

    def set_location(self, location: dict) -> None:
        self.location = {k: location.get(k) for k in ("lat", "lon", "accuracy")}


def seg_tried_stop(session: Session) -> bool:
    return time.time() - session.stop_refused_at < CONTEXT_SECONDS


SESSION = Session()
