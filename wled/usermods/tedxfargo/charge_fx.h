// TEDxFargo CHARGE — custom effect mode functions.
//
// SHARED SOURCE OF TRUTH: this exact file compiles into BOTH the WLED firmware
// (via tedxfargo.cpp, after #include "wled.h") and the browser simulator (via
// sim/sim_main.cpp, after #include "wled_shim.h"). It must therefore use only
// the API surface the shim mirrors:
//   SEGMENT.fill/.setPixelColorXY/.is2D/.speed/.intensity/.custom1..3/.check1..3
//   SEGENV.step/.aux0/.aux1/.call
//   strip.now, hw_random8(), qsub8(), color_fade(), color_blend(), RGBW32, BLACK
//   pgm_read_byte/pgm_read_word + the charge_geometry.h tables
// plus the two platform-glue functions declared below (charge_audio*), which
// tedxfargo.cpp implements from the audioreactive usermod and the sim
// implements from a JS-settable level (synthetic beat or real microphone).
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
// - custom3 is a 5-bit slider in WLED (0..31) — avoid it; use custom1/2.
#pragma once
#include <stdint.h>
#include "charge_geometry.h"

#define CHARGE_CYAN     RGBW32(0, 255, 255, 0)     // electric CHARGE cyan
#define CHARGE_TEDX_RED RGBW32(235, 0, 40, 0)      // TEDx brand red (#EB0028)

// platform glue — smoothed audio level 0..255 and beat/peak flag.
// Firmware: audioreactive um_data (volumeSmth/samplePeak, with WLED's
// simulateSound fallback). Simulator: JS-fed (synthetic beat or microphone).
uint8_t charge_audio();
uint8_t charge_audio_peak();

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

// ---------- mini gradient palettes (goblin-curated, 4 stops each) ----------
// Effects with a "Palette" slider map it as index = custom / 32 (8 palettes).
struct ChargePal { uint32_t c[4]; };
static const ChargePal CHARGE_PALS[8] = {
  {{ CHARGE_CYAN, RGBW32(0,120,255,0), RGBW32(180,0,255,0), CHARGE_TEDX_RED }},   // 0 brand trip
  {{ RGBW32(255,30,0,0), RGBW32(255,110,0,0), RGBW32(255,220,40,0), RGBW32(255,255,255,0) }}, // 1 fire
  {{ RGBW32(255,0,0,0), RGBW32(255,255,0,0), RGBW32(0,255,80,0), RGBW32(0,80,255,0) }},       // 2 rainbow
  {{ RGBW32(40,255,40,0), RGBW32(0,200,80,0), RGBW32(180,255,0,0), RGBW32(230,255,230,0) }},  // 3 slime
  {{ RGBW32(255,0,180,0), RGBW32(120,0,255,0), RGBW32(0,255,255,0), RGBW32(255,255,0,0) }},   // 4 psychedelic
  {{ CHARGE_TEDX_RED, RGBW32(255,255,255,0), CHARGE_TEDX_RED, RGBW32(40,0,8,0) }},            // 5 TEDx
  {{ RGBW32(0,0,255,0), RGBW32(0,255,255,0), RGBW32(255,255,255,0), RGBW32(0,120,255,0) }},   // 6 electric ice
  {{ RGBW32(255,140,0,0), RGBW32(255,0,90,0), RGBW32(140,0,255,0), RGBW32(0,255,200,0) }},    // 7 sunset acid
};
static inline uint32_t charge_palette(uint8_t pal, uint8_t pos) {
  const ChargePal &P = CHARGE_PALS[pal & 7];
  uint8_t seg = pos / 85; if (seg > 2) seg = 2;
  uint8_t frac = (uint8_t)((pos - seg * 85) * 3);
  return color_blend(P.c[seg], P.c[seg + 1], frac);
}
// The same palettes in WLED gradient-palette byte format (pos,r,g,b x 4).
// tedxfargo.cpp registers these as NATIVE usermod palettes (IDs 255 down to
// 248) so stock WLED effects can use them too; the sim registers identical
// bytes at identical IDs. User-facing palette selection in our effects goes
// through SEGMENT.color_from_palette(); CHARGE_PALS/charge_palette above stay
// for internal fixed uses only (rainbow jet/tail novelties).
#define CHARGE_UM_PAL_COUNT 8
// rows hold up to 7 gradient stops (28 bytes); shorter palettes terminate at
// their pos-255 stop and pad with zeros (gradient loaders stop at 255)
static const uint8_t CHARGE_UM_PAL_DATA[CHARGE_UM_PAL_COUNT][28] PROGMEM = {
  { 0,0,255,255,    85,0,120,255,   170,180,0,255,  255,235,0,40,    0,0,0,0, 0,0,0,0, 0,0,0,0 }, // 255 Brand Trip
  { 0,255,30,0,     85,255,110,0,   170,255,220,40, 255,255,255,255, 0,0,0,0, 0,0,0,0, 0,0,0,0 }, // 254 Fire
  { 0,255,0,0,      85,255,255,0,   170,0,255,80,   255,0,80,255,    0,0,0,0, 0,0,0,0, 0,0,0,0 }, // 253 Rainbow
  { 0,40,255,40,    85,0,200,80,    170,180,255,0,  255,230,255,230, 0,0,0,0, 0,0,0,0, 0,0,0,0 }, // 252 Slime
  { 0,255,0,180,    85,120,0,255,   170,0,255,255,  255,255,255,0,   0,0,0,0, 0,0,0,0, 0,0,0,0 }, // 251 Psychedelic
  // TEDx: modeled on the device's custom palette 0 (the sign's art colors) —
  // teal and BOLD red as the mains, yellow as a narrow accent between them
  { 0,0,243,251,    88,0,255,255,   112,255,247,0,  136,255,42,42,   255,255,0,0, 0,0,0,0, 0,0,0,0 }, // 250 TEDx
  { 0,0,0,255,      85,0,255,255,   170,255,255,255,255,0,120,255,   0,0,0,0, 0,0,0,0, 0,0,0,0 }, // 249 Electric Ice
  { 0,255,140,0,    85,255,0,90,    170,140,0,255,  255,0,255,200,   0,0,0,0, 0,0,0,0, 0,0,0,0 }, // 248 Sunset Acid
};
static const char* const CHARGE_UM_PAL_NAMES[CHARGE_UM_PAL_COUNT] = {
  "Brand Trip", "Fire", "Rainbow", "Slime",
  "Psychedelic", "TEDx", "Electric Ice", "Sunset Acid",
};
// smoothstep on a byte: 0..255 -> 0..255 with eased ends
static inline uint8_t charge_smooth8(uint8_t v) {
  return (uint8_t)(((uint32_t)v * v * (765 - 2 * (uint32_t)v)) >> 16);
}
// fast octagonal distance approximation in grid cells (max + min/2 ~ Euclidean)
static inline uint8_t charge_dist8(int16_t dx, int16_t dy) {
  if (dx < 0) dx = (int16_t)-dx;
  if (dy < 0) dy = (int16_t)-dy;
  int16_t mx = dx > dy ? dx : dy, mn = dx > dy ? dy : dx;
  int16_t d = (int16_t)(mx + (mn >> 1));
  return d > 255 ? 255 : (uint8_t)d;
}
// per-letter centroid in GRID (col,row) coordinates — one pass over the chain
static inline void charge_letter_centroids(uint8_t cx[CHARGE_NUM_LETTERS],
                                           uint8_t cy[CHARGE_NUM_LETTERS]) {
  uint32_t ax[CHARGE_NUM_LETTERS] = {0}, ay[CHARGE_NUM_LETTERS] = {0};
  for (uint16_t i = 0; i < CHARGE_NUM_PIXELS; i++) {
    uint8_t L = pgm_read_byte(&CHARGE_LETTER[i]);
    ax[L] += pgm_read_byte(&CHARGE_COL[i]);
    ay[L] += pgm_read_byte(&CHARGE_ROW[i]);
  }
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint16_t n = charge_lcount(L);
    cx[L] = (uint8_t)(ax[L] / n);
    cy[L] = (uint8_t)(ay[L] / n);
  }
}
// Manhattan RGB distance — used to keep adjacent letters visibly different
static inline uint16_t charge_coldist(uint32_t a, uint32_t b) {
  int16_t dr = (int16_t)((a >> 16) & 255) - (int16_t)((b >> 16) & 255);
  int16_t dg = (int16_t)((a >> 8) & 255)  - (int16_t)((b >> 8) & 255);
  int16_t db = (int16_t)(a & 255)         - (int16_t)(b & 255);
  return (uint16_t)((dr < 0 ? -dr : dr) + (dg < 0 ? -dg : dg) + (db < 0 ? -db : db));
}
// Pick 6 per-letter colors from the CURRENT segment palette, re-rolling so
// each letter differs visibly from its left neighbor when the palette allows
// it (greedy; right neighbor is handled on its own turn). `primaries` draws
// from the 6 evenly spaced palette positions; else positions are seed-random.
static inline void charge_letter_colors(uint32_t seed, bool primaries,
                                        uint32_t out[CHARGE_NUM_LETTERS]) {
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint32_t best = 0; uint16_t bestd = 0;
    for (uint8_t c = 0; c < 6; c++) {
      uint32_t h = charge_hash(seed ^ ((uint32_t)L << 8) ^ ((uint32_t)c * 0x9E3779B1u));
      uint8_t pos = primaries ? (uint8_t)((h % 6) * 51) : (uint8_t)h;
      uint32_t col = SEGMENT.color_from_palette(pos, false, true, 255);
      if (L == 0) { best = col; break; }
      uint16_t d = charge_coldist(col, out[L - 1]);
      if (d >= 90) { best = col; break; }                    // distinct enough — take it
      if (d >= bestd) { bestd = d; best = col; }             // else keep the most distinct
    }
    out[L] = best;
  }
}

// per-letter x-extent in XNORM units (scanned on demand; letters are ~80 px)
static inline void charge_letter_xrange(uint8_t L, uint8_t *xlo, uint8_t *xhi) {
  uint16_t st = charge_lstart(L), n = charge_lcount(L);
  uint8_t lo = 255, hi = 0;
  for (uint16_t k = 0; k < n; k++) {
    uint8_t x = pgm_read_byte(&CHARGE_XNORM[st + k]);
    if (x < lo) lo = x;
    if (x > hi) hi = x;
  }
  *xlo = lo; *xhi = hi;
}

