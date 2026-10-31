// Audio plumbing: the server wants 16 kHz, mono, 16-bit PCM in 4-second chunks, the same as the web page.
export const TARGET_RATE = 16000;
export const CHUNK_SECONDS = 4;

/** Mono int16 at `from` Hz to int16 at 16 kHz. Averages each output sample's span (a box filter) before
 *  picking it, so a 48 kHz microphone doesn't alias into the speech band. */
export function resampleInt16(input: Int16Array, from: number, to = TARGET_RATE): Int16Array {
  if (from === to) return input;
  const ratio = from / to;
  const out = new Int16Array(Math.floor(input.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(input.length, Math.max(start + 1, Math.floor((i + 1) * ratio)));
    let sum = 0;
    for (let j = start; j < end; j++) sum += input[j];
    out[i] = Math.round(sum / (end - start));
  }
  return out;
}

/** Interleaved multi-channel int16 to mono. */
export function toMono(input: Int16Array, channels: number): Int16Array {
  if (channels <= 1) return input;
  const out = new Int16Array(Math.floor(input.length / channels));
  for (let i = 0; i < out.length; i++) {
    let sum = 0;
    for (let c = 0; c < channels; c++) sum += input[i * channels + c];
    out[i] = Math.round(sum / channels);
  }
  return out;
}

/** Collects 16 kHz samples and hands out fixed-length chunks. */
export class Chunker {
  private parts: Int16Array[] = [];
  private length = 0;
  constructor(private readonly samplesPerChunk = TARGET_RATE * CHUNK_SECONDS) {}

  push(samples: Int16Array): Int16Array[] {
    this.parts.push(samples);
    this.length += samples.length;
    const ready: Int16Array[] = [];
    while (this.length >= this.samplesPerChunk) ready.push(this.take(this.samplesPerChunk));
    return ready;
  }

  /** Everything buffered so far (for a recording the owner ends with a tap). */
  flush(): Int16Array {
    return this.take(this.length);
  }

  private take(n: number): Int16Array {
    const out = new Int16Array(n);
    let filled = 0;
    while (filled < n && this.parts.length) {
      const head = this.parts[0];
      const need = n - filled;
      if (head.length <= need) {
        out.set(head, filled);
        filled += head.length;
        this.parts.shift();
      } else {
        out.set(head.subarray(0, need), filled);
        this.parts[0] = head.subarray(need);
        filled += need;
      }
    }
    this.length -= filled;
    return out;
  }
}

/** Loudness of a buffer, 0..1, for the orb's glow. */
export function level(samples: Int16Array): number {
  if (!samples.length) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
  const rms = Math.sqrt(sum / samples.length) / 32768;
  const dbfs = 20 * Math.log10(Math.max(rms, 1e-6));
  return Math.max(0, Math.min(1, (dbfs + 55) / 40));
}

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

/** Base64 of raw bytes (for the enrollment and account uploads, which are JSON). */
export function toBase64(bytes: Uint8Array): string {
  let out = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i], b = bytes[i + 1] ?? 0, c = bytes[i + 2] ?? 0;
    const n = (a << 16) | (b << 8) | c;
    out += B64[(n >> 18) & 63] + B64[(n >> 12) & 63];
    out += i + 1 < bytes.length ? B64[(n >> 6) & 63] : '=';
    out += i + 2 < bytes.length ? B64[n & 63] : '=';
  }
  return out;
}

export function int16ToBase64(samples: Int16Array): string {
  return toBase64(new Uint8Array(samples.buffer, samples.byteOffset, samples.byteLength));
}

/** Little-endian bytes of int16 samples, for the WebSocket. */
export function int16Bytes(samples: Int16Array): ArrayBuffer {
  const copy = new Int16Array(samples);
  return copy.buffer;
}
