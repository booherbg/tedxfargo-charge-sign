// TEDxFargo CHARGE — custom effect mode functions.
//
// SHARED SOURCE OF TRUTH: this exact file compiles into BOTH the WLED firmware
// (via tedxfargo.cpp, after #include "wled.h") and the browser simulator (via
// sim/sim_main.cpp, after #include "wled_shim.h"). It must therefore use only
// the API surface the shim mirrors:
//   SEGMENT.fill/.setPixelColorXY/.is2D/.speed/.intensity
//   SEGENV.step/.aux0/.aux1/.call
//   strip.now, hw_random8(), qsub8(), color_fade(), color_blend(), RGBW32, BLACK
//   pgm_read_byte/pgm_read_word + the charge_geometry.h tables
// Do NOT include WLED headers here. (Editor lint on this file standalone is
// expected noise — it only compiles after wled.h or wled_shim.h.)
//
// DESIGN RULES for these effects:
// - Chain order IS tube order (greedy wiring), so "1D inside the letters"
//   means iterating a letter's contiguous chain range; the whole 0..458 chain
//   is one continuous tube path through all six letters.
// - Persistent randomness must be FRAME-COHERENT: derive it from charge_hash()
//   of stable inputs (letter, index, time window). hw_random8() is only for
//   ephemeral per-frame noise (flicker, sparks). This keeps every effect
//   deterministic in the simulator and frame-rate independent on the device.
// - Timers compare wrap-safe: (int32_t)(now - deadline) >= 0.
// - No allocation, no static mutable state; per-effect state only in SEGENV.
#pragma once
#include <stdint.h>
#include "charge_geometry.h"

#define CHARGE_CYAN     RGBW32(0, 255, 255, 0)     // electric CHARGE cyan
#define CHARGE_TEDX_RED RGBW32(235, 0, 40, 0)      // TEDx brand red (#EB0028)

// ---------- shared helpers over the geometry tables ----------
static inline uint16_t charge_lstart(uint8_t L) { return pgm_read_word(&CHARGE_LETTER_START[L]); }
static inline uint16_t charge_lcount(uint8_t L) { return pgm_read_word(&CHARGE_LETTER_COUNT[L]); }
static inline void charge_setpx(uint16_t i, uint32_t c) {
  SEGMENT.setPixelColorXY(pgm_read_byte(&CHARGE_COL[i]), pgm_read_byte(&CHARGE_ROW[i]), c);
}
// chain-position with wraparound (for effects that treat the chain as a loop)
static inline void charge_setpx_mod(int32_t i, uint32_t c) {
  int32_t n = CHARGE_NUM_PIXELS;
  charge_setpx((uint16_t)(((i % n) + n) % n), c);
}
// deterministic integer hash (lowbias32) — frame-coherent pseudo-randomness
static inline uint32_t charge_hash(uint32_t x) {
  x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16;
  return x;
}
// 0..255..0 triangle wave over `period` ms (period >= 2)
static inline uint8_t charge_tri8(uint32_t t, uint32_t period) {
  uint32_t ph = t % period, half = period / 2;
  uint32_t v = (ph < half) ? (ph * 255) / half : ((period - ph) * 255) / half;
  return (uint8_t)v;
}

// =====================================================================
// CHARGE Boot — neon ignition: letters flicker on C->H->A->R->G->E,
// settle to cyan, hold, loop. (First-cut effect; proven pipeline.)
// =====================================================================
static const char _data_CHARGE_BOOTUP[] PROGMEM = "CHARGE Boot@Speed,Flicker;;;2";