// =====================================================================
// CHARGE Boot — neon ignition: letters flicker on C->H->A->R->G->E,
// settle, hold (Hold slider), loop. Palette 'Default' = the classic neon
// cyan; any other palette colors the ignition — one random palette color
// per cycle, or a different random color per letter ("Letter colors").
// "Electrify": during the hold, white lightning blasts through the whole
// tube path left to right, leaving an overcharge glow that cools off.
// =====================================================================
static const char _data_CHARGE_BOOTUP[] PROGMEM =
  "CHARGE Boot@Ignite time,Flicker,Hold,,,Letter colors,Electrify;!,!,!;!;2;sx=128,ix=128,c1=70,o1=0,o2=0,pal=0";

static void mode_charge_bootup() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }  // needs the matrix

  // Ignite time: slow half stretches way out (2.2s/letter at 0), default and
  // fast end unchanged (~536ms at 128, ~155ms at 255)
  uint16_t letterMs = (SEGMENT.speed < 128)
      ? (uint16_t)(2200 - SEGMENT.speed * 13)
      : (uint16_t)(536 - (SEGMENT.speed - 128) * 3);
  uint32_t holdMs = 300 + (uint32_t)SEGMENT.custom1 * 20; // 300..5400 ms
  uint32_t cycle = (uint32_t)letterMs * CHARGE_NUM_LETTERS + holdMs;

  if (SEGENV.step == 0 || (strip.now - SEGENV.step) > cycle) SEGENV.step = strip.now;  // (re)start
  uint32_t t = strip.now - SEGENV.step;

  SEGMENT.fill(BLACK);                                    // clear the matrix each frame
  uint8_t flicker = SEGMENT.intensity;                    // 0..255 flicker strength
  // ease down at the end of the hold so the loop doesn't hard-cut to black
  uint32_t fadeMs = holdMs / 2 > 450 ? 450 : holdMs / 2;
  uint8_t gfade = (t > cycle - fadeMs) ? (uint8_t)(((cycle - t) * 255) / fadeMs) : 255;

  // color seed: stable within a cycle, re-rolled every loop (step = cycle start)
  uint32_t seed = charge_hash(SEGENV.step | 1u);
  uint32_t seqColor = (SEGMENT.palette == 0)              // Default = classic neon cyan
      ? CHARGE_CYAN
      : SEGMENT.color_from_palette((uint8_t)seed, false, true, 255);
  uint32_t lettercols[CHARGE_NUM_LETTERS];
  bool perLetter = SEGMENT.check1 && SEGMENT.palette != 0;
  if (perLetter) charge_letter_colors(seed, false, lettercols);  // neighbors kept distinct

  uint32_t litcol[CHARGE_NUM_LETTERS];                    // per-letter drawn color (for electrify)
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    litcol[L] = BLACK;
    uint32_t litAt = (uint32_t)letterMs * L;
    if (t < litAt) continue;                               // not yet igniting
    uint32_t age = t - litAt;

    uint8_t bri = 255;
    if (age < letterMs) {                                  // igniting: ramp up with random dips
      uint8_t ramp = (uint8_t)((age * 255) / letterMs);
      uint8_t dip  = (hw_random8() < 128) ? (uint8_t)(hw_random8() % (uint16_t)(flicker + 1)) : 0;
      bri = qsub8(ramp, dip);
    }
    bri = (uint8_t)(((uint16_t)bri * gfade) / 255);
    uint32_t basec = perLetter ? lettercols[L] : seqColor;
    uint32_t col = color_fade(basec, bri, true);
    litcol[L] = col;

    uint16_t start = charge_lstart(L), count = charge_lcount(L);
    for (uint16_t k = 0; k < count; k++) charge_setpx(start + k, col);
  }

  // Electrify: during the hold, lightning rips through the tube C -> E
  if (SEGMENT.check2) {
    uint32_t litEnd = (uint32_t)letterMs * CHARGE_NUM_LETTERS;
    uint32_t holdLen = (cycle - fadeMs > litEnd) ? (cycle - fadeMs - litEnd) : 0;
    if (t >= litEnd && holdLen > 500) {
      const uint32_t TRAVEL = 300;                         // bolt crosses the sign in 300ms
      const int32_t  OVER = 24;                            // spawn/exit off the ends
      uint8_t nStrikes = (uint8_t)(1 + holdLen / 1600);    // more hold = more strikes
      if (nStrikes > 3) nStrikes = 3;
      uint32_t slice = holdLen / nStrikes;
      for (uint8_t sk = 0; sk < nStrikes; sk++) {
        uint32_t jitter = (slice > 800) ? charge_hash(seed ^ (0xB017u + sk)) % (slice - 800) : 0;
        uint32_t at = litEnd + sk * slice + jitter;
        if (t < at) continue;
        uint32_t age = t - at;
        if (age >= TRAVEL + 450) continue;                 // strike fully cooled
        int32_t front = (int32_t)(((uint64_t)age * (CHARGE_NUM_PIXELS + 2 * OVER)) / TRAVEL) - OVER;
        for (uint16_t i = 0; i < CHARGE_NUM_PIXELS; i++) {
          int32_t d = front - (int32_t)i;
          if (d < 0) continue;                             // bolt hasn't reached this pixel
          uint32_t base = litcol[pgm_read_byte(&CHARGE_LETTER[i])];
          if (d < 10) {                                    // white-hot bolt head
            uint8_t w = (uint8_t)(255 - d * 18);
            w = qsub8(w, (uint8_t)(hw_random8() & 40));    // crackle
            w = (uint8_t)(((uint16_t)w * gfade) / 255);
            charge_setpx(i, color_blend(base, RGBW32(255, 255, 255, 0), w));
          } else {                                         // overcharge glow cooling off
            uint32_t passed = ((uint32_t)d * TRAVEL) / (CHARGE_NUM_PIXELS + 2 * OVER);
            if (passed < 420) {
              uint8_t w = (uint8_t)(200 - (passed * 200) / 420);
              w = (uint8_t)(((uint16_t)w * gfade) / 255);
              charge_setpx(i, color_blend(base, RGBW32(255, 255, 255, 0), w));
            }
          }
        }
        // branch crackle: stray sparks bursting off around the bolt head
        for (uint8_t b = 0; b < 3; b++) {
          int32_t bi = front - 5 + (int32_t)(hw_random8() % 24) - 9;
          if (bi >= 0 && bi < CHARGE_NUM_PIXELS && hw_random8() < 170)
            charge_setpx((uint16_t)bi, color_fade(RGBW32(255, 255, 255, 0),
                          (uint8_t)(((uint16_t)(160 + (hw_random8() % 96)) * gfade) / 255), true));
        }
      }
    }
  }
}

// =====================================================================
// CHARGE Surge — electricity: current packets race the tube C->E over a
// dim charged glow; letters take arc-flash surges on a rate you control.
// "Accumulate": surged letters STAY lit until all six are on, hold, then
// flicker out together electrically and the cycle restarts. Palettes:
// 'Default' = the classic cyan; otherwise "Letter colors" gives each
// letter a palette primary (samples at L*51), else one new palette color
// per cycle — packets take the color of the letter they're passing
// through. "Color wave" (needs Accumulate + a palette): once all six are
// on, a pulse of the full palette washes left to right, leaves the sign
// white-hot, then the flicker-out. Sparks now scale with Energy (no
// checkbox; Energy < 64 disables them).
// =====================================================================
static const char _data_CHARGE_SURGE[] PROGMEM =
  "CHARGE Surge@Speed,Energy,Surge rate,,,Accumulate,Color wave,Letter colors;!,!,!;!;2;sx=128,ix=160,c1=128,o1=0,o2=0,o3=0,pal=0";

