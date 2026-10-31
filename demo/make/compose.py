"""
Step 5 (video env): assemble the demo. Title cards, the recorded phone segments cut to ranges, captions,
subtitles, the narration, and the scene audio the phone heard (ducked under the narration).

    python compose.py <work dir> <out.mp4>

<work>/edit.json says how each recorded segment is cut, in recording seconds:
  {"party": {"parts": [["hold", rec_t, seconds], ["play", from, to], ...],
             "narr": [["party1", clip_t] | ["party2", ["rec", rec_t]], ...],
             "scene": ["party-drink", rec_t_of_scene_start]}, ...}
"""
import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WORK, VIDEO = Path(sys.argv[1]), Path(sys.argv[2])
W, H, FPS, SR = 1920, 1080, 25, 48_000
FONT = "/System/Library/Fonts/Avenir Next.ttc"
BOLD, DEMI, MED, REG, HEAVY = 0, 2, 5, 7, 8
NARR = json.loads((WORK / "narration" / "lines.json").read_text())
EDIT = json.loads((WORK / "edit.json").read_text())

BG_TOP, BG_BOTTOM = (11, 13, 20), (22, 26, 40)
TEXT, MUTED, ACCENT, RED, PURPLE, GREEN = (236, 238, 242), (154, 160, 173), (123, 147, 255), (255, 107, 107), (177, 151, 252), (81, 207, 102)


def font(size, style=REG):
    return ImageFont.truetype(FONT, size, index=style)


def background():
    g = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(BG_TOP) * (1 - g) + np.array(BG_BOTTOM) * g).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, W, axis=1))