static void mode_charge_bootup() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }  // needs the matrix

  uint16_t letterMs = 900 - (SEGMENT.speed * 3);          // ~900..~135 ms per letter
  const uint16_t holdMs = 1500;
  uint32_t cycle = (uint32_t)letterMs * CHARGE_NUM_LETTERS + holdMs;

  if (SEGENV.step == 0 || (strip.now - SEGENV.step) > cycle) SEGENV.step = strip.now;  // (re)start
  uint32_t t = strip.now - SEGENV.step;

  SEGMENT.fill(BLACK);                                    // clear the matrix each frame
  uint8_t flicker = SEGMENT.intensity;                    // 0..255 flicker strength

  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint32_t litAt = (uint32_t)letterMs * L;
    if (t < litAt) continue;                               // not yet igniting
    uint32_t age = t - litAt;

    uint8_t bri = 255;
    if (age < letterMs) {                                  // igniting: ramp up with random dips
      uint8_t ramp = (uint8_t)((age * 255) / letterMs);
      uint8_t dip  = (hw_random8() < 128) ? (uint8_t)(hw_random8() % (uint16_t)(flicker + 1)) : 0;
      bri = qsub8(ramp, dip);
    }
    uint32_t col = color_fade(CHARGE_CYAN, bri, true);

    uint16_t start = charge_lstart(L), count = charge_lcount(L);
    for (uint16_t k = 0; k < count; k++) charge_setpx(start + k, col);
  }
}

// =====================================================================
// CHARGE Surge — electricity: current packets race the tube C->E over a
// dim charged glow; random sparks; every few seconds a letter takes a
// full arc-flash surge and dissipates.
// =====================================================================
static const char _data_CHARGE_SURGE[] PROGMEM = "CHARGE Surge@Speed,Energy;;;2;ix=160";

static void mode_charge_surge() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint32_t now = strip.now;

  // idle <-> surge state machine
  if (SEGENV.call == 0) { SEGENV.aux0 = 0; SEGENV.step = now + 1500; }
  if ((int32_t)(now - SEGENV.step) >= 0) {
    if (SEGENV.aux0 == 0) {                                  // start a letter surge
      SEGENV.aux0 = 1 + (hw_random8() % CHARGE_NUM_LETTERS);
      SEGENV.step = now + 260 + hw_random8();                // ~260..515 ms long
    } else {                                                 // back to idle
      SEGENV.aux0 = 0;
      SEGENV.step = now + 1800 + (uint32_t)hw_random8() * 16; // next in 1.8..5.9 s
    }
  }

  uint32_t bg = color_fade(CHARGE_CYAN, 30, true);           // charged-tube idle glow
  for (uint16_t i = 0; i < CHARGE_NUM_PIXELS; i++) charge_setpx(i, bg);

  // current packets racing the whole chain
  uint8_t np = 1 + (SEGMENT.intensity >> 5);                 // 1..8 packets
  uint32_t v = 60 + (uint32_t)SEGMENT.speed * 3;             // 60..825 px/s
  const uint16_t TAIL = 7;
  for (uint8_t p = 0; p < np; p++) {
    uint32_t head = (uint32_t)(((uint64_t)now * v / 1000 +
                    (uint32_t)p * CHARGE_NUM_PIXELS / np) % CHARGE_NUM_PIXELS);
    for (uint16_t k = 0; k <= TAIL; k++) {
      int32_t i = (int32_t)head - (int32_t)k;
      if (i < 0) break;                                      // chain isn't a loop
      uint32_t c = (k == 0) ? RGBW32(255, 255, 255, 0)
                 : color_fade(CHARGE_CYAN, (uint8_t)(255 - (k * 255) / (TAIL + 1)), true);
      charge_setpx((uint16_t)i, c);
    }
  }

  // stray sparks (ephemeral)
  for (uint8_t s = 0; s < (SEGMENT.intensity >> 6); s++) {
    uint16_t i = (uint16_t)(((((uint32_t)hw_random8() << 8) | hw_random8())) % CHARGE_NUM_PIXELS);
    charge_setpx(i, RGBW32(255, 255, 255, 0));
  }

  // the surging letter: arc-white flicker overlay
  if (SEGENV.aux0) {
    uint8_t bri = (hw_random8() < 140) ? (uint8_t)(255 - (hw_random8() % 120)) : 255;
    uint32_t c = color_fade(RGBW32(200, 255, 255, 0), bri, true);
    uint8_t L = (uint8_t)(SEGENV.aux0 - 1);
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    for (uint16_t k = 0; k < n; k++) charge_setpx(st + k, c);
  }
}

