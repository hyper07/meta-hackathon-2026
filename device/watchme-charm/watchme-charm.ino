// Watch Me on the Waveshare ESP32-C6-LCD-1.69: the board is the Charm, the Mac is the brain.
//
//  - The microphone (ES8311 codec) streams 16 kHz audio to the Watch Me server's /ws, in the same
//    4-second chunks the phone sends. Whisper, the voiceprint and the Muse agents all run there.
//  - The screen shows Momo. Nothing changes when Watch Me starts listening (stealth); the only
//    Watch Me screen is "Are you OK?", with the countdown, and the speaker says it out loud.
//  - Two links to the server: Wi-Fi (WebSocket straight to /ws), or USB (LINK_USB in config.h): the
//    board talks to device/bridge.py on the Mac over the USB cable, and the bridge talks to /ws.
//  - Start, stop and "I'm OK" are by voice only, as in the app. Holding BOOT during "Are you OK?"
//    asks for help (it can only raise an alert, never turn Watch Me off).
//
// Pins: Waveshare's board definition (xiaozhi-esp32, boards/waveshare/esp32-c6-lcd-1.69/config.h).
#include <Arduino.h>
#include <WiFi.h>
#include <Wire.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Arduino_GFX_Library.h>
#include "ESP_I2S.h"
#include "es8311.h"
#include "config.h"
#include "ws.h"
#include "avatar.h"

// display (ST7789V2, 240x280, SPI)
#define LCD_SCK 1
#define LCD_MOSI 2
#define LCD_DC 3
#define LCD_RST 4
#define LCD_CS 5
#define LCD_BL 6
// audio (ES8311: I2C control, I2S data)
#define I2C_SCL 7
#define I2C_SDA 8
#define I2S_MCLK 19
#define I2S_BCLK 20
#define I2S_DIN 21    // microphone -> ESP
#define I2S_WS 22
#define I2S_DOUT 23   // ESP -> speaker
// buttons and power
#define BOOT_BTN 9
#define BATTERY_EN 15  // held high so the board stays on when running from the battery

#define RATE 16000
#define BLOCK 4000                    // 0.25 s of audio per WebSocket fragment
#define BLOCKS_PER_CHUNK 16           // 16 x 0.25 s = the server's 4-second chunk
#define POOL 6

Arduino_DataBus *bus = new Arduino_HWSPI(LCD_DC, LCD_CS, LCD_SCK, LCD_MOSI);
Arduino_GFX *lcd = new Arduino_ST7789(bus, LCD_RST, 0, true, 240, 280, 0, 20, 0, 20);
Arduino_Canvas *gfx = new Arduino_Canvas(240, 280, lcd);

I2SClass i2s;
es8311_handle_t codec;
WsClient ws;

static int16_t pool[POOL][BLOCK];
QueueHandle_t freeQ, fullQ;
volatile uint32_t muteUntil = 0;      // while the speaker talks, the mic sends silence (no self-echo)
volatile float levelDb = -90;
volatile uint32_t dropped = 0;

enum Screen { CONNECTING, IDLE, CHECKIN, RELIEVED };
Screen screen = CONNECTING;
bool watching = false;
bool urgent = false;
uint32_t checkinEnds = 0, checkinTotal = 10000, relievedUntil = 0;
int blockIndex = 0;
String pendingText;
TaskHandle_t fetchTask;
uint32_t lastHeard = 0;           // when the server last said anything (USB link: the bridge pings)

// ── audio in ──────────────────────────────────────────────────────────────────

void micTask(void *) {
  for (;;) {
    int16_t *buf;
    xQueueReceive(freeQ, &buf, portMAX_DELAY);
    size_t got = 0;
    while (got < BLOCK * 2) got += i2s.readBytes((char *)buf + got, BLOCK * 2 - got);
    if (millis() < muteUntil) memset(buf, 0, BLOCK * 2);
    double sum = 0;
    for (int i = 0; i < BLOCK; i++) sum += (double)buf[i] * buf[i];
    levelDb = 10 * log10(sum / BLOCK / (32768.0 * 32768.0) + 1e-12);
    if (xQueueSend(fullQ, &buf, 0) != pdTRUE) {   // the network fell behind: drop the oldest block
      int16_t *old;
      if (xQueueReceive(fullQ, &old, 0) == pdTRUE) { xQueueSend(freeQ, &old, 0); dropped++; }
      xQueueSend(fullQ, &buf, 0);
    }
  }
}

void drainAudio() {
  int16_t *buf;
  while (xQueueReceive(fullQ, &buf, 0) == pdTRUE) xQueueSend(freeQ, &buf, 0);
  blockIndex = 0;
}

