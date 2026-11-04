"""
The web server: the phone page, its WebSocket, setup, voice enrollment and review.

    uv run uvicorn watchme.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile ... --ssl-certfile ...
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import messenger, muse, notice, speech, store
from .config import settings
from .session import SESSION

STATIC = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Load Whisper and the voiceprint model now, not on the first "Watch me".
    asyncio.ensure_future(speech.run(speech.warm_up))
    if settings.demo_mode:            # a public demo starts clean, from the demo profile
        store.reset_demo()
        SESSION.profile = store.load_profile()
    if store.read_pending():          # work left from an offline stretch finishes once the network allows
        SESSION.start_catch_up()
    yield


app = FastAPI(title="Watch Me", lifespan=lifespan)

# Public demo: the visitor who holds the WebSocket, and the token their page sends with every API call.
VISIT: dict = {"ws": None, "token": ""}
DEMO_OPEN = {"/api/status"}


@app.middleware("http")
async def demo_guard(request: Request, call_next):
    """In a public demo only the current visitor's page may use the API, so nobody else can read
    their sessions or Notice entries, or change the profile while they're trying it."""
    path = request.url.path
    if settings.demo_mode and path.startswith("/api/") and path not in DEMO_OPEN:
        token = request.headers.get("x-visit", "")
        if not VISIT["token"] or not secrets.compare_digest(token, VISIT["token"]):
            return PlainTextResponse("Someone else is trying the demo right now.", status_code=423)
    return await call_next(request)


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/api/status")
async def status():
    return {"services": settings.describe(), "state": SESSION.screen_state(),
            "profile": store.public_profile(store.load_profile())}


@app.post("/api/profile")
async def save_profile(body: dict):
    profile = store.load_profile()
    pin = str(body.get("pin") or "").strip()
    if pin and not re.fullmatch(r"\d{4,8}", pin):
        raise HTTPException(400, "The PIN must be 4 to 8 digits.")
    contacts = []
    for c in body.get("contacts") or []:
        phone, email = str(c.get("phone") or "").strip(), str(c.get("email") or "").strip()
        if phone and not re.fullmatch(r"\+\d{8,15}", phone):
            raise HTTPException(400, f"Phone numbers need the country code, like +12125551234 (got {phone!r}).")
        if phone or email:
            relation = str(c.get("relation") or "").strip().lower()
            contacts.append({"name": str(c.get("name") or "").strip(), "phone": phone, "email": email,
                             "call": bool(c.get("call", True)), "default": bool(c.get("default")),
                             "relation": relation if relation in messenger.RELATIONS else ""})
    sos, duress = str(body.get("sos_phrase") or "").strip(), str(body.get("duress_phrase") or "").strip()
    for phrase in (sos, duress):
        if phrase and re.search(r"watch me|stop watching|i'?m (ok|okay|fine)", phrase, re.IGNORECASE):
            raise HTTPException(400, f"{phrase!r} overlaps a command. Pick words you wouldn't say by accident.")
    profile.update({"name": str(body.get("name") or "").strip(), "contacts": contacts,
                    "sos_phrase": sos, "duress_phrase": duress})
    if pin:
        profile["pin"] = pin
    store.save_profile(profile)
    SESSION.profile = profile
    return store.public_profile(profile)


@app.post("/api/enroll")
async def enroll(body: dict):
    """Recordings of the owner (16 kHz PCM16, base64) become one voiceprint: one spoken line (the app's
    setup), or three or more (older clients)."""
    samples = [speech.pcm16_to_float(base64.b64decode(s)) for s in body.get("samples") or []]
    samples = [s for s in samples if s.size >= speech.SAMPLE_RATE and speech.dbfs(s) > settings.silence_dbfs]
    whole = []
    if 0 < len(samples) < 3:
        line = np.concatenate(samples)
        if len(speech.voiced(line)) < 2.5 * speech.SAMPLE_RATE:
            raise HTTPException(400, "That was too short. Say the whole line, in your normal voice.")
        whole = [await speech.run(speech.voiceprint, line)]
        samples = speech.enrollment_pieces(line)
    if len(samples) < 3:
        raise HTTPException(400, "Say the line once, clearly, in your normal voice.")
    prints = [await speech.run(speech.voiceprint, s) for s in samples]
    pairs = [speech.similarity(a, b) for i, a in enumerate(prints) for b in prints[i + 1:]]
    mean = np.mean([p / np.linalg.norm(p) for p in prints + whole], axis=0)
    mean = mean / np.linalg.norm(mean)
    profile = store.load_profile()
    profile["voiceprint"] = mean.tolist()
    profile["voice_model"] = speech.VOICE_MODEL
    profile["enrolled_at"] = time.strftime("%Y-%m-%d %H:%M")
    profile.pop("needs_reenroll", None)
    store.save_profile(profile)
    SESSION.profile = profile
    consistency = round(min(pairs), 3)
    return {
        **store.public_profile(profile),
        "samples": len(samples), "consistency": consistency,
        "sample_signatures": [speech.signature(p) for p in prints],
        "threshold": 0.70, "strict_threshold": 0.90,
        "advice": None if consistency >= settings.voice_strict_threshold else
        "That recording wasn't clear enough. Try again somewhere quieter, at your normal speaking distance.",
    }


