// Momo, the Charm's character: a round mochi cat drawn from shapes, so it needs no image files.
// The same Momo shows whether Watch Me is listening or not (stealth: nothing tells anyone nearby
// that it is on). The only hint is for her: while watching, the sparkles in Momo's eyes are hearts.
#pragma once
#include <Arduino_GFX_Library.h>

namespace momo {

inline uint16_t rgb(uint8_t r, uint8_t g, uint8_t b) { return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3); }

const uint16_t BODY = rgb(255, 238, 244), SHADE = rgb(246, 214, 228), EAR_IN = rgb(255, 176, 198),
               INK = rgb(58, 42, 70), BLUSH = rgb(255, 150, 178), WHITE = rgb(255, 255, 255),
               HEART = rgb(255, 92, 138), TEAR = rgb(150, 205, 255);

enum Face { AWAKE, SLEEPY, WORRIED, HAPPY };

inline void heart(Arduino_GFX *g, int x, int y, float r, uint16_t c) {
  int k = max(1, (int)r);
  g->fillCircle(x - k, y, k, c);
  g->fillCircle(x + k, y, k, c);
  g->fillTriangle(x - 2 * k, y + k / 2, x + 2 * k, y + k / 2, x, y + 3 * k, c);
}

// Vertical gradient between two colours, plus a few twinkling stars.
inline void sky(Arduino_GFX *g, uint8_t r0, uint8_t g0, uint8_t b0, uint8_t r1, uint8_t g1, uint8_t b1, uint32_t t) {
  int h = g->height(), w = g->width();
  for (int y = 0; y < h; y += 2) {
    float f = (float)y / h;
    g->fillRect(0, y, w, 2, rgb(r0 + (r1 - r0) * f, g0 + (g1 - g0) * f, b0 + (b1 - b0) * f));
  }
  static const int16_t stars[][2] = {{28, 30}, {206, 46}, {40, 222}, {196, 238}, {120, 18}, {222, 150}, {16, 140}};
  for (int i = 0; i < 7; i++) {
    float tw = 0.5f + 0.5f * sinf(t / 600.0f + i * 1.7f);
    if (tw > 0.35f) {
      uint8_t v = 120 + 120 * tw;
      g->fillCircle(stars[i][0], stars[i][1], tw > 0.8f ? 2 : 1, rgb(v, v, v));
    }
  }
}

// Draw Momo centred at (cx, cy), `s` = scale (1.0 is about 160 px wide).
inline void draw(Arduino_GFX *g, int cx, int cy, float s, Face face, bool hearts, bool blink, uint32_t t) {
  auto S = [s](float v) { return (int)(v * s); };
  // feet and body
  g->fillEllipse(cx - S(34), cy + S(58), S(18), S(9), SHADE);
  g->fillEllipse(cx + S(34), cy + S(58), S(18), S(9), SHADE);
  // ears (behind the head's top)
  g->fillTriangle(cx - S(70), cy - S(18), cx - S(54), cy - S(86), cx - S(14), cy - S(52), BODY);
  g->fillTriangle(cx + S(70), cy - S(18), cx + S(54), cy - S(86), cx + S(14), cy - S(52), BODY);
  g->fillTriangle(cx - S(58), cy - S(30), cx - S(52), cy - S(70), cx - S(28), cy - S(50), EAR_IN);
  g->fillTriangle(cx + S(58), cy - S(30), cx + S(52), cy - S(70), cx + S(28), cy - S(50), EAR_IN);
  g->fillEllipse(cx, cy, S(80), S(64), BODY);
  g->fillEllipse(cx, cy + S(40), S(56), S(18), SHADE);   // soft shadow under the chin
  g->fillEllipse(cx, cy + S(30), S(66), S(20), BODY);

  int ex = S(30), ey = cy - S(4);
  // blush
  g->fillEllipse(cx - S(50), cy + S(16), S(12), S(6), BLUSH);
  g->fillEllipse(cx + S(50), cy + S(16), S(12), S(6), BLUSH);

  for (int side = -1; side <= 1; side += 2) {
    int x = cx + side * ex;
    if (face == SLEEPY || (blink && face != HAPPY)) {
      g->fillArc(x, ey, S(10), S(7), 20, 160, INK);          // closed: a gentle downward curve
    } else if (face == HAPPY) {
      g->fillArc(x, ey + S(6), S(11), S(8), 200, 340, INK);  // ^ ^
    } else {
      g->fillEllipse(x, ey, S(10), S(13), INK);
      if (hearts) heart(g, x + S(3), ey - S(7), 2.6f * s, HEART);
      else g->fillCircle(x + S(3), ey - S(5), S(4), WHITE);
      g->fillCircle(x - S(4), ey + S(5), max(1, S(2)), WHITE);
    }
    if (face == WORRIED) {   // eyebrows slanting up in the middle
      g->fillTriangle(x - side * S(12), ey - S(30), x + side * S(12), ey - S(20), x + side * S(10), ey - S(16), INK);
    }
  }

  // mouth
  if (face == WORRIED) {
    g->fillEllipse(cx, cy + S(20), S(6), S(7), INK);
    g->fillEllipse(cx, cy + S(21), S(4), S(4), rgb(255, 120, 150));
    float d = fmodf(t / 900.0f, 1.0f);                       // a sweat drop that slides down
    int dx = cx + S(66), dy = cy - S(42) + S(14 * d);
    g->fillCircle(dx, dy, S(6), TEAR);
    g->fillTriangle(dx - S(6), dy - S(1), dx + S(6), dy - S(1), dx, dy - S(12), TEAR);
  } else if (face == SLEEPY) {
    g->fillEllipse(cx, cy + S(18), S(4), S(3), INK);
  } else {
    g->fillArc(cx - S(6), cy + S(14), S(7), S(5), 10, 170, INK);   // a little "w"
    g->fillArc(cx + S(6), cy + S(14), S(7), S(5), 10, 170, INK);
  }
}

}  // namespace momo
