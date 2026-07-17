// WLED 16.0.1 API shim for the CHARGE effect simulator.
//
// Mirrors ONLY the surface charge_fx.h is allowed to use (see its header
// comment). Fidelity strategy, in order of preference:
//   1. COMPILE THE REAL THING: sim/vendor/fastled_slim.h is WLED's own
//      palette/color dependency, vendored byte-for-byte from the checkout
//      (wled00/src/dependencies/fastled_slim/) with a no-op pgmspace.h stub —
//      CRGB, CRGBPalette16, gradient loading are WLED's actual code.
//   2. VERBATIM PORTS with the source file cited (color_fade, color_blend,
//      ColorFromPalette, color_from_palette, loadPalette) — re-diff on WLED
//      upgrades.
//   3. DOCUMENTED APPROXIMATIONS (hw_random8 = seeded PRNG; palette 1
//      "Random Cycle" = hash-seeded regeneration; no palette transitions).
// The effect code itself is NOT ported: the simulator compiles the same
// charge_fx.h the firmware does. Palette DATA is extracted from the WLED
// source by sim/extract_palettes.py and fed in at runtime — never transcribed.
#pragma once
#include <stdint.h>
#include "fastled_slim.h"   // vendored — brings CRGB/CRGBPalette16/qsub8/scale8/pgmspace

typedef uint8_t byte;

// --- color macros: wled00/colors.h (identical in bus_wrapper.h) ---
#define RGBW32(r,g,b,w) (uint32_t((byte(w) << 24) | (byte(r) << 16) | (byte(g) << 8) | (byte(b))))
// wled00/FX.h
#define BLACK      (uint32_t)0x000000
// wled00/colors.h channel accessors
#define W(c) (byte((c) >> 24))
#define NUM_COLORS 3

// --- hw_random8: wled00/fcn_declare.h reads the ESP32 hardware RNG register.
// Here: xorshift32, seedable so simulator runs are reproducible.
extern uint32_t sim_rng_state;
static inline uint8_t hw_random8() {
  uint32_t x = sim_rng_state;
  x ^= x << 13; x ^= x >> 17; x ^= x << 5;
  sim_rng_state = x;
  return (uint8_t)(x >> 24);
}

// --- verbatim ports from wled00/colors.cpp (16.0.1) ---
uint32_t color_fade(uint32_t c1, uint8_t amount, bool video = false);
uint32_t color_blend(uint32_t color1, uint32_t color2, uint8_t blend);
uint32_t ColorFromPalette(const CRGBPalette16 &pal, unsigned index,
                          uint8_t brightness = 255, TBlendType blendType = LINEARBLEND);

// --- palette registry: data pushed in by the harness (JS page / node QA /
// native test). Fixed ids 6..12 are 16xu32 tables; 13..71 gradient bytes;
// customs count down from 200; usermod palettes count down from 255
// (wled00/const.h id layout).
void shim_pal_fixed16(uint8_t id, const uint32_t *entries16);
void shim_pal_gradient(uint8_t id, const uint8_t *bytes, int len);   // (pos,r,g,b)*
void shim_pal_counts(uint8_t custom_count, uint8_t usermod_count);
extern uint8_t shim_paletteBlend;   // wled00: strip.paletteBlend, default 0

// --- Segment: framebuffer + the runtime/UI fields effects touch.
// Field types match wled00/FX.h Segment (step/call u32, aux0/aux1 u16,
// speed/intensity u8) so wrap/overflow behavior is identical.
struct SimSegment {
  // UI fields
  uint8_t  speed     = 128;
  uint8_t  intensity = 128;
  uint8_t  custom1 = 0, custom2 = 0, custom3 = 0;
  bool     check1 = false, check2 = false, check3 = false;
  uint8_t  palette = 0;
  uint8_t  default_palette = 6;      // FX_fcn.cpp setMode: pal= default, else 6
  uint32_t colors[NUM_COLORS] = { 0x00FFAA00u, 0x00000000u, 0x00000000u };
  // runtime state (cleared on effect (re)start, like WLED's markForReset path)
  uint32_t step = 0;
  uint32_t call = 0;
  uint16_t aux0 = 0, aux1 = 0;
  CRGBPalette16 _currentPalette;     // loaded per tick (WLED: beginDraw())
  // the 2D canvas
  int W = 0, H = 0;
  uint32_t* buf = nullptr;

  bool is2D() const { return true; }
  unsigned vWidth() const { return W; }
  unsigned vHeight() const { return H; }
  unsigned vLength() const { return (unsigned)W * H; }
  // wled00/FX.h: getCurrentColor(i) = _currentColors[i<NUM_COLORS?i:0]
  uint32_t getCurrentColor(unsigned i) const { return colors[i < NUM_COLORS ? i : 0]; }
  void fill(uint32_t c) const {
    for (int i = 0; i < W * H; i++) buf[i] = c;
  }
  // bounds semantics: wled00/FX_2Dfcn.cpp Segment::setPixelColorXY(int,int,u32)
  void setPixelColorXY(int x, int y, uint32_t col) const {
    if ((unsigned)x >= vWidth() || (unsigned)y >= vHeight()) return;
    buf[y * W + x] = col;
  }
  // ports of wled00/FX_fcn.cpp Segment::loadPalette / color_from_palette
  void loadPalette(CRGBPalette16 &targetPalette, uint8_t pal) const;
  uint32_t color_from_palette(uint16_t i, bool mapping, bool moving,
                              uint8_t mcol, uint8_t pbri = 255) const;
};

struct SimStrip {
  uint32_t now = 0;  // frame-coherent millis, set by the harness per tick
};

extern SimSegment sim_segment;
extern SimStrip strip;

// wled00/FX.h: SEGMENT and SEGENV are both (*strip._currentSegment)
#define SEGMENT sim_segment
#define SEGENV  sim_segment
