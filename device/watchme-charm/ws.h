// A small WebSocket client (RFC 6455) over plain TCP, enough for Watch Me's /ws:
//  - audio goes out as one binary message per 4-second chunk, sent in 0.25 s fragments as the
//    microphone fills them, so the board never holds a whole 128 KB chunk in RAM;
//  - JSON text messages come back from the server.
#pragma once
#include <WiFi.h>
#include "esp_random.h"

class WsClient {
 public:
  using TextHandler = void (*)(const char *text, size_t len);

  bool connect(const char *host, uint16_t port, const char *path) {
    tcp.stop();
    if (!tcp.connect(host, port, 3000)) return false;
    tcp.setNoDelay(true);
    uint8_t raw[16];
    for (auto &b : raw) b = esp_random() & 0xFF;
    char key[32];
    base64(raw, 16, key);
    tcp.printf("GET %s HTTP/1.1\r\nHost: %s:%u\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n", path, host, port, key);
    String status = tcp.readStringUntil('\n');
    if (status.indexOf(" 101") < 0) { tcp.stop(); return false; }
    while (tcp.connected()) {               // skip the rest of the response headers
      String line = tcp.readStringUntil('\n');
      if (line.length() <= 1) break;
    }
    open = true;
    return true;
  }

  bool connected() { return open && tcp.connected(); }
  void close() { open = false; tcp.stop(); }

  // opcode 1 text, 2 binary, 0 continuation; fin = last fragment of the message.
  bool sendFrame(uint8_t opcode, bool fin, const uint8_t *data, size_t len) {
    if (!connected()) return false;
    uint8_t head[14];
    size_t n = 0;
    head[n++] = (fin ? 0x80 : 0x00) | (opcode & 0x0F);
    if (len < 126) {
      head[n++] = 0x80 | len;
    } else if (len < 65536) {
      head[n++] = 0x80 | 126; head[n++] = len >> 8; head[n++] = len & 0xFF;
    } else {
      head[n++] = 0x80 | 127;
      for (int i = 7; i >= 0; i--) head[n++] = (uint64_t)len >> (8 * i) & 0xFF;
    }
    uint8_t mask[4];
    uint32_t r = esp_random();
    memcpy(mask, &r, 4);
    memcpy(head + n, mask, 4); n += 4;
    if (!writeAll(head, n)) return fail();
    uint8_t buf[512];                        // clients must mask what they send
    for (size_t off = 0; off < len;) {
      size_t k = min(sizeof(buf), len - off);
      for (size_t i = 0; i < k; i++) buf[i] = data[off + i] ^ mask[(off + i) & 3];
      if (!writeAll(buf, k)) return fail();
      off += k;
    }
    return true;
  }

  bool sendText(const char *text) { return sendFrame(1, true, (const uint8_t *)text, strlen(text)); }

  // Reads whatever frames have arrived; text messages go to the handler.
  void poll(TextHandler onText) {
    while (connected() && tcp.available() >= 2) {
      uint8_t h[2];
      if (!readAll(h, 2)) { fail(); return; }
      uint8_t opcode = h[0] & 0x0F;
      bool masked = h[1] & 0x80;
      uint64_t len = h[1] & 0x7F;
      if (len == 126) { uint8_t e[2]; if (!readAll(e, 2)) { fail(); return; } len = (e[0] << 8) | e[1]; }
      else if (len == 127) { uint8_t e[8]; if (!readAll(e, 8)) { fail(); return; } len = 0; for (auto b : e) len = (len << 8) | b; }
      uint8_t mask[4] = {0, 0, 0, 0};
      if (masked && !readAll(mask, 4)) { fail(); return; }
      bool keep = (opcode == 1 || opcode == 9) && len < sizeof(rx) - 1;
      for (uint64_t off = 0; off < len;) {
        uint8_t tmp[256];
        size_t k = min((uint64_t)sizeof(tmp), len - off);
        if (!readAll(tmp, k)) { fail(); return; }
        if (keep) for (size_t i = 0; i < k; i++) rx[off + i] = tmp[i] ^ mask[(off + i) & 3];
        off += k;
      }
      if (opcode == 8) { close(); return; }                       // the server closed
      if (opcode == 9 && keep) sendFrame(10, true, rx, len);      // ping -> pong
      if (opcode == 1 && keep) { rx[len] = 0; onText((const char *)rx, len); }
    }
  }

 private:
  WiFiClient tcp;
  bool open = false;
  uint8_t rx[12288];

  bool fail() { close(); return false; }

  bool writeAll(const uint8_t *p, size_t n) {
    uint32_t start = millis();
    while (n) {
      size_t w = tcp.write(p, n);
      if (w == 0) { if (!tcp.connected() || millis() - start > 3000) return false; delay(1); continue; }
      p += w; n -= w;
    }
    return true;
  }

  bool readAll(uint8_t *p, size_t n) {
    uint32_t start = millis();
    while (n) {
      int a = tcp.available();
      if (a <= 0) { if (!tcp.connected() || millis() - start > 3000) return false; delay(1); continue; }
      int r = tcp.read(p, min((size_t)a, n));
      if (r > 0) { p += r; n -= r; }
    }
    return true;
  }

  static void base64(const uint8_t *in, size_t n, char *out) {
    static const char t[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    size_t o = 0;
    for (size_t i = 0; i < n; i += 3) {
      uint32_t v = in[i] << 16 | (i + 1 < n ? in[i + 1] << 8 : 0) | (i + 2 < n ? in[i + 2] : 0);
      out[o++] = t[v >> 18 & 63]; out[o++] = t[v >> 12 & 63];
      out[o++] = i + 1 < n ? t[v >> 6 & 63] : '=';
      out[o++] = i + 2 < n ? t[v & 63] : '=';
    }
    out[o] = 0;
  }
};