// =====================================================================
// CHARGE Comet — a white-hot head with a sparking cyan tail traces the
// entire neon path end to end (the wiring order IS the tube path).
// =====================================================================
static const char _data_CHARGE_COMET[] PROGMEM = "CHARGE Comet@Speed,Tail;;;2;sx=140,ix=96";

static void mode_charge_comet() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  SEGMENT.fill(BLACK);
  uint32_t now = strip.now;
  uint32_t v = 100 + (uint32_t)SEGMENT.speed * 4;            // 100..1120 px/s
  uint16_t tail = 8 + (SEGMENT.intensity >> 2);              // 8..71 px
  uint32_t total = (uint32_t)CHARGE_NUM_PIXELS + tail;       // run fully off the end
  uint32_t head = (uint32_t)((uint64_t)now * v / 1000 % total);
  for (uint16_t k = 0; k < tail; k++) {
    int32_t i = (int32_t)head - (int32_t)k;
    if (i < 0 || i >= CHARGE_NUM_PIXELS) continue;
    if (k < 2) { charge_setpx((uint16_t)i, RGBW32(255, 255, 255, 0)); continue; }
    uint8_t bri = (uint8_t)(((uint32_t)(tail - k) * 255) / tail);
    bri = qsub8(bri, hw_random8() & 63);                     // sparking decay
    charge_setpx((uint16_t)i, color_fade(CHARGE_CYAN, bri, true));
  }
}

// =====================================================================
// CHARGE Marquee — retro theater-bulb chase along the tubes: every Nth
// "bulb" lit warm amber, marching C->E; unlit bulbs ember faintly.
// =====================================================================
static const char _data_CHARGE_MARQUEE[] PROGMEM = "CHARGE Marquee@Speed,Spacing;;;2;ix=64";

static void mode_charge_marquee() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint8_t sp = 2 + (SEGMENT.intensity >> 6);                 // bulb spacing 2..5
  uint32_t stepMs = 40 + (uint32_t)(255 - SEGMENT.speed);    // 40..295 ms per step
  uint8_t phase = (uint8_t)((strip.now / stepMs) % sp);
  uint32_t bulb  = RGBW32(255, 170, 50, 0);
  uint32_t ember = color_fade(bulb, 18, true);
  for (uint16_t i = 0; i < CHARGE_NUM_PIXELS; i++)
    charge_setpx(i, ((i + sp - phase) % sp) == 0 ? bulb : ember);
}

// =====================================================================
// CHARGE Neon Morph — each letter drifts between electric cyan and TEDx
// red on its own phase; occasionally a letter "buzzes" like failing neon.
// =====================================================================
static const char _data_CHARGE_MORPH[] PROGMEM = "CHARGE Neon Morph@Speed,Buzz;;;2;ix=96";

static void mode_charge_morph() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint32_t now = strip.now;
  uint32_t P = 3000 + (uint32_t)(255 - SEGMENT.speed) * 40;  // 3..13.2 s morph period
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint8_t m = charge_tri8(now + (uint32_t)L * (P / 9), P); // staggered letters
    uint32_t c = color_blend(CHARGE_CYAN, CHARGE_TEDX_RED, m);
    // buzz: per-letter 512ms windows chosen by hash; dips inside are per-frame
    uint32_t win = (now >> 9) ^ ((uint32_t)L * 0x9E3779B1u);
    if ((charge_hash(win) & 0xFF) < (SEGMENT.intensity >> 2))
      if (hw_random8() < 160) c = color_fade(c, (uint8_t)(255 - (hw_random8() % 190)), true);
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    for (uint16_t k = 0; k < n; k++) charge_setpx(st + k, c);
  }
}

// =====================================================================
// CHARGE Pac-Man — each letter's tube is a maze corridor: a chomping pac
// eats pellets along the tube with a ghost in pursuit; pellets respawn
// each lap. Letters desync naturally (different tube lengths + offsets).
// =====================================================================
static const char _data_CHARGE_PACMAN[] PROGMEM = "CHARGE Pac-Man@Speed,Pellets;;;2";

