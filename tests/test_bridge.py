"""
The USB link between the Charm board and the server (device/bridge.py): framing, the CRC that
keeps damaged audio away from the voiceprint, and joining 0.25 s blocks into 4-second chunks.

    uvx pytest tests          # from the repo root; the server's own tests are in app/tests
"""
import random
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "device"))

import bridge  # noqa: E402
from bridge import Chunks, Frames, crc16  # noqa: E402


def frame(kind: str, payload: bytes, crc: int | None = None) -> bytes:
    """A frame as the board sends it: A5 5A, type, length (LE), payload, CRC-16 (LE)."""
    body = bytes([ord(kind)]) + struct.pack("<H", len(payload)) + payload
    return b"\xa5\x5a" + body + struct.pack("<H", crc16(body) if crc is None else crc)


def block(index: int, audio: bytes, first: bool = False, last: bool = False) -> bytes:
    return bytes([index << 4 | (1 if first else 0) | (2 if last else 0)]) + audio


def chunk_blocks(fill: int = 0) -> list[bytes]:
    """The 16 blocks of one 4-second chunk; block i carries 4000 samples of (fill + i)."""
    return [block(i, struct.pack("<h", fill + i) * 4000, first=i == 0, last=i == 15) for i in range(16)]


# ── CRC ──────────────────────────────────────────────────────────────────────────────────

def test_crc_is_ccitt_false():
    assert crc16(b"123456789") == 0x29B1        # the standard check value the board's C code matches
    assert crc16(b"") == 0xFFFF


# ── Framing ──────────────────────────────────────────────────────────────────────────────

def test_frames_and_the_boards_log_are_separated():
    frames = Frames()
    got, lines = frames.feed(b"boot ok\n" + frame("T", b'{"type":"hello"}') + b"mic on\n")
    assert got == [("T", b'{"type":"hello"}')]
    assert lines == ["boot ok", "mic on"]


def test_a_frame_split_across_reads_arrives_whole():
    data = frame("A", bytes(range(200)))
    frames, got = Frames(), []
    for i in range(0, len(data), 7):             # the serial port hands over whatever it has
        got += frames.feed(data[i:i + 7])[0]
    assert got == [("A", bytes(range(200)))]


def test_a_damaged_frame_is_dropped_and_the_next_one_still_arrives():
    damaged = bytearray(frame("A", b"\x01" * 100))
    damaged[50] ^= 0xFF                           # one byte flipped on the cable
    frames = Frames()
    got, _ = frames.feed(bytes(damaged) + frame("A", b"\x02" * 100))
    assert got == [("A", b"\x02" * 100)]
    assert frames.bad == 1


def test_a5_5a_inside_the_log_is_not_mistaken_for_a_frame():
    frames = Frames()
    got, _ = frames.feed(b"noise \xa5\x5a\x41\xff\xff more\n" + frame("J", b"{}"))
    assert got == [("J", b"{}")]


def test_a_lone_a5_at_the_end_of_a_read_waits_for_the_next_byte():
    data = frame("T", b"x")
    frames = Frames()
    first, _ = frames.feed(data[:1])
    second, _ = frames.feed(data[1:])
    assert first == [] and second == [("T", b"x")]


def test_random_noise_never_produces_a_frame():
    rng = random.Random(7)
    frames = Frames()
    got, _ = frames.feed(bytes(rng.randrange(256) for _ in range(50_000)))
    assert got == []


# ── Joining audio blocks into chunks ─────────────────────────────────────────────────────

def test_sixteen_blocks_in_order_make_one_four_second_chunk():
    chunks = Chunks()
    out = [chunks.add(b) for b in chunk_blocks()]
    assert out[:15] == [None] * 15
    assert len(out[15]) == 16 * 4000 * 2         # 4 s of 16 kHz PCM16
    assert struct.unpack_from("<h", out[15], 15 * 8000) == (15,)


def test_a_chunk_with_a_missing_block_is_dropped_and_the_next_chunk_is_kept():
    chunks = Chunks()
    blocks = chunk_blocks()
    del blocks[7]
    assert all(chunks.add(b) is None for b in blocks)
    out = [chunks.add(b) for b in chunk_blocks(fill=100)]
    assert out[-1] is not None and struct.unpack_from("<h", out[-1]) == (100,)


def test_blocks_before_the_first_one_are_ignored():
    chunks = Chunks()
    assert chunks.add(chunk_blocks()[5]) is None   # joined mid-chunk after a restart
    assert [chunks.add(b) for b in chunk_blocks()][-1] is not None


# ── The spoken check-in sent to the board's speaker ──────────────────────────────────────

def test_the_check_in_prompt_is_resampled_to_16_khz():
    with wave.open(str(bridge.PROMPT)) as w:
        seconds = w.getnframes() / w.getframerate()
    pcm = bridge.prompt_pcm()
    assert abs(len(pcm) / 2 / 16000 - seconds) < 0.01
