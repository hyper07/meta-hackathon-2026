"""
USB link between the Watch Me Charm board and the Watch Me server, for a board without Wi-Fi.

    cd app && ./run.sh                      # the server, in one terminal
    uvx --with pyserial --with websockets python device/bridge.py /dev/cu.usbmodem1101
    ... device/bridge.py /dev/cu.usbmodem1101 --enroll     # first: say one line to record your voice

The board sends its microphone as 0.25 s blocks; the bridge joins each 4-second chunk and sends it
to the server's /ws as one binary message, exactly like the phone app. Back to the board go only
the messages it acts on (state, check-in, its result, alert), and, on a check-in, the app's spoken
"Are you OK? Say I'm OK." as 16 kHz audio for its speaker. Framing: A5 5A, type, length (2 bytes LE),
payload; the board adds a CRC-16 so frames the USB link damaged are dropped, never passed on.
"""
from __future__ import annotations

import array
import asyncio
import base64
import json
import math
import sys
import threading
import urllib.request
import wave
from pathlib import Path

import serial
import websockets

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
PORT = ARGS[0] if ARGS else "/dev/cu.usbmodem1101"
SERVER = ARGS[1] if len(ARGS) > 1 else "ws://127.0.0.1:8000/ws"
ENROLL = "--enroll" in sys.argv
LINE = "Watch me. This is my voice, and only I can turn this on or off."
PROMPT = Path(__file__).resolve().parents[1] / "app" / "static" / "voice" / "are-you-ok.wav"
KEEP = {"hello", "state", "checkin", "checkin_result", "alert", "mode"}
FIELDS = ("type", "state", "timeout", "urgent", "ok", "mode")


def prompt_pcm() -> bytes:
    """The app's spoken check-in, resampled (linear) to the board's 16 kHz."""
    with wave.open(str(PROMPT)) as w:
        rate, data = w.getframerate(), array.array("h", w.readframes(w.getnframes()))
    out, step, pos = array.array("h"), rate / 16000, 0.0
    while pos < len(data) - 1:
        i = int(pos)
        out.append(int(data[i] + (data[i + 1] - data[i]) * (pos - i)))
        pos += step
    return out.tobytes()


def crc16(data: bytes, crc: int = 0xFFFF) -> int:
    """CRC-16/CCITT-FALSE, as the board computes it."""
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
        crc &= 0xFFFF
    return crc


class Board:
    def __init__(self, port: str) -> None:
        self.serial = serial.Serial(port, 115200, timeout=0.05)
        self.lock = threading.Lock()
        self.bad = 0

    def send(self, kind: str, payload: bytes) -> None:
        head = bytes([0xA5, 0x5A, ord(kind), len(payload) & 0xFF, len(payload) >> 8])
        with self.lock:
            self.serial.write(head + payload)

    def read_frames(self, on_frame) -> None:
        """Runs in a thread: frames go to on_frame; anything else is the board's log, printed."""
        buf, log = bytearray(), bytearray()
        while True:
            buf += self.serial.read(8192)
            while True:
                start = buf.find(b"\xa5\x5a")
                if start < 0:
                    log += buf[:-1] if buf.endswith(b"\xa5") else buf
                    del buf[:len(buf) - 1 if buf.endswith(b"\xa5") else len(buf)]
                    break
                log += buf[:start]
                del buf[:start]
                if len(buf) < 5:
                    break
                length = buf[3] | buf[4] << 8
                if length > 8200:                 # no real frame is this long: a false start
                    del buf[:2]
                    continue
                if len(buf) < 7 + length:
                    break
                if crc16(bytes(buf[2:5 + length])) != (buf[5 + length] | buf[6 + length] << 8):
                    self.bad += 1
                    del buf[:2]               # not a real frame start, or damaged: look for the next one
                    continue
                on_frame(chr(buf[2]), bytes(buf[5:5 + length]))
                del buf[:7 + length]
            while b"\n" in log:
                line, _, rest = bytes(log).partition(b"\n")
                print("board:", line.decode("utf-8", "replace").rstrip(), flush=True)
                log = bytearray(rest)