@app.post("/api/voice-check")
async def voice_check(body: dict):
    """Say anything; get the match score against the enrolled voice. For setup and for the demo."""
    profile = store.load_profile()
    if not profile.get("voiceprint"):
        raise HTTPException(400, "No voice enrolled yet.")
    audio = speech.pcm16_to_float(base64.b64decode(body["sample"]))
    print_ = await speech.run(speech.voiceprint, audio)
    similarity = speech.similarity(print_, np.asarray(profile["voiceprint"], dtype=np.float32))
    return {"similarity": round(similarity, 3), "match": speech.display_match(similarity),
            "owner": similarity >= settings.voice_threshold,
            "strict": similarity >= settings.voice_strict_threshold, "signature": speech.signature(print_),
            "threshold": 0.70, "strict_threshold": 0.90}


@app.get("/api/sessions")
async def sessions():
    return store.list_sessions()


@app.get("/api/sessions/{session_id}")
async def session_detail(session_id: str):
    if not re.fullmatch(r"[\w-]+", session_id):
        raise HTTPException(404)
    try:
        return store.read_session(session_id)
    except FileNotFoundError:
        raise HTTPException(404)


@app.get("/api/sessions/{session_id}/summary")
async def session_summary(session_id: str):
    return {"summary": await muse.summarise(await session_detail(session_id))}


@app.get("/api/sessions/{session_id}/clips/{name}")
async def clip(session_id: str, name: str):
    try:
        path = store.clip_path(session_id, name)
    except ValueError:
        raise HTTPException(404)
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="audio/wav")


# ── Notice ───────────────────────────────────────────────────────────────────

SETTINGS = ("school", "work", "online", "other")