// ── speaker: "Are you OK? Say I'm OK." in the server's own voice ───────────────
// 16 kHz PCM goes into a stream buffer (from the Wi-Fi fetch below, or from the USB bridge);
// one task plays it. While it plays, the mic sends silence, so the server never hears the
// board's own "I'm OK".

StreamBufferHandle_t speakerBuf;

void speakerLoop(void *) {
  static uint8_t buf[1024];
  for (;;) {
    size_t n = xStreamBufferReceive(speakerBuf, buf, sizeof buf, portMAX_DELAY);
    if (!n) continue;
    muteUntil = millis() + 700;
    i2s.write(buf, n);
    muteUntil = millis() + 700;
  }
}

void fetchPromptLoop(void *) {   // Wi-Fi link: fetch the prompt from the server and resample it to 16 kHz
  for (;;) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    HTTPClient http;
    String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/static/voice/are-you-ok.wav";
    if (!http.begin(url) || http.GET() != 200) { http.end(); continue; }
    WiFiClient *in = http.getStreamPtr();
    uint8_t head[44];
    if (in->readBytes(head, 44) != 44) { http.end(); continue; }
    uint32_t inRate = head[24] | head[25] << 8 | head[26] << 16 | head[27] << 24;
    float step = (float)inRate / RATE, pos = 0;
    int16_t a = 0, b = 0, out[256];
    int n = 0;
    auto next = [&]() -> bool {
      uint8_t s[2];
      if (in->readBytes(s, 2) != 2) return false;
      a = b; b = (int16_t)(s[0] | s[1] << 8);
      return true;
    };
    next(); next();
    bool more = true;
    while (more) {
      while (pos >= 1.0f && more) { more = next(); pos -= 1.0f; }
      out[n++] = a + (b - a) * pos;
      pos += step;
      if (n == 256 || !more) { xStreamBufferSend(speakerBuf, out, n * 2, portMAX_DELAY); n = 0; }
    }
    http.end();
  }
}

// ── server messages ────────────────────────────────────────────────────────────

void onText(const char *text, size_t len) {
  lastHeard = millis();
  JsonDocument filter;
  for (auto k : {"type", "state", "timeout", "urgent", "ok"}) filter[k] = true;
  JsonDocument doc;
  if (deserializeJson(doc, text, len, DeserializationOption::Filter(filter))) return;
  String type = doc["type"] | "";
  if (type == "hello" || type == "state") {
    watching = String(doc["state"] | "standby") == "watching";
    if (screen == CONNECTING) screen = IDLE;
  } else if (type == "checkin") {
    urgent = doc["urgent"] | false;
    checkinTotal = (uint32_t)((float)(doc["timeout"] | 10.0f) * 1000);
    checkinEnds = millis() + checkinTotal;
    screen = CHECKIN;
    if (!LINK_USB) xTaskNotifyGive(fetchTask);   // over USB the bridge sends the prompt's audio itself
  } else if (type == "checkin_result") {
    bool ok = doc["ok"] | false;
    screen = ok ? RELIEVED : IDLE;
    relievedUntil = millis() + 2500;
  } else if (type == "alert") {
    if (screen == CHECKIN) screen = IDLE;   // stealth again: the alert itself is never shown
  }
}

// ── links ──────────────────────────────────────────────────────────────────────

// Board -> Mac frames on the USB link: A5 5A, type, length (2 bytes, little-endian), payload, then a
// CRC-16 (CCITT, little-endian) of type + length + payload, so the bridge drops any frame the USB
// link damaged instead of passing scrambled audio on.
//   'A' audio: a flags byte (1 = first block of a 4 s chunk, 2 = last, high 4 bits = block number)
//       + 0.25 s of PCM;  'T' JSON text.
// Mac -> board: A5 5A, type, length, payload (no CRC): 'J' a JSON message from the server,
// 'P' 16 kHz PCM for the speaker.
// Log lines (Serial.printf) go out between frames as plain text; the bridge prints them.
uint16_t crc16(uint16_t crc, const uint8_t *p, size_t n) {
  while (n--) {
    crc ^= (uint16_t)*p++ << 8;
    for (int i = 0; i < 8; i++) crc = crc & 0x8000 ? (crc << 1) ^ 0x1021 : crc << 1;
  }
  return crc;
}

void usbFrame(uint8_t type, const uint8_t *a, size_t na, const uint8_t *b = nullptr, size_t nb = 0) {
  uint8_t head[5] = {0xA5, 0x5A, type, (uint8_t)((na + nb) & 0xFF), (uint8_t)((na + nb) >> 8)};
  uint16_t crc = crc16(crc16(0xFFFF, head + 2, 3), a, na);
  if (nb) crc = crc16(crc, b, nb);
  uint8_t tail[2] = {(uint8_t)(crc & 0xFF), (uint8_t)(crc >> 8)};
  Serial.write(head, 5);
  Serial.write(a, na);
  if (nb) Serial.write(b, nb);
  Serial.write(tail, 2);
}