static void mode_charge_pacman() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint32_t now = strip.now;
  uint32_t v256 = 1536 + (uint32_t)SEGMENT.speed * 32;       // 6..38 px/s (8.8 fixed)
  uint8_t sp = 3 + ((uint8_t)(255 - SEGMENT.intensity) >> 6); // pellet spacing 3..6
  static const uint32_t GHOSTC[4] = { RGBW32(255,0,0,0),    RGBW32(255,105,180,0),
                                      RGBW32(0,255,255,0),  RGBW32(255,140,0,0) };
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    uint32_t prog = (uint32_t)((uint64_t)now * v256 / 256000) + (charge_hash(L) & 63);
    uint32_t lap = prog / n;
    uint16_t pos = (uint16_t)(prog % n);
    for (uint16_t k = 0; k < n; k++) {                       // pellets ahead, eaten behind
      uint32_t c = ((k % sp) == 0 && k > pos)
                 ? color_fade(RGBW32(255, 220, 150, 0), 70, true) : BLACK;
      charge_setpx(st + k, c);
    }
    charge_setpx(st + pos, RGBW32(255, 210, 0, 0));          // pac (chomping 2nd px)
    if (((now / 130) & 1) && pos + 1u < n) charge_setpx(st + pos + 1, RGBW32(255, 210, 0, 0));
    if (lap > 0 || pos >= 7) {                               // ghost 7 px behind
      uint16_t g = (uint16_t)((pos + n - 7) % n);
      uint32_t gc = GHOSTC[L & 3];
      charge_setpx(st + g, gc);
      if (g + 1u < n) charge_setpx(st + g + 1, color_fade(gc, 120, true));
    }
  }
}

// =====================================================================
// CHARGE Lava — lava lamp per letter: hot wax blobs rise from the base
// and sink back (gravity dwell at the bottom), over a deep red liquid;
// a heater glow warms each letter's base.
// =====================================================================
static const char _data_CHARGE_LAVA[] PROGMEM = "CHARGE Lava@Speed,Blobs;;;2;sx=64";

static void mode_charge_lava() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint32_t now = strip.now;
  uint8_t nb = (uint8_t)(2 + SEGMENT.intensity / 86);        // 2..4 blobs per letter
  uint32_t base = 18000 - (uint32_t)SEGMENT.speed * 50;      // rise period 5.25..18 s
  uint32_t bg = color_fade(RGBW32(255, 40, 0, 0), 26, true); // deep red liquid
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    uint8_t hb[4], sig[4]; uint32_t bc[4];                   // blob height/size/color
    for (uint8_t b = 0; b < nb; b++) {
      uint32_t h = charge_hash(((uint32_t)L << 8) | b | 0xA5A50000u);
      uint32_t Pb = base * (205 + ((h & 0xFF) * 153) / 255) / 256;   // 0.8..1.4x
      uint8_t m = charge_tri8(now + (h >> 8), Pb);
      uint16_t e = (uint16_t)(((uint32_t)m * m * (765 - 2 * (uint32_t)m)) >> 16); // smoothstep
      hb[b]  = (uint8_t)(((uint32_t)e * e) / 255);           // gravity: dwell low
      sig[b] = (uint8_t)(30 + ((h >> 16) & 31));             // blob half-height 30..61
      bc[b]  = color_blend(RGBW32(255, 110, 8, 0), RGBW32(255, 0, 120, 0), (uint8_t)(h >> 24));
    }
    for (uint16_t k = 0; k < n; k++) {
      uint16_t i = st + k;
      uint8_t hp = pgm_read_byte(&CHARGE_HEIGHT[i]);
      uint8_t wbest = 0; uint32_t cbest = bg;
      for (uint8_t b = 0; b < nb; b++) {
        uint8_t d = (hp > hb[b]) ? (uint8_t)(hp - hb[b]) : (uint8_t)(hb[b] - hp);
        if (d >= sig[b]) continue;
        uint16_t wl = (uint16_t)(((uint16_t)(sig[b] - d) * 255) / sig[b]);
        uint8_t w = (uint8_t)(((uint32_t)wl * wl) >> 8);     // soft blob edge
        if (w > wbest) { wbest = w; cbest = bc[b]; }
      }
      uint32_t c = wbest ? color_blend(bg, cbest, wbest) : bg;
      if (hp < 40) c = color_blend(c, RGBW32(255, 90, 0, 0), (uint8_t)((40 - hp) * 3)); // heater
      charge_setpx(i, c);
    }
  }
}