def _notice_fields(body: dict) -> dict:
    setting = body.get("setting") if body.get("setting") in SETTINGS else ""
    when = str(body.get("when") or "")
    if when and not re.fullmatch(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?", when):
        raise HTTPException(400, "Date must look like 2026-10-31 or 2026-10-31T14:30.")
    return {"setting": setting, "who": str(body.get("who") or ""), "where": str(body.get("where") or ""), "when": when}


def _notice_page() -> dict:
    data = notice.read()
    return {**data, "patterns": notice.patterns(data["records"]),
            "types": {k: {"label": label, "plain": plain, "source": notice.SOURCES.get(src), "group": group}
                      for k, (label, plain, src, group) in notice.TYPES.items()},
            "groups": notice.GROUPS,
            "resources": notice.RESOURCES, "frequency": notice.FREQUENCY, "disclaimer": notice.DISCLAIMER,
            "ai": settings.muse_ready, "pending": len(store.read_pending())}


@app.get("/api/notice")
async def notice_list():
    return _notice_page()


@app.post("/api/notice/debrief")
async def notice_debrief(body: dict):
    """Her own account, typed, or spoken (16 kHz PCM16, base64) and transcribed here. The audio is not kept."""
    fields = _notice_fields(body)
    text = str(body.get("text") or "").strip()
    if body.get("audio"):
        audio = speech.pcm16_to_float(base64.b64decode(body["audio"]))
        # A whole account, no voice lock involved: Muse Voice Transcribe when there's a Meta key
        # (live listening stays on Whisper, whose word timings keep the voice lock tight).
        transcribe = speech.transcribe_muse if settings.voice_api_key else speech.transcribe
        try:
            spoken = " ".join(p.text for p in await speech.run(transcribe, audio))
        except Exception:
            spoken = " ".join(p.text for p in await speech.run(speech.transcribe_whisper, audio))
        text = f"{text}\n{spoken}".strip()
    if len(text) < 10:
        raise HTTPException(400, "Say or type a little more about what happened.")
    result = await notice.review(text, fields["setting"])
    if result and result.get("retry"):
        # No network: the account is saved now with its time; the check runs when the connection is back.
        record = notice.add(text, None, source="debrief", pending=True, **fields)
        store.queue_pending(kind="review", record=record["id"], text=text, setting=fields["setting"])
        await SESSION.go_offline(result["error"])
    else:
        record = notice.add(text, result, source="debrief", **fields)
    return {"record": record, **_notice_page()}


@app.post("/api/notice/session/{session_id}")
async def notice_session(session_id: str, body: dict):
    """Run the notice review on a recorded session, with who and where she adds now."""
    fields = _notice_fields(body)
    session = await session_detail(session_id)
    tag = {"owner": "owner", "other": "other"}
    text = "\n".join(f"[{tag.get(s.get('speaker'), 'unknown')}] {s['text']}" for s in session["segments"]
                     if s.get("text") and not s["text"].startswith("(loud"))
    if not text:
        raise HTTPException(400, "Nothing was transcribed in this session.")
    result = await notice.review(text, fields["setting"])
    if not fields["when"] and session["events"]:
        fields["when"] = time.strftime("%Y-%m-%dT%H:%M", time.localtime(session["events"][0]["t"]))
    record = notice.add(text, result, source="session", session=session_id, **fields)
    return {"record": record, **_notice_page()}


@app.post("/api/notice/{record_id}/label")
async def notice_label(record_id: str, body: dict):
    if not any(r["id"] == record_id for r in notice.read()["records"]):
        raise HTTPException(404)
    fields = _notice_fields(body)
    notice.label(record_id, setting=fields["setting"], who=fields["who"], where=fields["where"])
    page = _notice_page()
    return {"record": next(r for r in page["records"] if r["id"] == record_id), **page}


@app.get("/api/pending")
async def pending():
    return {"offline": SESSION.offline, "pending": len(store.read_pending())}


@app.post("/api/pending/retry")
async def pending_retry():
    """Try the queued analyses now, instead of waiting for the next automatic attempt."""
    done = await SESSION.catch_up_once() if await muse.online() else 0
    return {"done": done, "offline": SESSION.offline, "pending": len(store.read_pending())}


@app.get("/api/notice/export")
async def notice_export():
    return PlainTextResponse(notice.export(notice.read()), media_type="text/markdown",
                             headers={"Content-Disposition": "attachment; filename=notice-record.md"})


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    if settings.demo_mode:
        if VISIT["ws"] is not None:
            await ws.send_json({"type": "busy", "text": "Someone is trying the demo right now. "
                                "This page will connect by itself when it's free (at most 10 minutes)."})
            await ws.close()
            return
        VISIT["ws"], VISIT["token"] = ws, secrets.token_urlsafe(24)
    send = ws.send_json
    await SESSION.attach(send)
    timer = watchdog = None
    last_heard = [time.monotonic()]
    if settings.demo_mode:
        await ws.send_json({"type": "demo", "visit": VISIT["token"], "seconds": settings.demo_visit_s,
                            "pin": store.DEMO_PROFILE["pin"]})

        async def watch_idle() -> None:
            while True:
                await asyncio.sleep(min(10.0, settings.demo_idle_s / 3))
                if time.monotonic() - last_heard[0] > settings.demo_idle_s:
                    try:
                        await ws.close()
                    except Exception:
                        pass
                    return

        watchdog = asyncio.ensure_future(watch_idle())

        async def end_visit() -> None:
            await asyncio.sleep(settings.demo_visit_s)
            try:
                await ws.send_json({"type": "notice", "text": "Your demo time is up. Thanks for trying Watch Me!"})
                await ws.close()
            except Exception:
                pass                      # already gone

        timer = asyncio.ensure_future(end_visit())
    try:
        while True:
            message = await ws.receive()
            last_heard[0] = time.monotonic()
            if message.get("type") == "websocket.disconnect":
                break
            if message.get("bytes"):
                await SESSION.on_audio(message["bytes"])
                continue
            data = json.loads(message.get("text") or "{}")
            kind = data.get("type")
            if kind == "location":
                SESSION.set_location(data)
            elif kind == "checkin_answer":
                await SESSION.answer_checkin_tap(bool(data.get("ok")), data.get("pin"))
            elif kind == "stop_pin":
                await SESSION.stop_with_pin(str(data.get("pin") or ""))
            elif kind == "start_pin":
                await SESSION.start_with_pin(str(data.get("pin") or ""))
            elif kind == "mode":
                await SESSION.set_mode(str(data.get("mode") or ""))
    except WebSocketDisconnect:
        pass
    finally:
        SESSION.detach(send)
        if settings.demo_mode and VISIT["ws"] is ws:
            for task in (timer, watchdog):
                if task:
                    task.cancel()
            await SESSION.reset()
            VISIT["ws"], VISIT["token"] = None, ""