BG = background()


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for w in text.split():
        trial = (line + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = w
    return lines + ([line] if line else [])


def text_block(draw, xy, text, fnt, fill, width, spacing=1.25):
    x, y = xy
    for line in wrap(draw, text, fnt, width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += int(fnt.size * spacing)
    return y


# ── cards ────────────────────────────────────────────────────────────────────

def card_title(img):
    d = ImageDraw.Draw(img)
    d.text((W // 2, 380), "Watch Me", font=font(150, HEAVY), fill=TEXT, anchor="mm")
    d.text((W // 2, 520), "Listens only when you ask. Answers only to your voice.", font=font(46, MED), fill=MUTED, anchor="mm")
    d.rounded_rectangle((W // 2 - 300, 640, W // 2 + 300, 700), 30, fill=(30, 36, 56))
    d.text((W // 2, 670), "Meta Global AI Developer Hackathon · 2026", font=font(28, DEMI), fill=ACCENT, anchor="mm")


def card_problem(img):
    d = ImageDraw.Draw(img)
    d.text((W // 2, 300), "“I felt like bait.”", font=font(110, HEAVY), fill=TEXT, anchor="mm")
    d.text((W // 2, 420), "A student, in a recent lawsuit over a fraternity party (reported by AP, October 2026). The allegations are disputed.",
           font=font(30, MED), fill=MUTED, anchor="mm")
    d.text((W // 2, 590), "Someone who's been drugged can't say they're not OK.", font=font(52, DEMI), fill=RED, anchor="mm")
    d.text((W // 2, 680), "At school and at work, harassment often hides inside a joke.", font=font(52, DEMI), fill=PURPLE, anchor="mm")


def card_hood(img):
    d = ImageDraw.Draw(img)
    d.text((W // 2, 110), "Every agent has its own model", font=font(64, HEAVY), fill=TEXT, anchor="mm")
    rows = [
        ("Listener", "Whisper + ECAPA voiceprint", "on the device", ACCENT),
        ("Analyst", "Muse Spark 1.3", "Meta Model API", ACCENT),
        ("Decider", "Muse Spark 1.1: discard · ask · alert", "Meta Model API", ACCENT),
        ("Check-in, Messenger", "Muse Spark writes · Twilio sends", "SMS, call, email", RED),
        ("Notice reviewer", "Muse Wonder 1.0", "Meta Model API", PURPLE),
        ("Spoken accounts", "Muse Voice Transcribe", "Meta Model API", PURPLE),
    ]
    y = 180
    for name, model, where, color in rows:
        d.rounded_rectangle((260, y, 1660, y + 84), 18, fill=(26, 31, 46), outline=(44, 50, 70), width=2)
        d.rectangle((260, y + 14, 268, y + 70), fill=color)
        d.text((300, y + 42), name, font=font(32, DEMI), fill=MUTED, anchor="lm")
        d.text((760, y + 42), model, font=font(36, BOLD), fill=TEXT, anchor="lm")
        d.text((1630, y + 42), where, font=font(26, MED), fill=MUTED, anchor="rm")
        y += 94
    x = 260
    for big, small in [("9 / 11", "harmful scenes asked “Are you OK?”"), ("0 / 9", "needless check-ins"),
                       ("40 / 40", "public training cases (NY State, EEOC)")]:
        d.text((x, 780), big, font=font(72, HEAVY), fill=GREEN, anchor="lm")
        d.text((x, 843), small, font=font(26, MED), fill=MUTED, anchor="lm")
        x += 480
    d.text((260, 900), "22 scripted scenes with synthetic voices and background noise; test sets described in the repo.",
           font=font(24, REG), fill=MUTED, anchor="lm")


def card_close(img):
    d = ImageDraw.Draw(img)
    d.text((W // 2, 300), "Watch Me", font=font(120, HEAVY), fill=TEXT, anchor="mm")
    for i, (t, c) in enumerate([("You turn it on.", TEXT), ("Only your voice turns it off.", ACCENT),
                                ("Only you decide what happened.", PURPLE)]):
        d.text((W // 2, 460 + i * 80), t, font=font(54, DEMI), fill=c, anchor="mm")
    d.text((W // 2, 800), "Opt-in · nothing kept in standby · audio only around flagged moments · no one else's voiceprint stored",
           font=font(28, MED), fill=MUTED, anchor="mm")
    d.text((W // 2, 880), "On your phone today. Built for the Muse Charm pendant when Meta opens it to developers.",
           font=font(30, DEMI), fill=ACCENT, anchor="mm")


SEGMENTS = {
    "enroll": dict(kicker="SETUP", title="Her voice is the key",
                   bullets=["Three lines become one voiceprint (ECAPA, on the device)",
                            "70% match to start · 90% to stop or to say “I'm OK”"]),
    "party": dict(kicker="EMERGENCY MODE", title="“Watch me”", color=RED,
                  bullets=["Whisper transcribes every few seconds", "Muse Spark scores the last minute",
                           "A decision model picks discard, ask or alert",
                           "No answer, or “no” in her voice: SMS, call, email"]),
    "lock": dict(kicker="VOICE LOCK", title="Only her voice stops it", color=RED,
                 bullets=["A stranger's “stop watching” is refused", "Recording continues, and she's asked right away"]),
    "notice": dict(kicker="NOTICE MODE · SCHOOL, WORK, ONLINE", title="Was this harassment?", color=PURPLE,
                   bullets=["No check-ins, no alerts: a review when she stops",
                            "Muse Wonder quotes the exact words and names the EEOC description",
                            "Patterns per person, in a hash-chained record she can export"]),
}

CLIPS = [dict(card=card_title, dur=6.0, narr=[["title", 0.5]]),
         dict(card=card_problem, dur=None, narr=[["problem", 0.6]])]
for seg in ("enroll", "party", "lock", "notice"):
    CLIPS.append(dict(rec=seg, seg=seg, **EDIT[seg]))
CLIPS += [dict(card=card_hood, dur=None, narr=[["hood", 0.5]]), dict(card=card_close, dur=None, narr=[["close", 0.5]])]


def parts_duration(parts):
    return sum(b if kind == "hold" else b - a for kind, a, b in parts)


def rec_to_out(parts, rec_t):
    t = 0.0
    for kind, a, b in parts:
        if kind == "play" and a <= rec_t <= b:
            return t + rec_t - a
        t += b if kind == "hold" else b - a
    return None


def out_to_rec(parts, t):
    for kind, a, b in parts:
        length = b if kind == "hold" else b - a
        if t < length:
            return a if kind == "hold" else a + t
        t -= length
    kind, a, b = parts[-1]
    return a if kind == "hold" else b


for c in CLIPS:
    if "parts" in c:
        c["dur"] = parts_duration(c["parts"])
        c["narr"] = [[k, rec_to_out(c["parts"], at[1]) if isinstance(at, list) else at] for k, at in c["narr"]]
    elif c["dur"] is None:   # a card lasts its narration plus a breath
        c["dur"] = max(at + NARR["seconds"][k] for k, at in c["narr"]) + 1.2
start = 0.0
for c in CLIPS:
    c["start"] = start
    start += c["dur"]
TOTAL = start
print(f"total {TOTAL:.1f}s", [round(c["dur"], 1) for c in CLIPS])
for c in CLIPS:
    for k, at in c["narr"]:
        assert at is not None and at + NARR["seconds"][k] <= c["dur"] + 0.05, (k, at, c["dur"])

# ── subtitles ────────────────────────────────────────────────────────────────

cues = []
for c in CLIPS:
    for key, at in c["narr"]:
        text, dur = NARR["lines"][key], NARR["seconds"][key]
        sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]
        chars = sum(len(s) for s in sentences)
        t = c["start"] + at
        for s in sentences:
            d = dur * len(s) / chars
            cues.append((t, t + d, s.replace("E E O C", "EEOC").replace("twenty two", "22").replace("check ins", "check-ins")))
            t += d

# ── frames ───────────────────────────────────────────────────────────────────

PHONE_H = 960
PHONE_W = round(860 * PHONE_H / 1864)
PHONE_X, PHONE_Y = 250, (H - PHONE_H) // 2


@lru_cache(maxsize=64)
def phone(rec, file):
    im = Image.open(WORK / "rec" / rec / "frames" / file).convert("RGB").resize((PHONE_W, PHONE_H), Image.LANCZOS)
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *im.size), 36, fill=255)
    return im, mask


FRAME_TIMES = {}


def frame_file(rec, t):
    if rec not in FRAME_TIMES:
        log = json.loads((WORK / "rec" / rec / "log.json").read_text())
        FRAME_TIMES[rec] = (np.array([f["t"] for f in log["frames"]]), [f["file"] for f in log["frames"]])
    times, files = FRAME_TIMES[rec]
    return files[max(0, int(np.searchsorted(times, t, side="right")) - 1)]


@lru_cache(maxsize=16)
def segment_layer(seg):
    img = BG.copy()
    d = ImageDraw.Draw(img)
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((PHONE_X - 14, PHONE_Y - 14, PHONE_X + PHONE_W + 14, PHONE_Y + PHONE_H + 14), 50, fill=170)
    img.paste((0, 0, 0), (0, 0), shadow.filter(ImageFilter.GaussianBlur(28)))
    d.rounded_rectangle((PHONE_X - 12, PHONE_Y - 12, PHONE_X + PHONE_W + 12, PHONE_Y + PHONE_H + 12), 48,
                        fill=(5, 6, 9), outline=(60, 66, 84), width=3)
    s = SEGMENTS[seg]
    color = s.get("color", ACCENT)
    x, width = 900, 900
    d.text((x, 200), s["kicker"], font=font(28, BOLD), fill=color)
    y = text_block(d, (x, 250), s["title"], font(76, HEAVY), TEXT, width, 1.15) + 30
    for b in s["bullets"]:
        d.ellipse((x, y + 16, x + 14, y + 30), fill=color)
        y = text_block(d, (x + 34, y), b, font(36, MED), TEXT, width - 40, 1.3) + 18
    d.text((x, 860), "Live recording of the app · synthetic voices (Chatterbox, Kokoro) · alerts in dry run",
           font=font(22, REG), fill=MUTED)
    return img


@lru_cache(maxsize=16)
def card_layer(i):
    img = BG.copy()
    CLIPS[i]["card"](img)
    return img


@lru_cache(maxsize=64)
def subtitle_layer(text, on_card):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fnt = font(34, DEMI)
    x0, width = (260, W - 520) if on_card else (900, 900)
    lines = wrap(d, text, fnt, width - 40)
    top = 1040 - (len(lines) * 46 + 24)
    box_w = max(d.textlength(l, font=fnt) for l in lines) + 40
    bx = (W - box_w) / 2 if on_card else x0
    d.rounded_rectangle((bx, top, bx + box_w, 1040), 14, fill=(0, 0, 0, 170))
    for i, l in enumerate(lines):
        d.text((bx + 20, top + 12 + i * 46), l, font=fnt, fill=(255, 255, 255, 255))
    return layer


def render(t):
    c = next((c for c in CLIPS if c["start"] <= t < c["start"] + c["dur"]), CLIPS[-1])
    local = t - c["start"]
    if "card" in c:
        img = card_layer(CLIPS.index(c)).copy()
        fade = min(1.0, local / 0.4, (c["dur"] - local) / 0.4)
    else:
        img = segment_layer(c["seg"]).copy()
        im, mask = phone(c["rec"], frame_file(c["rec"], out_to_rec(c["parts"], local)))
        img.paste(im, (PHONE_X, PHONE_Y), mask)
        fade = min(1.0, local / 0.3, (c["dur"] - local) / 0.3)
    cue = next((x for x in cues if x[0] <= t < x[1]), None)
    if cue:
        img = Image.alpha_composite(img.convert("RGBA"), subtitle_layer(cue[2], "card" in c)).convert("RGB")
    if fade < 1:
        img = Image.blend(Image.new("RGB", (W, H), BG_TOP), img, max(0.0, fade))
    return img


# ── audio ────────────────────────────────────────────────────────────────────

def resample(audio, rate_in, rate_out):
    n_out = int(round(len(audio) * rate_out / rate_in))
    spectrum = np.fft.rfft(audio)[: n_out // 2 + 1]
    return (np.fft.irfft(spectrum, n_out) * (n_out / len(audio))).astype(np.float32)


def load(path):
    a, r = sf.read(path, dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    return a if r == SR else resample(a, r, SR)


def rms_db(a):
    return 20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-9)


n = int(TOTAL * SR) + SR
narr_track, scene_track = np.zeros(n, np.float32), np.zeros(n, np.float32)
for c in CLIPS:
    for key, at in c["narr"]:
        a = load(WORK / "narration" / f"{key}.wav")
        a = a * 10 ** ((-19 - rms_db(a[np.abs(a) > 0.01])) / 20)   # every narration line at the same loudness
        i = int((c["start"] + at) * SR)
        narr_track[i:i + len(a)] += a[: n - i]
    if "scene" in c:
        scene, offset = c["scene"]
        a = load(WORK / "audio" / f"{scene}.wav")
        a = a * 10 ** ((-21 - rms_db(a[np.abs(a) > 0.01])) / 20)
        t = 0.0
        for kind, s0, s1 in c["parts"]:
            if kind == "play":
                piece = a[max(0, int((s0 - offset) * SR)):max(0, int((s1 - offset) * SR))].copy()
                i = int((c["start"] + t + max(0, offset - s0)) * SR)
                ramp = min(len(piece), int(0.05 * SR))
                if ramp:
                    piece[:ramp] *= np.linspace(0, 1, ramp)
                    piece[-ramp:] *= np.linspace(1, 0, ramp)
                scene_track[i:i + len(piece)] += piece[: n - i]
            t += s1 if kind == "hold" else s1 - s0
    for name, rec_t in c.get("prompts", []):     # what the phone said out loud, at the moment it said it
        a = load(WORK / "app-voice" / f"{name}.wav")
        a = a * 10 ** ((-19 - rms_db(a[np.abs(a) > 0.01])) / 20)
        t_out = rec_to_out(c["parts"], rec_t)
        if t_out is not None:
            i = int((c["start"] + t_out) * SR)
            narr_track[i:i + len(a)] += a[: n - i]   # on the narration track, so it isn't ducked
    for _, line, rec_t in c.get("sounds", []):   # enrollment: the line she reads, when she reads it
        a = load(WORK / "audio" / "enroll.wav")
        seg = a[int(line * 6.5 * SR):int((line + 1) * 6.5 * SR)]
        seg = seg * 10 ** ((-21 - rms_db(seg[np.abs(seg) > 0.01])) / 20)
        t_out = rec_to_out(c["parts"], rec_t)
        if t_out is not None:
            i = int((c["start"] + t_out) * SR)
            scene_track[i:i + len(seg)] += seg[: n - i]

env = (np.abs(narr_track) > 0.01).astype(np.float32)
k = int(0.25 * SR)
env = np.clip(np.convolve(env, np.ones(k) / k, mode="same") * 4, 0, 1)
mix = narr_track + scene_track * (1 - 0.72 * env)
mix = np.tanh(mix / 0.9) * 0.9   # soft limit instead of scaling everything down to the loudest peak
sf.write(WORK / "mix.wav", mix[: int(TOTAL * SR)], SR, subtype="PCM_16")

# ── encode ───────────────────────────────────────────────────────────────────

VIDEO.parent.mkdir(parents=True, exist_ok=True)
proc = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(WORK / "mix.wav"), "-c:v", "libx264",
                         "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                         "-shortest", "-movflags", "+faststart", str(VIDEO)], stdin=subprocess.PIPE)
for f in range(int(TOTAL * FPS)):
    proc.stdin.write(render(f / FPS).tobytes())
proc.stdin.close()
proc.wait()


def srt_time(t):
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(t % 1 * 1000):03d}"


VIDEO.with_suffix(".srt").write_text("".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{s}\n\n" for i, (a, b, s) in enumerate(cues, 1)))
print("wrote", VIDEO, f"{TOTAL:.1f}s")