static void mode_charge_surge() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint32_t now = strip.now;
  bool acc = SEGMENT.check1;
  bool usePal = SEGMENT.palette != 0;

  // phases in aux0: 0 idle, 1..6 surging letter L=aux0-1, 7 hold-all,
  // 8 color wave, 9 white hold, 10 flicker-out.
  // aux1: bits 0-5 = held-letter mask (Accumulate), bits 8-15 = cycle color seed.
  const uint32_t HOLDALL_MS = 900, WAVE_MS = 1400, WHITE_MS = 450, FLICK_MS = 750;
  if (SEGENV.call == 0) {
    SEGENV.aux0 = 0;
    SEGENV.aux1 = (uint16_t)((uint16_t)hw_random8() << 8);
    SEGENV.step = now + 1500;
  }
  if (!acc && SEGENV.aux0 > 6) {                             // Accumulate switched off mid-cycle
    SEGENV.aux0 = 0; SEGENV.aux1 &= 0xFF00; SEGENV.step = now + 800;
  }
  uint8_t held = (uint8_t)(SEGENV.aux1 & 0x3F);

  if ((int32_t)(now - SEGENV.step) >= 0) {                   // phase transitions
    switch (SEGENV.aux0) {
      case 0: {                                              // idle -> surge a letter
        uint8_t L = hw_random8() % CHARGE_NUM_LETTERS;
        if (acc && held != 0x3F) {                           // pick an unheld letter
          uint8_t tries = 0;
          while ((held >> L) & 1) { L = hw_random8() % CHARGE_NUM_LETTERS; if (++tries > 15) break; }
          while ((held >> L) & 1) L = (uint8_t)((L + 1) % CHARGE_NUM_LETTERS);
        }
        SEGENV.aux0 = (uint16_t)(1 + L);
        SEGENV.step = now + 260 + hw_random8();              // surge ~260..515 ms
        break; }
      case 1: case 2: case 3: case 4: case 5: case 6:        // surge over
        if (acc) {
          held |= (uint8_t)(1u << (SEGENV.aux0 - 1));
          SEGENV.aux1 = (uint16_t)((SEGENV.aux1 & 0xFF00) | held);
          if (held == 0x3F) { SEGENV.aux0 = 7; SEGENV.step = now + HOLDALL_MS; break; }
        }
        SEGENV.aux0 = 0;
        SEGENV.step = now + 600 + (uint32_t)(255 - SEGMENT.custom1) * 20
                          + (uint32_t)hw_random8() * 8;      // idle 0.6..7.7 s
        break;
      case 7:                                                // fully charged
        if (SEGMENT.check2 && usePal) { SEGENV.aux0 = 8; SEGENV.step = now + WAVE_MS; }
        else                          { SEGENV.aux0 = 10; SEGENV.step = now + FLICK_MS; }
        break;
      case 8: SEGENV.aux0 = 9;  SEGENV.step = now + WHITE_MS; break;
      case 9: SEGENV.aux0 = 10; SEGENV.step = now + FLICK_MS; break;
      default:                                               // flicker-out done: new cycle
        SEGENV.aux0 = 0;
        SEGENV.aux1 = (uint16_t)((uint16_t)hw_random8() << 8);  // re-roll cycle color
        SEGENV.step = now + 900 + (uint32_t)(255 - SEGMENT.custom1) * 10;
        break;
    }
    held = (uint8_t)(SEGENV.aux1 & 0x3F);
  }
  uint8_t phase = (uint8_t)SEGENV.aux0;

  // cycle + per-letter colors
  uint32_t seed = charge_hash(((uint32_t)(SEGENV.aux1 >> 8) << 3) ^ 0x5EED0000u);
  uint32_t cyccol = usePal ? SEGMENT.color_from_palette((uint8_t)seed, false, true, 255)
                           : CHARGE_CYAN;
  uint32_t lcol[CHARGE_NUM_LETTERS];
  if (usePal && SEGMENT.check3)
    charge_letter_colors(seed, true, lcol);                // palette primaries, neighbors distinct
  else
    for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) lcol[L] = cyccol;

  if (phase >= 7) {
    // ---- all-on finale phases (per-pixel; packets rest, the charge is full) ----
    uint32_t rem = (int32_t)(SEGENV.step - now) > 0 ? SEGENV.step - now : 0;
    for (uint16_t i = 0; i < CHARGE_NUM_PIXELS; i++) {
      uint8_t L = pgm_read_byte(&CHARGE_LETTER[i]);
      uint32_t c;
      if (phase == 7) {                                      // hold-all, fully charged
        c = color_fade(lcol[L], 235, true);
      } else if (phase == 8) {                               // palette pulse washes L->R
        uint32_t prog = WAVE_MS - rem;
        int32_t front = -60 + (int32_t)((prog * 375) / WAVE_MS);
        int32_t d = front - (int32_t)pgm_read_byte(&CHARGE_XNORM[i]);
        const int32_t BAND = 56;
        if (d < 0)          c = color_fade(lcol[L], 235, true);          // wave hasn't hit
        else if (d < BAND)  c = SEGMENT.color_from_palette((uint8_t)((d * 255) / BAND), false, true, 255);
        else                c = color_fade(WHITE, 235, true);            // washed to white
      } else if (phase == 9) {                               // white-hot hold
        c = color_fade(WHITE, 235, true);
      } else {                                               // flicker out together
        uint32_t base = (SEGMENT.check2 && usePal) ? WHITE : lcol[L];
        uint8_t g = (uint8_t)((rem * 255) / FLICK_MS);       // 255 -> 0 as it dies
        uint8_t bri = qsub8(g, (uint8_t)(hw_random8() % (uint8_t)(2 + (255 - g) / 2)));
        // per-letter electrical dropouts, worsening as the charge drains
        if ((charge_hash(((now >> 5) * 0x9E3779B1u) ^ L) & 0xFF) < (uint8_t)(255 - g))
          bri = (uint8_t)(bri >> 3);
        c = color_fade(base, bri, true);
      }
      charge_setpx(i, c);
    }
    return;
  }

  // ---- idle / surging phases ----
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {         // glow: held letters stay ON
    uint8_t bri = ((held >> L) & 1) ? 170 : 30;
    uint32_t c = color_fade(lcol[L], bri, true);
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    for (uint16_t k = 0; k < n; k++) charge_setpx(st + k, c);
  }

  uint8_t np = 1 + (SEGMENT.intensity >> 5);                 // 1..8 packets
  uint32_t v = 60 + (uint32_t)SEGMENT.speed * 3;             // 60..825 px/s
  const uint16_t TAIL = 7;
  for (uint8_t p = 0; p < np; p++) {
    uint32_t head = (uint32_t)(((uint64_t)now * v / 1000 +
                    (uint32_t)p * CHARGE_NUM_PIXELS / np) % CHARGE_NUM_PIXELS);
    for (uint16_t k = 0; k <= TAIL; k++) {
      int32_t i = (int32_t)head - (int32_t)k;
      if (i < 0) break;                                      // chain isn't a loop
      uint32_t base = lcol[pgm_read_byte(&CHARGE_LETTER[(uint16_t)i])];
      uint32_t c = (k == 0) ? WHITE
                 : color_fade(base, (uint8_t)(255 - (k * 255) / (TAIL + 1)), true);
      charge_setpx((uint16_t)i, c);
    }
  }

  if (SEGMENT.intensity >= 64)                               // stray sparks scale w/ Energy
    for (uint8_t s = 0; s < (uint8_t)(1 + (SEGMENT.intensity >> 6)); s++) {
      uint16_t i = (uint16_t)(((((uint32_t)hw_random8() << 8) | hw_random8())) % CHARGE_NUM_PIXELS);
      charge_setpx(i, WHITE);
    }

  if (phase >= 1 && phase <= 6) {                            // arc-flash overlay
    uint8_t bri = (hw_random8() < 140) ? (uint8_t)(255 - (hw_random8() % 120)) : 255;
    uint8_t L = (uint8_t)(phase - 1);
    uint32_t arc = usePal ? color_blend(lcol[L], WHITE, 185) : RGBW32(200, 255, 255, 0);
    uint32_t c = color_fade(arc, bri, true);
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    for (uint16_t k = 0; k < n; k++) charge_setpx(st + k, c);
  }
}

// =====================================================================
// CHARGE Comet — 1..4 white-hot heads with sparking tails trace the
// entire neon path; optional rainbow tails (palette-cycled).
// =====================================================================
static const char _data_CHARGE_COMET[] PROGMEM =
  "CHARGE Comet@Speed,Tail,Comets,,,Rainbow;!,!,!;!;2;sx=140,ix=96,c1=32,o1=0,pal=0";

static void mode_charge_comet() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  SEGMENT.fill(BLACK);
  uint32_t now = strip.now;
  uint32_t v = 100 + (uint32_t)SEGMENT.speed * 4;            // 100..1120 px/s
  uint16_t tail = 8 + (SEGMENT.intensity >> 2);              // 8..71 px
  uint8_t nc = 1 + (SEGMENT.custom1 >> 6);                   // 1..4 comets
  uint32_t total = (uint32_t)CHARGE_NUM_PIXELS + tail;
  for (uint8_t cix = 0; cix < nc; cix++) {
    uint32_t head = (uint32_t)(((uint64_t)now * v / 1000 + (uint32_t)cix * total / nc) % total);
    // per-comet color: Default palette = classic cyan; else comets spread
    // across the palette and drift through it slowly
    uint32_t cometc = (SEGMENT.palette == 0) ? CHARGE_CYAN
      : SEGMENT.color_from_palette((uint8_t)(((uint16_t)cix * 255) / nc + (now >> 9)), false, true, 255);
    for (uint16_t k = 0; k < tail; k++) {
      int32_t i = (int32_t)head - (int32_t)k;
      if (i < 0 || i >= CHARGE_NUM_PIXELS) continue;
      if (k < 2) { charge_setpx((uint16_t)i, RGBW32(255, 255, 255, 0)); continue; }
      uint8_t bri = (uint8_t)(((uint32_t)(tail - k) * 255) / tail);
      bri = qsub8(bri, hw_random8() & 63);                   // sparking decay
      uint32_t base = SEGMENT.check1                         // Rainbow: palette cycles along the tail
        ? SEGMENT.color_from_palette((uint8_t)((k * 255) / tail + (now >> 4)), false, true, 255)
        : cometc;
      charge_setpx((uint16_t)i, color_fade(base, bri, true));
    }
  }
}

// =====================================================================
// CHARGE Marquee — retro theater-bulb chase along the tubes; Warmth
// blends the bulbs from cool white to warm amber.
// =====================================================================
static const char _data_CHARGE_MARQUEE[] PROGMEM =
  "CHARGE Marquee@Speed,Spacing,Warmth;;;2;sx=128,ix=64,c1=200";

static void mode_charge_marquee() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint8_t sp = 2 + (SEGMENT.intensity >> 6);                 // bulb spacing 2..5
  uint32_t stepMs = 40 + (uint32_t)(255 - SEGMENT.speed);    // 40..295 ms per step
  uint8_t phase = (uint8_t)((strip.now / stepMs) % sp);
  uint32_t bulb  = color_blend(RGBW32(200, 220, 255, 0), RGBW32(255, 170, 50, 0), SEGMENT.custom1);
  uint32_t ember = color_fade(bulb, 18, true);
  for (uint16_t i = 0; i < CHARGE_NUM_PIXELS; i++)
    charge_setpx(i, ((i + sp - phase) % sp) == 0 ? bulb : ember);
}

// =====================================================================
// CHARGE Neon Morph — letters drift cyan <-> TEDx red on staggered
// phases; Buzz adds failing-neon dropouts; Shimmer adds per-pixel life.
// =====================================================================
static const char _data_CHARGE_MORPH[] PROGMEM =
  "CHARGE Neon Morph@Speed,Buzz,Shimmer;!,!,!;!;2;sx=128,ix=96,c1=60,pal=0";

static void mode_charge_morph() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint32_t now = strip.now;
  uint32_t P = 3000 + (uint32_t)(255 - SEGMENT.speed) * 40;  // 3..13.2 s morph period
  uint8_t shim = SEGMENT.custom1;
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint8_t m = charge_tri8(now + (uint32_t)L * (P / 9), P); // staggered letters
    // Default palette = the classic cyan <-> TEDx-red morph; any other palette:
    // each letter drifts through the palette on its own staggered phase
    uint32_t c = (SEGMENT.palette == 0)
      ? color_blend(CHARGE_CYAN, CHARGE_TEDX_RED, m)
      : SEGMENT.color_from_palette(m, false, true, 255);
    uint32_t win = (now >> 9) ^ ((uint32_t)L * 0x9E3779B1u);
    bool buzzing = (charge_hash(win) & 0xFF) < (SEGMENT.intensity >> 2);
    if (buzzing && hw_random8() < 160)
      c = color_fade(c, (uint8_t)(255 - (hw_random8() % 190)), true);
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    for (uint16_t k = 0; k < n; k++) {
      uint32_t px = c;
      if (shim) {                                            // frame-coherent sparkle
        uint8_t s = (uint8_t)(charge_hash(((uint32_t)(st + k) << 10) ^ (now >> 7)) & 0xFF);
        if (s < shim) px = color_fade(px, (uint8_t)(140 + (s % 116)), true);
      }
      charge_setpx(st + k, px);
    }
  }
}

