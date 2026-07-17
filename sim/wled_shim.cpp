#include "wled_shim.h"

uint32_t sim_rng_state = 0x20260716u;  // any nonzero default; sim_seed() overrides

SimSegment sim_segment;
SimStrip strip;

// Verbatim port of color_fade from wled00/colors.cpp @ WLED 16.0.1 (only the
// IRAM_ATTR annotation dropped). Do not "improve" — fidelity beats style.
uint32_t color_fade(uint32_t c1, uint8_t amount, bool video) {
  if (c1 == BLACK || amount == 0) return 0; // black or full fade
  if (amount == 255) return c1;             // no change
  const uint32_t TWO_CHANNEL_MASK = 0x00FF00FF;
  uint32_t rb = c1 & TWO_CHANNEL_MASK; // extract R and B channels
  uint32_t wg = (c1 >> 8) & TWO_CHANNEL_MASK; // extract W and G channels (shifted for multiplication)
  uint32_t rb_scaled;
  uint32_t wg_scaled;

  // video scaling: make sure colors do not dim to zero if they started non-zero unless they distort the hue
  if (video) {
    rb_scaled = ((rb * amount + 0x007F007F) >> 8) & TWO_CHANNEL_MASK; // scale red and blue, add 0.5 for rounding
    wg_scaled = (wg * amount + 0x007F007F) & ~TWO_CHANNEL_MASK; // scale white and green, add 0.5 for rounding
    uint8_t r = byte(rb>>16), g = byte(wg), b = byte(rb), w = byte(wg>>16); // extract r, g, b, w channels from original color (wg is shifted)
    uint8_t maxc = (r > g) ? ((r > b) ? r : b) : ((g > b) ? g : b); // determine dominant channel for hue preservation
    maxc = (maxc>>2) + 1; // divide by 4 to get ~25% threshold for hue preservation, add 1 to prevent "washout" of very dark colors (prevents them becoming gray)
    rb_scaled |= r > maxc ? 0x00010000 : 0;
    wg_scaled |= g > maxc ? 0x00000100 : 0;
    rb_scaled |= b > maxc ? 0x00000001 : 0;
    wg_scaled |= w ? 0x01000000 : 0; // preserve white if it is present
  } else {
    rb_scaled = ((rb * (amount + 1)) >> 8) & TWO_CHANNEL_MASK; // scale red and blue
    wg_scaled = ((wg * (amount + 1)) & ~TWO_CHANNEL_MASK); // scale white and green
  }

  return (rb_scaled | wg_scaled);
}
