// TEDxFargo CHARGE — custom effect mode functions.
//
// SHARED SOURCE OF TRUTH: this exact file compiles into BOTH the WLED firmware
// (via tedxfargo.cpp, after #include "wled.h") and the browser simulator (via
// sim/sim_main.cpp, after #include "wled_shim.h"). It must therefore use only
// the API surface the shim mirrors:
//   SEGMENT.fill/.setPixelColorXY/.is2D/.speed/.intensity
//   SEGENV.step/.aux0/.aux1/.call
//   strip.now, hw_random8(), qsub8(), color_fade(), RGBW32, BLACK
//   pgm_read_byte/pgm_read_word + the charge_geometry.h tables
// Do NOT include WLED headers here. (Editor lint on this file standalone is
// expected noise — it only compiles after wled.h or wled_shim.h.)
#pragma once
#include <stdint.h>
#include "charge_geometry.h"

// Effect metadata: Name@slider1,slider2;colors;palette;flags(2=2D)
static const char _data_CHARGE_BOOTUP[] PROGMEM = "CHARGE Boot@Speed,Flicker;;;2";

// Neon boot-up: letters ignite in chain order C->H->A->R->G->E, each flickering
// on before settling to electric cyan; once all lit, hold, then loop.
static void mode_charge_bootup() {
  if (!SEGMENT.is2D()) { SEGMENT.fill(BLACK); return; }  // needs the matrix

  uint16_t letterMs = 900 - (SEGMENT.speed * 3);          // ~900..~135 ms per letter
  const uint16_t holdMs = 1500;
  uint32_t cycle = (uint32_t)letterMs * CHARGE_NUM_LETTERS + holdMs;

  if (SEGENV.step == 0 || (strip.now - SEGENV.step) > cycle) SEGENV.step = strip.now;  // (re)start
  uint32_t t = strip.now - SEGENV.step;

  SEGMENT.fill(BLACK);                                    // clear the matrix each frame
  const uint32_t cyan = RGBW32(0, 255, 255, 0);           // electric CHARGE cyan
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
    uint32_t col = color_fade(cyan, bri, true);

    uint16_t start = pgm_read_word(&CHARGE_LETTER_START[L]);
    uint16_t count = pgm_read_word(&CHARGE_LETTER_COUNT[L]);
    for (uint16_t k = 0; k < count; k++) {
      uint16_t i = start + k;
      SEGMENT.setPixelColorXY(pgm_read_byte(&CHARGE_COL[i]),
                              pgm_read_byte(&CHARGE_ROW[i]), col);
    }
  }
}

// Registration table so firmware + simulator enumerate the same effect list.
// Extend here when adding effects; tedxfargo.cpp and the sim both walk it.
typedef void (*charge_mode_fn)();
struct ChargeFxEntry { charge_mode_fn fn; const char* meta; };
static const ChargeFxEntry CHARGE_FX_LIST[] = {
  { &mode_charge_bootup, _data_CHARGE_BOOTUP },
};
static const uint8_t CHARGE_FX_COUNT =
    sizeof(CHARGE_FX_LIST) / sizeof(CHARGE_FX_LIST[0]);