// =====================================================================
// CHARGE Pac-Man — a real game simulation in the tubes (per-effect state
// via SEGENV.allocateData, like stock WLED effects):
// - pellets per letter, POWER pellets (every 5th, pulsing): eating one
//   REVERSES pac into frightened-ghost-hunting mode (real rules)
// - "Pacmen" slider: 1..6 pacs roam the sign; when a pac clears its
//   letter it hops to another letter that still has pellets; when the
//   whole board is clear, a new level starts (all pellets respawn)
// - one ghost per letter: chases its visitor, flees (blue, blinking)
//   when hunted, gets eaten and respawns; catches pac -> pac respawns
// - "Portals" (the letters' real geometry): tube spots that are far
//   apart along the wire but physically adjacent become escape portals
//   (violet markers) — a cornered pac jumps through to lose the ghost
// =====================================================================
static const char _data_CHARGE_PACMAN[] PROGMEM =
  "CHARGE Pac-Man@Speed,Pellets,Pacmen,,,Power pellets,Portals;;;2;sx=128,ix=128,c1=64,o1=1,o2=1";

typedef struct {
  uint8_t  letter;
  int8_t   dir;
  uint8_t  mode;                     // 0 normal, 1 frightened (hunting ghosts)
  uint8_t  _pad;
  uint16_t posfp;                    // 8.8 fixed tube position
  uint32_t modeUntil;
  uint32_t portalCd;                 // portal cooldown deadline
} ChargePac;
typedef struct {
  uint8_t  alive;
  int8_t   dir;
  uint16_t posfp;
  uint32_t respawnAt;
} ChargeGhost;
typedef struct {
  uint8_t  inited, npac, sp, level;
  uint32_t eaten[CHARGE_NUM_LETTERS];             // pellet-eaten bitmask (idx = k/sp)
  ChargePac   pac[CHARGE_NUM_LETTERS];
  ChargeGhost ghost[CHARGE_NUM_LETTERS];
  uint8_t  portal[CHARGE_NUM_LETTERS][4][2];      // close-in-space, far-on-wire pairs
  uint32_t lastMs;
} ChargePacData;

static void mode_charge_pacman() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  if (!SEGMENT.allocateData(sizeof(ChargePacData))) { SEGMENT.fill(BLACK); return; }
  ChargePacData *d = (ChargePacData*)SEGENV.data;
  uint32_t now = strip.now;
  uint8_t sp = (uint8_t)(3 + ((uint8_t)(255 - SEGMENT.intensity) >> 6));  // pellet spacing 3..6
  uint8_t npac = (uint8_t)(1 + ((uint16_t)SEGMENT.custom1 * 5) / 255);    // 1..6 pacmen
  uint32_t vp = 8 + (SEGMENT.speed >> 3);                                 // pac px/s 8..39

  if (!d->inited || d->sp != sp || d->npac != npac) {        // (re)start the board
    memset(d, 0, sizeof(ChargePacData));
    d->inited = 1; d->sp = sp; d->npac = npac; d->level = 1;
    for (uint8_t p = 0; p < npac; p++) {
      d->pac[p].letter = p; d->pac[p].dir = 1; d->pac[p].posfp = 0;
    }
    for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
      uint16_t n = charge_lcount(L);
      d->ghost[L].alive = 1; d->ghost[L].dir = 1;
      d->ghost[L].posfp = (uint16_t)((n / 2) << 8);
      // portals: pairs far apart along the tube but physically adjacent
      uint8_t np = 0;
      uint16_t st = charge_lstart(L);
      for (uint8_t a = 2; a + 14 < n && np < 4; a += 2) {
        for (uint16_t b = a + 14; b < n; b += 2) {
          uint8_t gd = charge_dist8(
            (int16_t)pgm_read_byte(&CHARGE_COL[st + a]) - (int16_t)pgm_read_byte(&CHARGE_COL[st + b]),
            (int16_t)pgm_read_byte(&CHARGE_ROW[st + a]) - (int16_t)pgm_read_byte(&CHARGE_ROW[st + b]));
          if (gd > 2) continue;
          bool clash = false;                                // keep portals spread out
          for (uint8_t j = 0; j < np; j++) {
            int16_t s1 = (int16_t)a - d->portal[L][j][0], s2 = (int16_t)b - d->portal[L][j][1];
            if ((s1 < 0 ? -s1 : s1) < 8 || (s2 < 0 ? -s2 : s2) < 8) { clash = true; break; }
          }
          if (clash) continue;
          d->portal[L][np][0] = (uint8_t)a; d->portal[L][np][1] = (uint8_t)b; np++;
          break;
        }
      }
      for (uint8_t j = np; j < 4; j++) { d->portal[L][j][0] = 255; d->portal[L][j][1] = 255; }
    }
    d->lastMs = now;
  }
  uint32_t dt = now - d->lastMs; if (dt > 80) dt = 80;
  d->lastMs = now;

  uint8_t flashN = 0; uint8_t flashL[8]; uint8_t flashP[8];  // this-frame jump flashes

  // ---- pacs ----
  for (uint8_t p = 0; p < npac; p++) {
    ChargePac *pc = &d->pac[p];
    uint16_t n = charge_lcount(pc->letter);
    uint16_t maxfp = (uint16_t)((n - 1) << 8);
    uint32_t v = (pc->mode == 1) ? vp * 5 / 4 : vp;
    int32_t fp = (int32_t)pc->posfp + pc->dir * (int32_t)(v * dt * 256 / 1000);
    if (fp <= 0)      { fp = 0;     pc->dir = 1;  }
    if (fp >= maxfp)  { fp = maxfp; pc->dir = -1; }
    pc->posfp = (uint16_t)fp;
    if (pc->mode == 1 && (int32_t)(now - pc->modeUntil) >= 0) pc->mode = 0;

    uint8_t k = (uint8_t)(pc->posfp >> 8);
    for (int8_t dk = -1; dk <= 1; dk++) {                    // chomp radius 1
      int16_t kk = (int16_t)k + dk;
      if (kk <= 0 || kk >= (int16_t)n || (kk % sp) != 0) continue;
      uint8_t idx = (uint8_t)(kk / sp);
      if (d->eaten[pc->letter] & (1u << idx)) continue;
      d->eaten[pc->letter] |= (1u << idx);
      if (SEGMENT.check1 && (idx % 5) == 0) {                // POWER pellet: hunt!
        pc->mode = 1; pc->modeUntil = now + 4000; pc->dir = (int8_t)-pc->dir;
      }
    }

    ChargeGhost *g = &d->ghost[pc->letter];
    if (g->alive) {
      int16_t dist = (int16_t)(g->posfp >> 8) - (int16_t)k; if (dist < 0) dist = (int16_t)-dist;
      if (pc->mode == 1 && dist <= 2) {                      // ghost eaten!
        g->alive = 0; g->respawnAt = now + 3500;
      } else if (pc->mode == 0 && dist <= 1) {               // pac caught: respawn far side
        pc->posfp = (k > n / 2) ? 0 : maxfp;
        pc->dir = (pc->posfp == 0) ? 1 : -1;
      } else if (SEGMENT.check2 && pc->mode == 0 && dist <= 6 &&
                 (int32_t)(now - pc->portalCd) >= 0) {       // cornered: take a portal
        for (uint8_t j = 0; j < 4; j++) {
          uint8_t a = d->portal[pc->letter][j][0], b = d->portal[pc->letter][j][1];
          if (a == 255) break;
          int16_t da = (int16_t)k - a; if (da < 0) da = (int16_t)-da;
          int16_t db = (int16_t)k - b; if (db < 0) db = (int16_t)-db;
          if (da <= 1 || db <= 1) {
            pc->posfp = (uint16_t)(((da <= 1) ? b : a) << 8);
            pc->portalCd = now + 1200;
            if (flashN < 8) { flashL[flashN] = pc->letter; flashP[flashN] = (da <= 1) ? b : a; flashN++; }
            break;
          }
        }
      }
    }

    uint8_t maxIdx = (uint8_t)((n - 1) / sp);                // letter cleared -> hop on
    uint32_t full = (maxIdx >= 1) ? ((2u << maxIdx) - 2u) : 0u;
    if (full && (d->eaten[pc->letter] & full) == full) {
      int8_t next = -1;
      for (uint8_t pass = 0; pass < 2 && next < 0; pass++) { // prefer letters w/o a pac
        uint8_t L0 = (uint8_t)(charge_hash(now + p * 131u) % CHARGE_NUM_LETTERS);
        for (uint8_t o = 0; o < CHARGE_NUM_LETTERS; o++) {
          uint8_t cand = (uint8_t)((L0 + o) % CHARGE_NUM_LETTERS);
          uint16_t cn = charge_lcount(cand);
          uint8_t cmax = (uint8_t)((cn - 1) / sp);
          uint32_t cfull = (cmax >= 1) ? ((2u << cmax) - 2u) : 0u;
          if (!cfull || (d->eaten[cand] & cfull) == cfull) continue;
          bool occupied = false;
          for (uint8_t q = 0; q < npac; q++) if (q != p && d->pac[q].letter == cand) occupied = true;
          if (pass == 0 && occupied) continue;
          next = (int8_t)cand; break;
        }
      }
      if (next >= 0) {
        pc->letter = (uint8_t)next; pc->posfp = 0; pc->dir = 1;
        if (flashN < 8) { flashL[flashN] = pc->letter; flashP[flashN] = 0; flashN++; }
      } else {                                               // board clear: NEW LEVEL
        d->level++;
        for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) d->eaten[L] = 0;
      }
    }
  }

  // ---- ghosts ----
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    ChargeGhost *g = &d->ghost[L];
    uint16_t n = charge_lcount(L);
    if (!g->alive) {
      if ((int32_t)(now - g->respawnAt) >= 0) { g->alive = 1; g->posfp = (uint16_t)((n / 2) << 8); }
      else continue;
    }
    int8_t target = -1;
    for (uint8_t p = 0; p < npac; p++) if (d->pac[p].letter == L) { target = (int8_t)p; break; }
    uint32_t vg = vp / 2;                                    // wander
    if (target >= 0) {
      bool fright = d->pac[(uint8_t)target].mode == 1;
      vg = fright ? vp * 3 / 5 : vp * 4 / 5;
      int16_t toward = ((d->pac[(uint8_t)target].posfp >> 8) > (g->posfp >> 8)) ? 1 : -1;
      g->dir = fright ? (int8_t)-toward : (int8_t)toward;
    }
    uint16_t maxfp = (uint16_t)((n - 1) << 8);
    int32_t fp = (int32_t)g->posfp + g->dir * (int32_t)(vg * dt * 256 / 1000);
    if (fp <= 0)     { fp = 0;     g->dir = 1;  }
    if (fp >= maxfp) { fp = maxfp; g->dir = -1; }
    g->posfp = (uint16_t)fp;
  }

  // ---- render ----
  SEGMENT.fill(BLACK);
  static const uint32_t GHOSTC[4] = { RGBW32(255,0,0,0),    RGBW32(255,105,180,0),
                                      RGBW32(0,255,255,0),  RGBW32(255,140,0,0) };
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    if (SEGMENT.check2)                                      // portal markers
      for (uint8_t j = 0; j < 4; j++) {
        uint8_t a = d->portal[L][j][0], b = d->portal[L][j][1];
        if (a == 255) break;
        charge_setpx(st + a, color_fade(RGBW32(150, 60, 255, 0), 60, true));
        charge_setpx(st + b, color_fade(RGBW32(150, 60, 255, 0), 60, true));
      }
    for (uint16_t k = sp; k < n; k += sp) {                  // uneaten pellets
      uint8_t idx = (uint8_t)(k / sp);
      if (d->eaten[L] & (1u << idx)) continue;
      if (SEGMENT.check1 && (idx % 5) == 0)                  // power pellet: pulsing
        charge_setpx(st + k, color_fade(RGBW32(255, 240, 180, 0),
                     (uint8_t)(120 + (charge_tri8(now, 700) >> 1)), true));
      else
        charge_setpx(st + k, color_fade(RGBW32(255, 220, 150, 0), 70, true));
    }
    ChargeGhost *g = &d->ghost[L];
    if (g->alive) {
      int8_t vis = -1;
      for (uint8_t p = 0; p < npac; p++) if (d->pac[p].letter == L) { vis = (int8_t)p; break; }
      bool fright = vis >= 0 && d->pac[(uint8_t)vis].mode == 1;
      bool blink = fright && (d->pac[(uint8_t)vis].modeUntil - now < 1200) && ((now / 160) & 1);
      uint32_t gc = fright ? (blink ? WHITE : RGBW32(40, 40, 255, 0)) : GHOSTC[L & 3];
      uint8_t gk = (uint8_t)(g->posfp >> 8);
      charge_setpx(st + gk, gc);
      int16_t g2 = (int16_t)gk + g->dir;
      if (g2 >= 0 && g2 < (int16_t)n) charge_setpx((uint16_t)(st + g2), color_fade(gc, 120, true));
    }
  }
  for (uint8_t p = 0; p < npac; p++) {                       // pacs on top
    ChargePac *pc = &d->pac[p];
    uint16_t st = charge_lstart(pc->letter), n = charge_lcount(pc->letter);
    uint8_t k = (uint8_t)(pc->posfp >> 8);
    uint32_t pcc = RGBW32(255, 210, 0, 0);
    if (pc->mode == 1)                                       // hunting: white-hot pulse
      pcc = color_blend(pcc, WHITE, charge_tri8(now, 300));
    charge_setpx(st + k, pcc);
    int16_t k2 = (int16_t)k + pc->dir;
    if (((now / 130) & 1) && k2 >= 0 && k2 < (int16_t)n)     // chomp
      charge_setpx((uint16_t)(st + k2), pcc);
  }
  for (uint8_t f = 0; f < flashN; f++) {                     // portal / hop flashes
    uint16_t st = charge_lstart(flashL[f]), n = charge_lcount(flashL[f]);
    for (int16_t o = -1; o <= 1; o++) {
      int16_t k = (int16_t)flashP[f] + o;
      if (k >= 0 && k < (int16_t)n) charge_setpx((uint16_t)(st + k), WHITE);
    }
  }
}