// =====================================================================
// CHARGE Ants — the tubes are ant tunnels: each letter's colony forages
// out from a breathing nest at the tube mouth and hauls glinting green
// food back home. Ant speeds vary per ant (deterministic).
// =====================================================================
static const char _data_CHARGE_ANTS[] PROGMEM = "CHARGE Ants@Speed,Ants;;;2;sx=96";

static void mode_charge_ants() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint32_t now = strip.now;
  uint8_t na = (uint8_t)(2 + SEGMENT.intensity / 52);        // 2..6 ants per letter
  uint32_t vbase = 4 + (SEGMENT.speed >> 3);                 // 4..35 px/s
  uint32_t tunnel = color_fade(RGBW32(180, 120, 60, 0), 12, true);
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    for (uint16_t k = 0; k < n; k++) charge_setpx(st + k, tunnel);
    uint8_t nestb = (uint8_t)(60 + (charge_tri8(now, 2400) >> 1));   // breathing nest
    charge_setpx(st, color_fade(RGBW32(255, 160, 40, 0), nestb, true));
    if (n > 1) charge_setpx(st + 1, color_fade(RGBW32(255, 160, 40, 0), nestb >> 1, true));
    for (uint8_t a = 0; a < na; a++) {
      uint32_t h = charge_hash(((uint32_t)L << 16) | a | 0x50F00000u);
      uint32_t va = vbase * (179 + (h & 0x7F)) / 256;        // 0.70..1.19x speed
      if (va == 0) va = 1;
      uint32_t rt = (uint32_t)(((uint64_t)now * va / 1000 + (h >> 8)) % (2u * n));
      bool carrying = rt >= n;                               // out = forage, back = haul
      uint16_t pos = carrying ? (uint16_t)(2u * n - 1 - rt) : (uint16_t)rt;
      charge_setpx(st + pos, carrying ? RGBW32(160, 90, 20, 0)
                                      : color_fade(RGBW32(200, 120, 30, 0), 140, true));
      if (carrying && pos > 0)                               // the food glints homeward
        charge_setpx(st + pos - 1, RGBW32(120, 255, 120, 0));
    }
  }
}

// =====================================================================
// CHARGE Raider — old-school side-scroller: a ship flies the whole neon
// path like a tunnel run, rocket jet blazing, firing bolts at aliens
// ahead; hits burst into multicolor explosions. Periodic boosts flare
// the jet blue-white. (Level loops = next stage.)
// =====================================================================
static const char _data_CHARGE_RAIDER[] PROGMEM = "CHARGE Raider@Speed,Enemies;;;2;sx=140";