// Off, as far as a USB-powered board can be: the panel asleep, the backlight off and held off, and the
// chip in deep sleep with no wake-up source. RESET or replugging the cable brings Momo back. On the
// battery alone, BATTERY_EN is released too, which cuts the power.
void goToSleep() {
  Serial.println("sleep: screen off; press RESET or replug to wake");
  Serial.flush();
  lcd->displayOff();
  digitalWrite(LCD_BL, LOW);
  gpio_hold_en((gpio_num_t)LCD_BL);
  digitalWrite(BATTERY_EN, LOW);
  delay(50);
  esp_deep_sleep_start();
}

void usbRead() {
  static uint8_t buf[4100];
  static size_t have = 0;
  while (Serial.available()) {
    uint8_t c = Serial.read();
    if (have == 0 && c != 0xA5) continue;
    if (have == 1 && c != 0x5A) { have = 0; continue; }
    if (have < sizeof buf) buf[have++] = c;
    if (have >= 5) {
      size_t len = buf[3] | buf[4] << 8;
      if (len > sizeof buf - 5) { have = 0; continue; }
      if (have == 5 + len) {
        if (buf[2] == 'J') onText((const char *)buf + 5, len);
        else if (buf[2] == 'S') goToSleep();     // the Mac says: switch off
        else if (buf[2] == 'P') { lastHeard = millis(); xStreamBufferSend(speakerBuf, buf + 5, len, pdMS_TO_TICKS(200)); }
        have = 0;
      }
    }
  }
}

void sendAudio(bool linkUp) {
  int16_t *buf;
  while (xQueueReceive(fullQ, &buf, 0) == pdTRUE) {
    bool first = blockIndex == 0, last = blockIndex == BLOCKS_PER_CHUNK - 1;
    if (linkUp) {
      if (LINK_USB) {
        uint8_t flags = (first ? 1 : 0) | (last ? 2 : 0) | (blockIndex << 4);
        usbFrame('A', &flags, 1, (uint8_t *)buf, BLOCK * 2);
      } else {
        ws.sendFrame(first ? 2 : 0, last, (uint8_t *)buf, BLOCK * 2);
      }
    }
    xQueueSend(freeQ, &buf, 0);
    blockIndex = (blockIndex + 1) % BLOCKS_PER_CHUNK;
    if (blockIndex == 0 && linkUp && pendingText.length()) {
      if (LINK_USB) usbFrame('T', (const uint8_t *)pendingText.c_str(), pendingText.length());
      else ws.sendText(pendingText.c_str());
      pendingText = "";
    }
  }
}

void network() {
  static uint32_t lastTry = 0;
  if (LINK_USB) {
    usbRead();
    bool up = lastHeard && millis() - lastHeard < 15000;
    if (!up) screen = CONNECTING;
    else if (screen == CONNECTING) screen = IDLE;
    sendAudio(up);
    return;
  }
  if (WiFi.status() != WL_CONNECTED) {
    if (ws.connected()) ws.close();
    screen = CONNECTING;
    drainAudio();
    if (millis() - lastTry > 8000) {
      lastTry = millis();
      Serial.printf("wifi: joining \"%s\" (status %d)\n", WIFI_SSID, WiFi.status());
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    }
    return;
  }
  if (!ws.connected()) {
    screen = CONNECTING;
    drainAudio();
    if (millis() - lastTry > 3000) {
      lastTry = millis();
      Serial.printf("connecting to ws://%s:%d/ws ...\n", SERVER_HOST, SERVER_PORT);
      if (ws.connect(SERVER_HOST, SERVER_PORT, "/ws")) Serial.println("connected");
    }
    return;
  }
  sendAudio(true);
  ws.poll(onText);
}

// ── screen ─────────────────────────────────────────────────────────────────────

void centered(const char *text, int y, uint8_t size, uint16_t color) {
  int16_t x1, y1;
  uint16_t w, h;
  gfx->setTextSize(size);
  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  gfx->setTextColor(color);
  gfx->setCursor((240 - w) / 2 - x1, y);
  gfx->print(text);
}