// =====================================================================
// CHARGE Lava — lava lamp per letter: wax blobs rise from the base and
// sink back (gravity dwell), heater glow below. Trippy = acid wax.
// =====================================================================
static const char _data_CHARGE_LAVA[] PROGMEM =
  "CHARGE Lava@Speed,Blobs,Size,,,Trippy;!,!,!;!;2;sx=64,ix=128,c1=128,o1=0,pal=251";

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
      uint16_t sg = (uint16_t)((30 + ((h >> 16) & 31)) * (128 + (uint16_t)SEGMENT.custom1) / 256);
      sig[b] = (uint8_t)(sg < 12 ? 12 : (sg > 90 ? 90 : sg)); // Size slider 0.5..1.5x
      bc[b]  = SEGMENT.check1
        ? SEGMENT.color_from_palette((uint8_t)((h >> 24) + (now >> 6)), false, true, 255)  // acid wax
        : color_blend(RGBW32(255, 110, 8, 0), RGBW32(255, 0, 120, 0), (uint8_t)(h >> 24));
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
// CHARGE Ants — the tubes are ant tunnels: colonies forage out from a
// breathing nest at the tube mouth and haul green food glints home.
// =====================================================================
static const char _data_CHARGE_ANTS[] PROGMEM =
  "CHARGE Ants@Speed,Ants;;;2;sx=96,ix=128";

static void mode_charge_ants() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint32_t now = strip.now;
  uint8_t na = (uint8_t)(2 + SEGMENT.intensity / 52);        // 2..6 ants per letter
  uint32_t vbase = 4 + (SEGMENT.speed >> 3);                 // 4..35 px/s
  uint32_t tunnel = color_fade(RGBW32(180, 120, 60, 0), 30, true);
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
// CHARGE Raider — side-scroller ship flies the whole neon path: rocket
// jet with flame noise, periodic boosts, bolts intercepting aliens,
// multicolor explosions. Rainbow jet = palette-cycled exhaust.
// =====================================================================
static const char _data_CHARGE_RAIDER[] PROGMEM =
  "CHARGE Raider@Speed,Enemies,Boost freq,,,Rainbow jet;;;2;sx=140,ix=128,c1=128,o1=0";

static void mode_charge_raider() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  SEGMENT.fill(BLACK);
  uint32_t now = strip.now;
  const int32_t N = CHARGE_NUM_PIXELS;
  uint32_t v = 40 + (uint32_t)SEGMENT.speed;                 // ship 40..295 px/s
  uint32_t travel = (uint32_t)((uint64_t)now * v / 1000);
  uint16_t ship = (uint16_t)(travel % (uint32_t)N);
  uint32_t lap = travel / (uint32_t)N;

  for (uint16_t i = 0; i < CHARGE_NUM_PIXELS; i++) {         // twinkling starfield
    uint32_t hs = charge_hash((uint32_t)i * 2654435761u);
    if ((hs & 0xFF) < 20)
      charge_setpx(i, color_fade(RGBW32(150, 170, 220, 0),
        (uint8_t)(24 + (charge_tri8(now + (hs >> 8), 1400 + (hs % 1100)) >> 2)), true));
  }

  // boost: ~75% of windows get a 1.3s flare; window 3..10.1s (Boost freq)
  uint32_t bwin = 3000 + (uint32_t)(255 - SEGMENT.custom1) * 28;
  uint32_t bph = now % bwin;
  bool boost = ((charge_hash(now / bwin) & 3) != 0) && bph < 1300;

  uint8_t jetlen = boost ? 18 : 9;
  for (uint8_t k = 1; k <= jetlen; k++) {
    uint8_t frac = (uint8_t)(((uint16_t)k * 255) / jetlen);
    uint32_t c;
    if (SEGMENT.check1)      c = charge_palette(4, (uint8_t)(frac + (now >> 3)));  // rainbow jet
    else if (boost)          c = color_blend(RGBW32(170, 220, 255, 0), RGBW32(30, 60, 255, 0), frac);
    else                     c = color_blend(RGBW32(255, 220, 60, 0), RGBW32(255, 30, 0, 0), frac);
    uint8_t bri = (uint8_t)(((uint16_t)(jetlen - k + 1) * 255) / (jetlen + 1));
    bri = qsub8(bri, hw_random8() & 60);                     // flame flicker
    charge_setpx_mod((int32_t)ship - k, color_fade(c, bri, true));
  }
  charge_setpx_mod(ship, boost ? RGBW32(255, 255, 255, 0) : CHARGE_CYAN);
  charge_setpx_mod((int32_t)ship + 1, RGBW32(255, 255, 255, 0));

  uint8_t ne = (uint8_t)(2 + (SEGMENT.intensity >> 5));      // 2..9 per lap
  static const uint32_t ALIENC[3] = { RGBW32(255,0,90,0), RGBW32(140,255,0,0),
                                      RGBW32(255,60,0,0) };
  for (uint8_t j = 0; j < ne; j++) {
    uint32_t hj = charge_hash(lap * 31 + j + 0xE11E0000u);
    int32_t E = (int32_t)(((uint32_t)j * (uint32_t)N) / ne + (hj % 24)) % N;
    int32_t d = E - (int32_t)ship; if (d < 0) d += N;        // distance ahead
    if (d > 40) {                                            // alive: pulsing alien
      uint8_t bri = (uint8_t)(140 + (charge_tri8(now + j * 997u, 700) >> 2));
      uint32_t ac = color_fade(ALIENC[hj % 3], bri, true);
      charge_setpx_mod(E, ac);
      charge_setpx_mod(E + 1, color_fade(ac, 120, true));
    } else if (d > 24 && d <= 40) {                          // hit: multicolor burst
      uint8_t age = (uint8_t)(((uint32_t)(d - 24) * 255) / 16); // 255 at impact -> 0
      uint8_t r = (uint8_t)(1 + (40 - d) / 3);               // expanding 1..6 px
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

// =====================================================================
// CHARGE Gravity — palette-colored balls bounce inside each letter with
// real decay physics (parabolic arcs, restitution 0.62), using the baked
// height table as the vertical axis and xnorm as the ball's lane.
// =====================================================================
static const char _data_CHARGE_GRAVITY[] PROGMEM =
  "CHARGE Gravity@Gravity,Balls,,,,Trails;!,!,!;!;2;sx=128,ix=172,o1=1,pal=255";

static void mode_charge_gravity() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  SEGMENT.fill(BLACK);
  uint32_t now = strip.now;
  uint8_t nballs = (uint8_t)(1 + SEGMENT.intensity / 86);    // 1..3 per letter
  uint32_t T0 = 1400 - (uint32_t)SEGMENT.speed * 4;          // first-bounce period 380..1400ms
  // restitution 0.62 in 8.8 fixed: r^k and r^(2k) tables for 7 bounces
  static const uint16_t RK[7]  = { 256, 159, 98, 61, 38, 24, 15 };
  static const uint16_t RK2[7] = { 256, 98, 38, 15, 6, 2, 1 };
  uint32_t Ctot = 0;
  for (uint8_t k = 0; k < 7; k++) Ctot += (T0 * RK[k]) >> 8;
  Ctot += 500;                                               // rest at the floor

  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    uint8_t xlo, xhi; charge_letter_xrange(L, &xlo, &xhi);
    uint8_t xspan = (uint8_t)(xhi - xlo);
    for (uint16_t k = 0; k < n; k++) {                       // floor glow grounds the scene
      uint16_t i = st + k;
      if (pgm_read_byte(&CHARGE_HEIGHT[i]) < 8)
        charge_setpx(i, color_fade(SEGMENT.color_from_palette(40, false, true, 255), 46, true));
    }
    for (uint8_t b = 0; b < nballs; b++) {
      uint32_t h = charge_hash(((uint32_t)L << 8) | b | 0x0B0B0000u);
      uint32_t tc = (now + (h & 0x3FFF)) % Ctot;
      // find which bounce we're in
      uint8_t bk = 7; uint32_t rem = tc;
      for (uint8_t k = 0; k < 7; k++) {
        uint32_t Tk = (T0 * RK[k]) >> 8;
        if (rem < Tk) { bk = k; break; }
        rem -= Tk;
      }
      int16_t bh = 0; bool falling = false;
      if (bk < 7) {                                          // parabola: peak = 255*r^2k
        uint32_t Tk = (T0 * RK[bk]) >> 8; if (Tk < 2) Tk = 2;
        uint8_t u = (uint8_t)((rem * 255) / Tk);
        uint16_t peak = (uint16_t)((255 * RK2[bk]) >> 8);
        bh = (int16_t)(((uint32_t)peak * 4 * u * (255 - u)) / 65025);
        falling = u > 128;
      }
      uint8_t xb = (uint8_t)(xlo + ((h >> 16) & 0xFF) * xspan / 255);
      uint8_t xw = xspan / 5; if (xw < 8) xw = 8;            // lane width
      uint32_t ballc = SEGMENT.color_from_palette((uint8_t)(h >> 24), false, true, 255);
      for (uint16_t k = 0; k < n; k++) {
        uint16_t i = st + k;
        uint8_t xd = pgm_read_byte(&CHARGE_XNORM[i]);
        uint8_t dx = (xd > xb) ? (uint8_t)(xd - xb) : (uint8_t)(xb - xd);
        if (dx >= xw) continue;
        int16_t hp = pgm_read_byte(&CHARGE_HEIGHT[i]);
        int16_t dh = hp - bh; if (dh < 0) dh = -dh;
        if (dh < 20) {                                       // the ball: solid core, soft rim
          uint8_t w = (dh < 8) ? 255 : (uint8_t)(((20 - dh) * 255) / 12);
          uint8_t lanew = (uint8_t)(90 + ((uint16_t)(xw - dx) * 165) / xw);
          w = (uint8_t)(((uint16_t)w * lanew) / 255);
          charge_setpx(i, color_fade(ballc, w, true));
        } else if (SEGMENT.check1) {                         // motion trail
          int16_t tr = hp - bh - (falling ? 26 : -26); if (tr < 0) tr = -tr;
          if (tr < 12) charge_setpx(i, color_fade(ballc, 80, true));
        }
        if (bh < 6 && hp < 8 && dx < xw)                     // floor impact flash
          charge_setpx(i, color_fade(RGBW32(255,255,255,0), (uint8_t)(200 - bh * 30), true));
      }
    }
  }
}

