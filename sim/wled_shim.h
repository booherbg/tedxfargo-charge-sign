// WLED 16.0.1 API shim for the CHARGE effect simulator.
//
// Mirrors ONLY the surface charge_fx.h is allowed to use (see its header
// comment). Every non-trivial function is a verbatim port from the WLED
// 16.0.1 sources, with the source file cited — if WLED is upgraded, re-diff
// these against the new checkout. The effect code itself is NOT ported: the
// simulator compiles the same charge_fx.h the firmware does.
#pragma once
#include <stdint.h>

// --- AVR/Arduino compat: PROGMEM is a no-op (as it is on ESP32) ---
#define PROGMEM
#define pgm_read_byte(addr) (*(const uint8_t*)(addr))
#define pgm_read_word(addr) (*(const uint16_t*)(addr))
typedef uint8_t byte;

// --- color macros: wled00/colors.h (identical in bus_wrapper.h) ---
#define RGBW32(r,g,b,w) (uint32_t((byte(w) << 24) | (byte(r) << 16) | (byte(g) << 8) | (byte(b))))
// wled00/FX.h
#define BLACK      (uint32_t)0x000000

// --- qsub8: FastLED lib8tion (saturating 8-bit subtract) ---
static inline uint8_t qsub8(uint8_t i, uint8_t j) {
  int t = i - j;
  if (t < 0) t = 0;
  return (uint8_t)t;
}

// --- hw_random8: wled00/fcn_declare.h reads the ESP32 hardware RNG register.
// Here: xorshift32, seedable so simulator runs are reproducible. Semantics
// (uniform u8 noise) match; the sequence obviously differs from hardware.
extern uint32_t sim_rng_state;
static inline uint8_t hw_random8() {
  uint32_t x = sim_rng_state;
  x ^= x << 13; x ^= x >> 17; x ^= x << 5;
  sim_rng_state = x;
  return (uint8_t)(x >> 24);
}

// --- color_fade: verbatim port of wled00/colors.cpp (16.0.1) ---
uint32_t color_fade(uint32_t c1, uint8_t amount, bool video = false);

// --- Segment: framebuffer + the runtime/UI fields effects touch.
// Field types match wled00/FX.h Segment (step/call u32, aux0/aux1 u16,
// speed/intensity u8) so wrap/overflow behavior is identical.
struct SimSegment {
  // UI fields
  uint8_t  speed     = 128;
  uint8_t  intensity = 128;
  uint8_t  custom1 = 0, custom2 = 0, custom3 = 0;
  bool     check1 = false, check2 = false, check3 = false;
  // runtime state (cleared on effect (re)start, like WLED's markForReset path)
  uint32_t step = 0;
  uint32_t call = 0;
  uint16_t aux0 = 0, aux1 = 0;
  // the 2D canvas
  int W = 0, H = 0;
  uint32_t* buf = nullptr;

  bool is2D() const { return true; }
  unsigned vWidth() const { return W; }
  unsigned vHeight() const { return H; }
  void fill(uint32_t c) const {
    for (int i = 0; i < W * H; i++) buf[i] = c;
  }
  // bounds semantics: wled00/FX_2Dfcn.cpp Segment::setPixelColorXY(int,int,u32)
  void setPixelColorXY(int x, int y, uint32_t col) const {
    if ((unsigned)x >= vWidth() || (unsigned)y >= vHeight()) return;
    buf[y * W + x] = col;
  }
};

struct SimStrip {
  uint32_t now = 0;  // frame-coherent millis, set by the harness per tick
};

extern SimSegment sim_segment;
extern SimStrip strip;

// wled00/FX.h: SEGMENT and SEGENV are both (*strip._currentSegment)
#define SEGMENT sim_segment
#define SEGENV  sim_segment