void render() {
  uint32_t t = millis();
  static uint32_t nextBlink = 3000;
  bool blink = false;
  if (t > nextBlink) { blink = true; if (t > nextBlink + 140) nextBlink = t + 2500 + esp_random() % 3000; }
  int bob = (int)(4 * sinf(t / 700.0f));

  if (screen == CHECKIN) {
    uint32_t left = checkinEnds > t ? checkinEnds - t : 0;
    momo::sky(gfx, 70, 22, 40, 34, 14, 30, t);
    momo::draw(gfx, 120, 78 + bob / 2, 0.55f, momo::WORRIED, false, false, t);
    centered("Are you OK?", 150, 3, momo::WHITE);
    centered("Say \"I'm OK\"", 184, 2, momo::rgb(255, 190, 205));
    float frac = checkinTotal ? (float)left / checkinTotal : 0;
    gfx->fillArc(120, 236, 28, 23, 0, 360, momo::rgb(90, 50, 70));
    if (frac > 0) gfx->fillArc(120, 236, 28, 23, -90, -90 + 360 * frac, urgent ? momo::rgb(255, 90, 90) : momo::rgb(255, 150, 120));
    char num[4];
    snprintf(num, sizeof num, "%u", (unsigned)((left + 999) / 1000));
    centered(num, 229, 2, momo::WHITE);
    centered("hold BOOT: get help", 270, 1, momo::rgb(200, 150, 170));
  } else {
    if (screen == RELIEVED && t > relievedUntil) screen = IDLE;
    momo::sky(gfx, 38, 30, 70, 16, 18, 40, t);
    momo::Face face = screen == CONNECTING ? momo::SLEEPY : screen == RELIEVED ? momo::HAPPY : momo::AWAKE;
    momo::draw(gfx, 120, 140 + bob, 1.0f, face, watching && screen == IDLE, blink, t);
    if (screen == CONNECTING) {
      int z = (t / 400) % 3;
      for (int i = 0; i <= z; i++) centered("z", 60 - i * 16, 2 + i, momo::rgb(190, 180, 230));
    }
  }
  gfx->flush();
}

// ── setup / loop ───────────────────────────────────────────────────────────────

void setup() {
  pinMode(BATTERY_EN, OUTPUT);
  digitalWrite(BATTERY_EN, HIGH);
  pinMode(BOOT_BTN, INPUT_PULLUP);
  Serial.setRxBufferSize(16384);
  Serial.setTxBufferSize(16384);
  Serial.setTxTimeoutMs(500);   // wait for the Mac to read rather than drop audio bytes
  Serial.begin(115200);

  if (!gfx->begin()) Serial.println("display: no memory for the frame buffer");
  pinMode(LCD_BL, OUTPUT);
  digitalWrite(LCD_BL, HIGH);
  render();

  Wire.begin(I2C_SDA, I2C_SCL);
  codec = es8311_create(I2C_NUM_0, ES8311_ADDRESS_0);
  es8311_clock_config_t clk = {false, false, true, RATE * 256, RATE};
  es8311_init(codec, &clk, ES8311_RESOLUTION_16, ES8311_RESOLUTION_16);
  es8311_microphone_config(codec, false);
  es8311_microphone_gain_set(codec, MIC_GAIN_DB);
  es8311_voice_volume_set(codec, SPEAKER_VOLUME, NULL);
  i2s.setPins(I2S_BCLK, I2S_WS, I2S_DOUT, I2S_DIN, I2S_MCLK);
  if (!i2s.begin(I2S_MODE_STD, RATE, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO, I2S_STD_SLOT_LEFT))
    Serial.println("i2s: failed to start");

  freeQ = xQueueCreate(POOL, sizeof(int16_t *));
  fullQ = xQueueCreate(POOL, sizeof(int16_t *));
  for (int i = 0; i < POOL; i++) { int16_t *p = pool[i]; xQueueSend(freeQ, &p, 0); }
  xTaskCreate(micTask, "mic", 4096, NULL, 6, NULL);
  speakerBuf = xStreamBufferCreate(16384, 1);
  xTaskCreate(speakerLoop, "speaker", 3072, NULL, 5, NULL);
  if (!LINK_USB) xTaskCreate(fetchPromptLoop, "fetch", 6144, NULL, 4, &fetchTask);

  if (!LINK_USB) {
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  }
  Serial.printf("Watch Me Charm: %s link, heap %u after setup\n", LINK_USB ? "USB" : "Wi-Fi", ESP.getFreeHeap());
}

void loop() {
  network();

  static uint32_t pressedAt = 0;
  bool down = digitalRead(BOOT_BTN) == LOW;
  if (down && !pressedAt) pressedAt = millis();
  if (!down) pressedAt = 0;
  if (down && pressedAt && millis() - pressedAt > 1500 && screen == CHECKIN) {
    pendingText = "{\"type\":\"checkin_answer\",\"ok\":false}";   // "Get help now": raises the alert
    screen = IDLE;
    pressedAt = millis() + 600000;
  }

  static uint32_t lastFrame = 0;
  if (millis() - lastFrame >= 66) { lastFrame = millis(); render(); }
  delay(1);
}