// =====================================================================
// CHARGE Fireworks — 1D fireworks in every letter (PS-style, ported to
// tube space): rockets climb the tube, burst into palette-colored sparks
// that spread ballistically and decay; optional crackle glints.
// =====================================================================
static const char _data_CHARGE_FIREWORKS[] PROGMEM =
  "CHARGE Fireworks@Spark speed,Sparks,,Rate,,Crackle;!,!,!;!;2;sx=140,ix=160,c2=120,o1=1,pal=6";

static void mode_charge_fireworks() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  SEGMENT.fill(BLACK);
  uint32_t now = strip.now;
  uint32_t Wms = 3000 - (uint32_t)SEGMENT.custom2 * 10;      // launch window 0.45..3s
  uint8_t ns = (uint8_t)(8 + (SEGMENT.intensity >> 3));      // 8..39 sparks

  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    uint32_t tphase = now + ((charge_hash(L ^ 0xF13E0000u) & 0x7FF));
    uint32_t win = tphase / Wms;
    uint32_t ph = tphase % Wms;
    uint32_t hj = charge_hash(win * 131 + L * 7 + 0xF13E0000u);
    if ((hj & 0xFF) > 215) continue;                         // ~84% of windows launch
    uint16_t B = (uint16_t)(((uint32_t)n * (102 + ((hj >> 8) & 0x7F))) / 256);  // burst at 40..90% of tube
    uint32_t t_up = (Wms * 2) / 5;
    if (ph < t_up) {                                         // rocket climb
      uint16_t pos = (uint16_t)(((uint32_t)B * ph) / t_up);
      charge_setpx(st + pos, RGBW32(255, 255, 255, 0));
      if (pos > 0) charge_setpx(st + pos - 1,
        color_fade(RGBW32(255, 200, 120, 0), (uint8_t)(120 + (hw_random8() & 63)), true));
      if (pos > 1) charge_setpx(st + pos - 2,
        color_fade(RGBW32(255, 160, 80, 0), (uint8_t)(60 + (hw_random8() & 31)), true));
    } else {                                                 // burst
      uint32_t age = ph - t_up, dur = Wms - t_up;
      uint8_t a8 = (uint8_t)((age * 255) / dur);
      uint8_t basec = (uint8_t)(hj >> 16);
      uint32_t boomDur = dur / 6;                            // the BOOM: bright core flash
      if (age < boomDur) {
        uint16_t rad = (uint16_t)(2 + (age * 9) / (boomDur ? boomDur : 1));
        uint8_t bb = (uint8_t)(255 - (age * 200) / (boomDur ? boomDur : 1));
        uint32_t bc = color_blend(SEGMENT.color_from_palette(basec, false, true, 255), RGBW32(255, 255, 255, 0), bb);
        for (int32_t kk = (int32_t)B - rad; kk <= (int32_t)B + rad; kk++) {
          if (kk < 0 || kk >= (int32_t)n) continue;
          int32_t dd = kk - (int32_t)B; if (dd < 0) dd = -dd;
          charge_setpx(st + (uint16_t)kk,
            color_fade(bc, (uint8_t)(255 - ((uint32_t)dd * 160) / (rad ? rad : 1)), true));
        }
      }
      // ballistic: sparks decelerate to a stop by end of burst
      uint32_t age_eff = (age * (2 * dur - age)) / (2 * dur);
      for (uint8_t s = 0; s < ns; s++) {
        uint32_t hs = charge_hash(hj ^ ((uint32_t)s * 0x9E3779B1u));
        int8_t dir = (hs & 1) ? 1 : -1;
        uint32_t vs = (20 + ((hs >> 1) & 0x3F)) * (64 + SEGMENT.speed) / 128;  // px/s
        int32_t sposi = (int32_t)B + dir * (int32_t)((vs * age_eff) / 1000);
        if (sposi < 0 || sposi >= (int32_t)n) continue;
        uint8_t bri = (uint8_t)(255 - charge_smooth8(a8)); // hold bright, then die
        bri = qsub8(bri, (uint8_t)(hw_random8() & 40));
        uint32_t c = SEGMENT.color_from_palette((uint8_t)(basec + ((hs >> 8) & 0x3F) - 32), false, true, 255);
        if (SEGMENT.check1 && hw_random8() < 18) c = RGBW32(255, 255, 255, 0);  // crackle
        charge_setpx(st + (uint16_t)sposi, color_fade(c, bri, true));
        int32_t tail = sposi - dir;                          // 2px spark body
        if (tail >= 0 && tail < (int32_t)n)
          charge_setpx(st + (uint16_t)tail, color_fade(c, (uint8_t)((bri * 3) >> 2), true));
      }
    }
  }
}

// =====================================================================
// CHARGE Drip — glowing goo beads swell at the top of each letter, drop
// with gravity down through (x, height) space, and splash at the base.
// Defaults to slime; palette slider for other fluids.
// =====================================================================
static const char _data_CHARGE_DRIP[] PROGMEM =
  "CHARGE Drip@Fall speed,Drips,,,,Glisten;!,!,!;!;2;sx=110,ix=96,o1=1,pal=252";