async def main() -> None:
    board = Board(PORT)
    pcm = prompt_pcm()
    loop = asyncio.get_running_loop()
    outbox: asyncio.Queue = asyncio.Queue()
    chunk = bytearray()

    blocks = -1

    def on_frame(kind: str, payload: bytes) -> None:
        nonlocal chunk, blocks
        if kind == "A":
            flags, audio = payload[0], payload[1:]
            if flags & 1:
                chunk, blocks = bytearray(), 0
            if flags >> 4 != blocks:          # a block went missing: wait for the next chunk
                blocks = -1
                return
            chunk += audio
            blocks += 1
            if flags & 2:
                samples = array.array("h", bytes(chunk))
                rms = (sum(x * x for x in samples) / max(1, len(samples))) ** 0.5
                level = 20 * math.log10(rms / 32768 + 1e-9)
                print(f"audio: {len(samples) / 16000:.2f} s chunk, {level:.0f} dBFS"
                      + (f" ({board.bad} damaged frames dropped so far)" if board.bad else ""), flush=True)
                if enrolling:
                    enroll_chunk(bytes(chunk), level)
                else:
                    loop.call_soon_threadsafe(outbox.put_nowait, bytes(chunk))
        elif kind == "T":
            loop.call_soon_threadsafe(outbox.put_nowait, payload.decode())

    enrolling = ENROLL
    takes: list[bytes] = []
    if ENROLL:
        print("enroll: say this once to the board, in your normal voice:", flush=True)
        print(f"   {LINE}", flush=True)

    def enroll_chunk(audio: bytes, level: float) -> None:
        nonlocal enrolling
        if not takes and (level < -45 or len(audio) < 32000):
            return                       # waiting for her to start
        takes.append(audio)              # the chunk she starts in, and the next one: her line may cross the 4 s edge
        print(f"enroll: heard you ({level:.0f} dBFS)", flush=True)
        if len(takes) < 2:
            return
        enrolling = False
        http = SERVER.replace("ws://", "http://").rsplit("/ws", 1)[0]
        body = json.dumps({"samples": [base64.b64encode(t).decode() for t in takes]}).encode()
        request = urllib.request.Request(http + "/api/enroll", body, {"Content-Type": "application/json"})
        try:
            out = json.loads(urllib.request.urlopen(request).read())
            print(f"enroll: saved your voiceprint (consistency {out.get('consistency')}); "
                  f"{out.get('advice') or 'say Watch me to start'}", flush=True)
        except Exception as error:
            print(f"enroll: failed ({error})", flush=True)

    threading.Thread(target=board.read_frames, args=(on_frame,), daemon=True).start()

    async def speak() -> None:
        # A little ahead of real time; the board buffers 16 KB (0.5 s).
        for i in range(0, len(pcm), 3200):
            board.send("P", pcm[i:i + 3200])
            await asyncio.sleep(0.085)

    async def ping() -> None:
        while True:
            board.send("J", b'{"type":"bridge"}')
            await asyncio.sleep(5)

    asyncio.create_task(ping())
    while True:
        try:
            async with websockets.connect(SERVER, max_size=None) as ws:
                print(f"bridge: {PORT} <-> {SERVER}", flush=True)

                async def upstream() -> None:
                    while True:
                        await ws.send(await outbox.get())

                async def downstream() -> None:
                    async for message in ws:
                        if not isinstance(message, str):
                            continue
                        data = json.loads(message)
                        if data.get("type") not in KEEP:
                            continue
                        board.send("J", json.dumps({k: data[k] for k in FIELDS if k in data}).encode())
                        print(f"server: {data.get('type')} {data.get('state', '')}", flush=True)
                        if data["type"] == "checkin":
                            asyncio.create_task(speak())

                await asyncio.gather(upstream(), downstream())
        except (OSError, websockets.ConnectionClosed) as error:
            print(f"bridge: server not reachable ({error}); retrying", flush=True)
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