static void mode_charge_raider() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  SEGMENT.fill(BLACK);
  uint32_t now = strip.now;
  const int32_t N = CHARGE_NUM_PIXELS;
  uint32_t v = 40 + (uint32_t)SEGMENT.speed;                 // ship 40..295 px/s
  uint32_t travel = (uint32_t)((uint64_t)now * v / 1000);
  uint16_t ship = (uint16_t)(travel % (uint32_t)N);
  uint32_t lap = travel / (uint32_t)N;

  // boost: ~75% of 6s windows get a 1.3s flare
  uint32_t bph = now % 6000;
  bool boost = ((charge_hash(now / 6000) & 3) != 0) && bph < 1300;

  // rocket jet (behind the ship): color ramp + per-frame flame noise
  uint8_t jetlen = boost ? 18 : 9;
  for (uint8_t k = 1; k <= jetlen; k++) {
    uint8_t frac = (uint8_t)(((uint16_t)k * 255) / jetlen);
    uint32_t c = boost ? color_blend(RGBW32(170, 220, 255, 0), RGBW32(30, 60, 255, 0), frac)
                       : color_blend(RGBW32(255, 220, 60, 0), RGBW32(255, 30, 0, 0), frac);
    uint8_t bri = (uint8_t)(((uint16_t)(jetlen - k + 1) * 255) / (jetlen + 1));
    bri = qsub8(bri, hw_random8() & 60);                     // flame flicker
    charge_setpx_mod((int32_t)ship - k, color_fade(c, bri, true));
  }
  // ship body: cyan hull + white nose (white-hot all over during boost)
  charge_setpx_mod(ship, boost ? RGBW32(255, 255, 255, 0) : CHARGE_CYAN);
  charge_setpx_mod((int32_t)ship + 1, RGBW32(255, 255, 255, 0));

  // enemies ahead on the level; each dies to a bolt as the ship closes in
  uint8_t ne = (uint8_t)(2 + (SEGMENT.intensity >> 5));      // 2..9 per lap
  static const uint32_t ALIENC[3] = { RGBW32(255,0,90,0), RGBW32(140,255,0,0),
                                      RGBW32(255,60,0,0) };
  for (uint8_t j = 0; j < ne; j++) {
    uint32_t hj = charge_hash(lap * 31 + j + 0xE11E0000u);
    int32_t E = (int32_t)(((uint32_t)j * (uint32_t)N) / ne + (hj % 24)) % N;
    int32_t d = E - (int32_t)ship; if (d < 0) d += N;        // distance ahead 0..N-1
    if (d > 40 && d < 160) {                                 // alive: pulsing alien
      uint8_t bri = (uint8_t)(140 + (charge_tri8(now + j * 997u, 700) >> 2));
      uint32_t ac = color_fade(ALIENC[hj % 3], bri, true);
      charge_setpx_mod(E, ac);
      charge_setpx_mod(E + 1, color_fade(ac, 120, true));
    } else if (d > 24 && d <= 40) {                          // hit: multicolor burst
      uint8_t age = (uint8_t)(((uint32_t)(d - 24) * 255) / 16); // 255 at impact -> 0
      uint8_t r = (uint8_t)(1 + (40 - d) / 5);               // expanding 1..4 px
      for (int8_t o = -(int8_t)r; o <= (int8_t)r; o++) {
        uint32_t hc = charge_hash(hj ^ (uint32_t)(o + 16) ^ (now >> 6));
        uint32_t c = color_blend(RGBW32(255, 200, 0, 0), RGBW32(255, 0, 200, 0), (uint8_t)hc);
        charge_setpx_mod(E + o, color_fade(c, age, true));
      }
    }
    // bolt in flight (launched at d=60, closes at 2x ship speed, hits at d=40)
    if (d > 40 && d < 60) {
      int32_t bolt = (int32_t)ship + 2 + (60 - d) * 2;
      charge_setpx_mod(bolt, RGBW32(255, 255, 180, 0));
      charge_setpx_mod(bolt - 1, color_fade(RGBW32(255, 255, 180, 0), 90, true));
    }
  }
}

// Registration table so firmware + simulator enumerate the same effect list.
// Extend here when adding effects; tedxfargo.cpp and the sim both walk it.
typedef void (*charge_mode_fn)();
struct ChargeFxEntry { charge_mode_fn fn; const char* meta; };
static const ChargeFxEntry CHARGE_FX_LIST[] = {
  { &mode_charge_bootup,  _data_CHARGE_BOOTUP },
  { &mode_charge_surge,   _data_CHARGE_SURGE },
  { &mode_charge_comet,   _data_CHARGE_COMET },
  { &mode_charge_marquee, _data_CHARGE_MARQUEE },
  { &mode_charge_morph,   _data_CHARGE_MORPH },
  { &mode_charge_pacman,  _data_CHARGE_PACMAN },
  { &mode_charge_lava,    _data_CHARGE_LAVA },
  { &mode_charge_ants,    _data_CHARGE_ANTS },
  { &mode_charge_raider,  _data_CHARGE_RAIDER },
};
static const uint8_t CHARGE_FX_COUNT =
    sizeof(CHARGE_FX_LIST) / sizeof(CHARGE_FX_LIST[0]);