static void mode_charge_drip() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  SEGMENT.fill(BLACK);
  uint32_t now = strip.now;
  uint8_t nd = (uint8_t)(1 + SEGMENT.intensity / 86);        // 1..3 drips per letter
  uint32_t Cd = 2600 - (uint32_t)SEGMENT.speed * 7;          // cycle 815..2600ms

  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    uint8_t xlo, xhi; charge_letter_xrange(L, &xlo, &xhi);
    for (uint8_t d = 0; d < nd; d++) {
      uint32_t h = charge_hash(((uint32_t)L << 8) | d | 0xD41B0000u);
      uint32_t tc = (now + (h & 0xFFF)) % Cd;
      // re-roll the drip's x lane every cycle
      uint32_t cyc = (now + (h & 0xFFF)) / Cd;
      uint32_t hc = charge_hash(h ^ (cyc * 0x85EBCA6Bu));
      uint8_t xd = (uint8_t)(xlo + (hc & 0xFF) * (uint8_t)(xhi - xlo) / 255);
      // source = highest pixel near lane xd
      int16_t hs0 = -1;
      for (uint16_t k = 0; k < n; k++) {
        uint8_t x = pgm_read_byte(&CHARGE_XNORM[st + k]);
        uint8_t dx = (x > xd) ? (uint8_t)(x - xd) : (uint8_t)(xd - x);
        if (dx < 10) {
          int16_t hp = pgm_read_byte(&CHARGE_HEIGHT[st + k]);
          if (hp > hs0) hs0 = hp;
        }
      }
      if (hs0 < 60) continue;                                // no tube up there — skip
      uint32_t swell = (Cd * 2) / 5, fall = (Cd * 2) / 5;    // swell 40%, fall 40%, splash 20%
      uint32_t gooc = SEGMENT.color_from_palette((uint8_t)(90 + ((hc >> 8) & 0x3F)), false, true, 255);
      if (tc < swell) {                                      // bead swells at the source
        uint8_t q = (uint8_t)((tc * 255) / swell);
        for (uint16_t k = 0; k < n; k++) {
          uint16_t i = st + k;
          uint8_t x = pgm_read_byte(&CHARGE_XNORM[i]);
          uint8_t dx = (x > xd) ? (uint8_t)(x - xd) : (uint8_t)(xd - x);
          int16_t dh = (int16_t)pgm_read_byte(&CHARGE_HEIGHT[i]) - hs0;
          if (dh < 0) dh = -dh;
          if (dx < 5 && dh < 10) charge_setpx(i, color_fade(gooc, (uint8_t)(40 + ((uint16_t)q * 200) / 255), true));
        }
      } else if (tc < swell + fall) {                        // gravity drop (accelerating)
        uint32_t q = ((tc - swell) * 255) / fall;
        int16_t hf = (int16_t)(hs0 - (int32_t)((hs0 + 20) * q * q / 65025));
        for (uint16_t k = 0; k < n; k++) {
          uint16_t i = st + k;
          uint8_t x = pgm_read_byte(&CHARGE_XNORM[i]);
          uint8_t dx = (x > xd) ? (uint8_t)(x - xd) : (uint8_t)(xd - x);
          if (dx >= 7) continue;
          int16_t hp = pgm_read_byte(&CHARGE_HEIGHT[i]);
          int16_t dh = hp - hf; if (dh < 0) dh = -dh;
          if (dh < 12) charge_setpx(i, color_fade(gooc, (uint8_t)(255 - (dh * 255) / 12), true));
          else if (hp > hf && hp <= hs0 && dx < 4)           // stretchy trail above
            charge_setpx(i, color_fade(gooc, 45, true));
        }
      } else {                                               // splash at the base
        uint32_t q = ((tc - swell - fall) * 255) / (Cd - swell - fall);
        uint8_t spread = (uint8_t)(6 + ((uint16_t)q * 16) / 255);
        uint8_t bri = (uint8_t)(255 - q);
        for (uint16_t k = 0; k < n; k++) {
          uint16_t i = st + k;
          if (pgm_read_byte(&CHARGE_HEIGHT[i]) > 22) continue;
          uint8_t x = pgm_read_byte(&CHARGE_XNORM[i]);
          uint8_t dx = (x > xd) ? (uint8_t)(x - xd) : (uint8_t)(xd - x);
          if (dx >= spread) continue;
          uint32_t c = gooc;
          if (SEGMENT.check1 && hw_random8() < 30) c = RGBW32(255, 255, 255, 0);  // glisten
          charge_setpx(i, color_fade(c, bri, true));
        }
      }
    }
  }
}

// =====================================================================
// CHARGE Pulse — energy pumps into each letter from both tube ends and
// meets in the middle, driven by audio (mic on the device; synthetic
// beat or browser microphone in the sim). Palette fill, peak flashes.
// =====================================================================
static const char _data_CHARGE_PULSE[] PROGMEM =
  "CHARGE Pulse@Gain,Floor,,,,From center;!,!,!;!;2;sx=140,ix=40,o1=0,pal=255";

static void mode_charge_pulse() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  SEGMENT.fill(BLACK);
  uint32_t now = strip.now;
  uint32_t lvl32 = (uint32_t)charge_audio() * (64 + SEGMENT.speed) / 128;  // gain
  uint8_t lvl = (uint8_t)(lvl32 > 255 ? 255 : lvl32);
  if (lvl < SEGMENT.intensity) lvl = SEGMENT.intensity;      // floor glow
  bool peak = charge_audio_peak() != 0;

  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint16_t st = charge_lstart(L), n = charge_lcount(L);
    uint16_t half = n / 2;
    uint16_t run = (uint16_t)(((uint32_t)half * lvl) / 255);
    for (uint16_t k = 0; k < half + 1; k++) {
      bool lit = k < run;
      bool edge = lit && (k + 1 == run);
      if (!lit && !peak) continue;
      uint8_t pos8 = (uint8_t)(((uint32_t)k * 255) / (half ? half : 1));
      // From center: fill middle->out instead of ends->in
      uint16_t i1 = SEGMENT.check1 ? (uint16_t)(half - k < 0 ? 0 : half - k) : k;
      uint16_t i2 = SEGMENT.check1 ? (uint16_t)(half + k >= n ? n - 1 : half + k)
                                   : (uint16_t)(n - 1 - k);
      uint32_t c = lit ? SEGMENT.color_from_palette((uint8_t)(pos8 + (now >> 5)), false, true, 255)
                       : color_fade(RGBW32(255, 255, 255, 0), 70, true);   // peak wash
      if (edge) c = color_blend(c, RGBW32(255, 255, 255, 0), 160);         // hot leading edge
      charge_setpx(st + i1, c);
      charge_setpx(st + i2, c);
    }
  }
}

// =====================================================================
// CHARGE Premiere — a ~22s movie-title sequence, looping:
//   dust motes -> a spotlight sweeps in and settles on each letter in
//   turn; C/A/G crackle in electrically, H/R/E explode in with a 2D
//   shockwave ring -> all-lit power swell -> lightning strikes + strobes
//   -> radial palette burst finale -> fade to black -> loop.
// Single pass per pixel; the whole timeline is a pure function of time.
// =====================================================================
static const char _data_CHARGE_PREMIERE[] PROGMEM =
  "CHARGE Premiere@Length,Sparkle;!,!,!;!;2;sx=128,ix=160,pal=255";

static void mode_charge_premiere() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint32_t now = strip.now;
  uint32_t total = 30000 - (uint32_t)SEGMENT.speed * 60;   // 14.7..30 s
  uint32_t t = now % total;
  uint32_t lap = now / total;
  uint32_t u = total / 24;                                 // one "beat"
  uint8_t spk = SEGMENT.intensity;

  uint8_t cx[CHARGE_NUM_LETTERS], cy[CHARGE_NUM_LETTERS];
  charge_letter_centroids(cx, cy);

  // per-letter reveal state: 0 = hidden, 1 = revealing (q 0..255), 2 = lit
  uint8_t lmode[CHARGE_NUM_LETTERS], lq[CHARGE_NUM_LETTERS];
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    uint32_t w0 = (2 + 2 * (uint32_t)L) * u;               // reveal L: [(2+2L)u, (4+2L)u)
    uint32_t w1 = w0 + 2 * u;
    if (t < w0)      { lmode[L] = 0; lq[L] = 0; }
    else if (t < w1) { lmode[L] = 1; lq[L] = (uint8_t)(((t - w0) * 255) / (2 * u)); }
    else             { lmode[L] = 2; lq[L] = 255; }
  }

  // spotlight position (grid coords), active only through the reveals
  int16_t spx = -30, spy = CHARGE_GRID_H / 2;
  bool spot = false;
  for (uint8_t L = 0; L < CHARGE_NUM_LETTERS; L++) {
    if (lmode[L] != 1) continue;
    spot = true;
    int16_t ax = (L == 0) ? -20 : cx[L - 1], ay = (L == 0) ? (CHARGE_GRID_H / 2) : cy[L - 1];
    if (lq[L] < 100) {                                     // gliding to letter L
      uint8_t e = charge_smooth8((uint8_t)(((uint16_t)lq[L] * 255) / 100));
      spx = (int16_t)(ax + ((int32_t)(cx[L] - ax) * e) / 255);
      spy = (int16_t)(ay + ((int32_t)(cy[L] - ay) * e) / 255);
    } else {                                               // holding, tiny wobble
      spx = (int16_t)(cx[L] + (int16_t)(charge_tri8(now, 900) / 64) - 2);
      spy = cy[L];
    }
    break;
  }
  if (t < 2 * u) {                                         // opening sweep-in
    spot = true;
    spx = (int16_t)(-30 + (int32_t)(cx[0] + 30) * (int32_t)t / (int32_t)(2 * u));
    spy = (int16_t)(CHARGE_GRID_H / 2 + (charge_tri8(t, 1300) / 32) - 4);
  }

  uint32_t beat = t / u;
  // swell 14..17, lightning 17..19, finale 19..22, fade 22..24
  uint8_t swellq = (beat >= 14 && beat < 17) ? (uint8_t)(((t - 14 * u) * 255) / (3 * u)) : (beat >= 17 ? 255 : 0);
  bool strike = false; uint8_t strobe = 0;
  uint8_t boltRow[CHARGE_GRID_W];
  if (beat >= 17 && beat < 19) {
    uint32_t su = t - 17 * u, sidx = su / u, sph = su % u;
    uint32_t hseed = charge_hash(lap * 7919u + sidx + 0xB017u);
    if (sph < (u * 55) / 100) {                            // the bolt itself
      strike = true;
      int16_t r = (int16_t)(4 + (hseed % 12));
      for (uint16_t c = 0; c < CHARGE_GRID_W; c++) {       // seeded jagged walk
        boltRow[c] = (uint8_t)(r < 0 ? 0 : (r >= CHARGE_GRID_H ? CHARGE_GRID_H - 1 : r));
        uint32_t hs = charge_hash(hseed ^ (c * 0x9E3779B1u));
        r = (int16_t)(r + (int16_t)(hs % 5) - 2);
      }
    } else if (((sph * 100) / u >= 60 && (sph * 100) / u < 70) ||
               ((sph * 100) / u >= 80 && (sph * 100) / u < 90)) {
      strobe = 140;                                        // whole-sign strobes
    }
  }
  uint8_t finq = (beat >= 19 && beat < 22) ? (uint8_t)(((t - 19 * u) * 255) / (3 * u)) : 0;
  uint8_t fadeq = (beat >= 22) ? (uint8_t)(((t - 22 * u) * 255) / (2 * u)) : 0;
  uint16_t ringR = (uint16_t)(((uint32_t)finq * 90) / 255);

  for (uint16_t i = 0; i < CHARGE_NUM_PIXELS; i++) {
    uint8_t col = pgm_read_byte(&CHARGE_COL[i]);
    uint8_t row = pgm_read_byte(&CHARGE_ROW[i]);
    uint8_t L   = pgm_read_byte(&CHARGE_LETTER[i]);
    uint32_t c = BLACK;

    if (t < 2 * u) {                                       // dust motes
      if ((charge_hash((uint32_t)i * 131 + ((t >> 8) * 0x85EBu)) & 0xFF) < (spk >> 5))
        c = color_fade(RGBW32(200, 200, 220, 0), 70, true);
    }

    if (lmode[L] == 2) {                                   // lit letter
      uint8_t bri = 60;                                    // ember hold
      uint32_t basec = CHARGE_CYAN;
      if (swellq) { bri = (uint8_t)(60 + ((uint16_t)195 * swellq) / 255);
                    basec = color_blend(CHARGE_CYAN, RGBW32(255,255,255,0), swellq / 2); }
      if (beat >= 17 && beat < 19) { bri = 255; basec = RGBW32(180, 255, 255, 0); }
      if (finq) { bri = 200; basec = CHARGE_CYAN; }
      c = color_fade(basec, bri, true);
    } else if (lmode[L] == 1 && lq[L] >= 100) {
      uint8_t q = lq[L];
      uint16_t st = charge_lstart(L), n = charge_lcount(L);
      uint16_t k = (uint16_t)(i - st);
      if ((L & 1) == 0) {                                  // C/A/G: crackle in
        uint8_t density = (uint8_t)(((uint16_t)(q - 100) * 255) / 155);
        uint32_t slice = t / 70;
        uint16_t seg = k / 3;
        if ((charge_hash(slice * 0x51EDu ^ ((uint32_t)L << 8) ^ seg) & 0xFF) < density)
          c = color_fade(CHARGE_CYAN, (uint8_t)(180 + (hw_random8() % 76)), true);
      } else {                                             // H/R/E: explode in
        uint16_t mid = n / 2;
        uint16_t spread = (uint16_t)(((uint32_t)(q - 100) * (mid + 8)) / 155);
        uint16_t dk = (k > mid) ? (uint16_t)(k - mid) : (uint16_t)(mid - k);
        if (dk < spread) {
          uint8_t bri = (dk + 6 >= spread) ? 255 : (uint8_t)(160 + ((uint16_t)dk * 95) / (spread ? spread : 1));
          c = color_fade(CHARGE_CYAN, bri, true);
        }
        // 2D shockwave ring around the letter, palette-tinged
        uint16_t rr = (uint16_t)(((uint32_t)(q - 100) * 55) / 155);
        uint8_t d = charge_dist8((int16_t)col - cx[L], (int16_t)row - cy[L]);
        int16_t band = (int16_t)d - (int16_t)rr; if (band < 0) band = (int16_t)-band;
        if (band < 3 && rr > 2 && rr < 50)
          c = color_blend(c, SEGMENT.color_from_palette((uint8_t)(d * 4), false, true, 255), (uint8_t)(220 - band * 60));
      }
    }

    if (spot) {                                            // spotlight pool
      int32_t dx = (int32_t)col - spx, dy = (int32_t)row - spy;
      int32_t d2 = dx * dx + dy * dy;
      const int32_t R2 = 13 * 13;
      if (d2 < R2) {
        uint8_t w = (uint8_t)(((R2 - d2) * 200) / R2);
        c = color_blend(c, RGBW32(255, 230, 180, 0), w);
      }
    }

    if (strike && (int16_t)row >= (int16_t)boltRow[col] - 2 && (int16_t)row <= (int16_t)boltRow[col] + 2) {
      int16_t dr = (int16_t)row - (int16_t)boltRow[col]; if (dr < 0) dr = (int16_t)-dr;
      c = (dr <= 1) ? RGBW32(255, 255, 255, 0) : color_blend(c, CHARGE_CYAN, 160);
    }
    if (strobe) c = color_blend(c, RGBW32(255, 255, 255, 0), strobe);

    if (finq) {                                            // finale: radial burst
      uint8_t d = charge_dist8((int16_t)col - CHARGE_GRID_W / 2, (int16_t)row - CHARGE_GRID_H / 2);
      int16_t band = (int16_t)d - (int16_t)ringR; if (band < 0) band = (int16_t)-band;
      if (band < 5)
        c = color_blend(c, SEGMENT.color_from_palette((uint8_t)(d * 3 + (now >> 4)), false, true, 255), (uint8_t)(240 - band * 40));
      if ((charge_hash((uint32_t)i * 31 + ((t >> 6) * 0xC2B2u)) & 0xFF) < (spk >> 3))
        c = color_blend(c, RGBW32(255, 255, 255, 0), 180);  // celebration glitter
    }

    if (fadeq) c = color_fade(c, (uint8_t)(255 - fadeq), true);
    charge_setpx(i, c);
  }
}

// =====================================================================
// CHARGE Dreamwave — the whole sign becomes an interference field: every
// letter's centroid is a wave source with its own wavelength and phase;
// pixels sum all six wavefronts (own letter weighted double) and map the
// result through a palette. Wild, spatial, letter-aware, deeply pleasing.
// =====================================================================
static const char _data_CHARGE_DREAMWAVE[] PROGMEM =
  "CHARGE Dreamwave@Speed,Glow,,Zoom,,Letter pulse;!,!,!;!;2;sx=100,ix=230,c2=128,o1=1,pal=255";

static void mode_charge_dreamwave() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }
  uint32_t now = strip.now;

  uint8_t cx[CHARGE_NUM_LETTERS], cy[CHARGE_NUM_LETTERS];
  charge_letter_centroids(cx, cy);

  // per-source wavelength (cells), phase offset, and drift rate
  uint16_t wl[CHARGE_NUM_LETTERS]; uint8_t ph0[CHARGE_NUM_LETTERS];
  uint32_t tv = (uint32_t)((uint64_t)now * (20 + SEGMENT.speed) / 256);  // wave time
  for (uint8_t k = 0; k < CHARGE_NUM_LETTERS; k++) {
    uint32_t h = charge_hash(0xD3EA0000u | k);
    wl[k] = (uint16_t)((10 + (h & 7)) * (64 + (uint16_t)SEGMENT.custom2) / 128);  // Zoom
    if (wl[k] < 4) wl[k] = 4;
    ph0[k] = (uint8_t)(h >> 8);
  }
  // per-letter pulse (own breathing tempo)
  uint8_t lpulse[CHARGE_NUM_LETTERS];
  for (uint8_t k = 0; k < CHARGE_NUM_LETTERS; k++) {
    uint32_t h = charge_hash(0xB1EA0000u | k);
    lpulse[k] = SEGMENT.check1
      ? (uint8_t)(190 + (charge_smooth8(charge_tri8(now + (h & 0xFFF), 2600 + (h % 2200))) >> 2))
      : 255;
  }

  for (uint16_t i = 0; i < CHARGE_NUM_PIXELS; i++) {
    uint8_t col = pgm_read_byte(&CHARGE_COL[i]);
    uint8_t row = pgm_read_byte(&CHARGE_ROW[i]);
    uint8_t L   = pgm_read_byte(&CHARGE_LETTER[i]);
    uint32_t sum = 0, wsum = 0;
    for (uint8_t k = 0; k < CHARGE_NUM_LETTERS; k++) {
      uint8_t d = charge_dist8((int16_t)col - cx[k], (int16_t)row - cy[k]);
      uint8_t phase = (uint8_t)(((uint16_t)d * 256) / wl[k] - (tv >> 3) + ph0[k]);
      uint8_t wave = (uint8_t)(phase < 128 ? phase * 2 : (255 - phase) * 2);  // byte triangle
      uint8_t w = (k == L) ? 2 : 1;                       // own letter dominates
      sum += (uint32_t)wave * w;
      wsum += w;
    }
    uint8_t v = (uint8_t)(sum / wsum);
    uint32_t c = SEGMENT.color_from_palette((uint8_t)(v + (now >> 6)), false, true, 255);  // slow palette drift
    if (v > 235) c = color_blend(c, RGBW32(255, 255, 255, 0), (uint8_t)((v - 235) * 12));  // antinode shimmer
    // high contrast: bright wavefronts roll over dark troughs (4:1)
    uint8_t bri = (uint8_t)(((uint16_t)SEGMENT.intensity * (60 + ((uint16_t)charge_smooth8(v) * 195) / 255)) / 255);
    bri = (uint8_t)(((uint16_t)bri * lpulse[L]) / 255);
    charge_setpx(i, color_fade(c, bri, true));
  }
}

// Registration table so firmware + simulator enumerate the same effect list.
// Extend here when adding effects; tedxfargo.cpp and the sim both walk it.
// NAMING RULE: every effect name starts with "CHARGE " so the whole suite
// sorts/filters together in the WLED effect list (QA enforces this).
typedef void (*charge_mode_fn)();
struct ChargeFxEntry { charge_mode_fn fn; const char* meta; };
static const ChargeFxEntry CHARGE_FX_LIST[] = {
  { &mode_charge_bootup,    _data_CHARGE_BOOTUP },
  { &mode_charge_surge,     _data_CHARGE_SURGE },
  { &mode_charge_comet,     _data_CHARGE_COMET },
  { &mode_charge_marquee,   _data_CHARGE_MARQUEE },
  { &mode_charge_morph,     _data_CHARGE_MORPH },
  { &mode_charge_pacman,    _data_CHARGE_PACMAN },
  { &mode_charge_lava,      _data_CHARGE_LAVA },
  { &mode_charge_ants,      _data_CHARGE_ANTS },
  { &mode_charge_raider,    _data_CHARGE_RAIDER },
  { &mode_charge_gravity,   _data_CHARGE_GRAVITY },
  { &mode_charge_fireworks, _data_CHARGE_FIREWORKS },
  { &mode_charge_drip,      _data_CHARGE_DRIP },
  { &mode_charge_pulse,     _data_CHARGE_PULSE },
  { &mode_charge_premiere,  _data_CHARGE_PREMIERE },
  { &mode_charge_dreamwave, _data_CHARGE_DREAMWAVE },
};
static const uint8_t CHARGE_FX_COUNT =
    sizeof(CHARGE_FX_LIST) / sizeof(CHARGE_FX_LIST[0]);
