#include "wled_shim.h"
#include <string.h>

uint32_t sim_rng_state = 0x20260716u;  // any nonzero default; sim_seed() overrides

SimSegment sim_segment;
SimStrip strip;
uint8_t shim_paletteBlend = 0;         // WLED default (cfg: strip.paletteBlend)

// ---------------------------------------------------------------------------
// palette registry — data extracted from the WLED source / device backups is
// pushed in by the harness; ids follow wled00/const.h layout.
// ---------------------------------------------------------------------------
static uint32_t g_fixed16[13][16];              // ids 6..12 (16 x u32 each)
static bool     g_fixed16_ok[13];
static uint8_t  g_grad[256][72];                // gradient bytes by palette id
static uint8_t  g_grad_ok[256];
static uint8_t  g_custom_count = 0, g_um_count = 0;

void shim_pal_fixed16(uint8_t id, const uint32_t *entries16) {
  if (id < 6 || id > 12) return;
  memcpy(g_fixed16[id], entries16, 16 * sizeof(uint32_t));
  g_fixed16_ok[id] = true;
}
void shim_pal_gradient(uint8_t id, const uint8_t *bytes, int len) {
  if (len > 72) len = 72;
  len -= len % 4;                                   // whole (pos,r,g,b) entries only
  if (len < 4) return;
  memcpy(g_grad[id], bytes, (size_t)len);
  g_grad[id][len - 4] = 255;   // guarantee a terminating stop at index 255
                               // (loadDynamicGradientPalette scans until it sees one)
  g_grad_ok[id] = 1;
}
void shim_pal_counts(uint8_t custom_count, uint8_t usermod_count) {
  g_custom_count = custom_count; g_um_count = usermod_count;
}

// Port of Segment::allocateData (wled00/FX_fcn.cpp): reuse when big enough
// (zeroing on an effect's first frame), else (re)allocate zeroed. Sim uses a
// fixed pool — effects requesting more than the pool get 'false' like a
// device that is out of segment data RAM.
alignas(8) static uint8_t seg_data_pool[8192];   // heap-like alignment (WLED callocs)
bool SimSegment::allocateData(size_t len) {
  if (len == 0 || len > sizeof(seg_data_pool)) return false;
  if (data && _dataLen >= len) {
    if (call == 0) memset(data, 0, len);
    return true;
  }
  data = seg_data_pool;
  memset(data, 0, len);
  _dataLen = (unsigned)len;
  return true;
}

// Verbatim port of ColorFromPalette from wled00/colors.cpp @ WLED 16.0.1.
uint32_t ColorFromPalette(const CRGBPalette16& pal, unsigned index, uint8_t brightness, TBlendType blendType) {
  if (blendType == LINEARBLEND_NOWRAP) {
    index = (index * 0xF0) >> 8; // Blend range is affected by lo4 blend of values, remap to avoid wrapping
  }
  unsigned hi4 = byte(index) >> 4;
  unsigned lo4 = (index & 0x0F);
  const CRGB* entry = (CRGB*)&(pal[0]) + hi4;
  unsigned red1   = entry->r;
  unsigned green1 = entry->g;
  unsigned blue1  = entry->b;
  if (lo4 && blendType != NOBLEND) {
    if (hi4 == 15) entry = &(pal[0]);
    else ++entry;
    unsigned f2 = (lo4 << 4);
    unsigned f1 = 256 - f2;
    red1   = (red1   * f1 + (unsigned)entry->r * f2) >> 8; // note: using color_blend() is slower
    green1 = (green1 * f1 + (unsigned)entry->g * f2) >> 8;
    blue1  = (blue1  * f1 + (unsigned)entry->b * f2) >> 8;
  }
  if (brightness < 255) { // note: zero checking could be done to return black but that is hardly ever used so it is omitted
    // actually same as color_fade(), using color_fade() is slower
    uint32_t scale = brightness + 1; // adjust for rounding (bitshift)
    red1   = (red1   * scale) >> 8;
    green1 = (green1 * scale) >> 8;
    blue1  = (blue1  * scale) >> 8;
  }
  return RGBW32(red1,green1,blue1,0);
}

// Port of Segment::loadPalette (wled00/FX_fcn.cpp @ 16.0.1). Adaptations:
// - palette data comes from the registry above instead of PROGMEM/vectors
// - palette 1 "Random Cycle" is APPROXIMATED: a 4-color palette re-hashed
//   every ~6s (WLED evolves a harmonic random palette; sequences differ)
void SimSegment::loadPalette(CRGBPalette16 &targetPalette, uint8_t pal) const {
  if (pal == 0) pal = default_palette;
  if (pal >= 72) {                                   // FIXED_PALETTE_COUNT
    if (pal > 200) {                                 // usermod range (IDs 201-255)
      if ((255 - pal) >= g_um_count) pal = 0;
    } else {                                         // custom range
      if ((200 - pal) >= g_custom_count) pal = 0;
    }
  }
  switch (pal) {
    case 0: //default palette. Exceptions for specific effects above
      if (g_fixed16_ok[6]) targetPalette = *(const TProgmemRGBPalette16*)g_fixed16[6];  // PartyColors_gc22
      break;
    case 1: { //randomly generated palette (approximation — see header note)
      uint32_t h = strip.now / 6000;
      CRGB c[4];
      for (int k = 0; k < 4; k++) {
        uint32_t x = h ^ (0xA5A5u + k * 0x9E3779B1u);
        x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16;
        c[k] = CRGB((uint32_t)(x & 0xFFFFFF) | 0x404040u);
      }
      targetPalette = CRGBPalette16(c[0], c[1], c[2], c[3]);
      break; }
    case 2: {//primary color only
      CRGB prim = CRGB(colors[0]);
      targetPalette = CRGBPalette16(prim);
      break;}
    case 3: {//primary + secondary
      CRGB prim = CRGB(colors[0]);
      CRGB sec  = CRGB(colors[1]);
      targetPalette = CRGBPalette16(prim,prim,sec,sec);
      break;}
    case 4: {//primary + secondary + tertiary
      CRGB prim = CRGB(colors[0]);
      CRGB sec  = CRGB(colors[1]);
      CRGB ter  = CRGB(colors[2]);
      targetPalette = CRGBPalette16(ter,sec,prim);
      break;}
    case 5: {//primary + secondary (+tertiary if not off), more distinct
      CRGB prim = CRGB(colors[0]);
      CRGB sec  = CRGB(colors[1]);
      if (colors[2]) {
        CRGB ter = CRGB(colors[2]);
        targetPalette = CRGBPalette16(prim,prim,prim,prim,prim,sec,sec,sec,sec,sec,ter,ter,ter,ter,ter,prim);
      } else {
        targetPalette = CRGBPalette16(prim,prim,prim,prim,prim,prim,prim,prim,sec,sec,sec,sec,sec,sec,sec,sec);
      }
      break;}
    default:
      if (pal < 13) {                                // fastled palettes 6-12
        if (g_fixed16_ok[pal]) targetPalette = *(const TProgmemRGBPalette16*)g_fixed16[pal];
      } else {                                       // gradient/custom/usermod by id
        if (g_grad_ok[pal]) targetPalette.loadDynamicGradientPalette(g_grad[pal]);
      }
      break;
  }
}

// Verbatim port of Segment::color_from_palette (wled00/FX_fcn.cpp @ 16.0.1).
// Adaptations: getCurrentColor() has no transitions here; _isRGB is always
// true (WS281x); CRGBW w-channel install done with uint32 ops (same bytes).
uint32_t SimSegment::color_from_palette(uint16_t i, bool mapping, bool moving, uint8_t mcol, uint8_t pbri) const {
  uint32_t color = getCurrentColor(mcol);
  // default palette or no RGB support on segment
  if (palette == 0 && mcol < NUM_COLORS) {
    return color_fade(color, pbri, true);
  }

  unsigned paletteIndex = i;
  if (mapping) { unsigned m = (i * 255) / vLength(); paletteIndex = m < 255u ? m : 255u; }
  // paletteBlend: 0 - wrap when moving, 1 - always wrap, 2 - never wrap, 3 - none (undefined/no interpolation of palette entries)
  TBlendType blend = NOBLEND;
  switch (shim_paletteBlend) {
    case 0: blend = moving ? LINEARBLEND : LINEARBLEND_NOWRAP; break;
    case 1: blend = LINEARBLEND; break;
    case 2: blend = LINEARBLEND_NOWRAP; break;
  }
  uint32_t palcol = ColorFromPalette(_currentPalette, paletteIndex, pbri, blend);
  return (palcol & 0x00FFFFFFu) | ((uint32_t)W(color) << 24);
}

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

// Verbatim port of color_blend from wled00/colors.cpp @ WLED 16.0.1 (only the
// WLED_O2_ATTR/IRAM_ATTR annotations dropped).
uint32_t color_blend(uint32_t color1, uint32_t color2, uint8_t blend) {
  // min / max blend checking is omitted: calls with 0 or 255 are rare, checking lowers overall performance
  const uint32_t TWO_CHANNEL_MASK = 0x00FF00FF;     // mask for R and B channels or W and G if negated (poorman's SIMD; https://github.com/wled/WLED/pull/4568#discussion_r1986587221)
  uint32_t rb1 =  color1       & TWO_CHANNEL_MASK;  // extract R & B channels from color1
  uint32_t wg1 = (color1 >> 8) & TWO_CHANNEL_MASK;  // extract W & G channels from color1 (shifted for multiplication later)
  uint32_t rb2 =  color2       & TWO_CHANNEL_MASK;  // extract R & B channels from color2
  uint32_t wg2 = (color2 >> 8) & TWO_CHANNEL_MASK;  // extract W & G channels from color2 (shifted for multiplication later)
  uint32_t rb3 = ((((rb1 << 8) | rb2) + (rb2 * blend) - (rb1 * blend)) >> 8) &  TWO_CHANNEL_MASK; // blend red and blue
  uint32_t wg3 = ((((wg1 << 8) | wg2) + (wg2 * blend) - (wg1 * blend)))      & ~TWO_CHANNEL_MASK; // negated mask for white and green
  return rb3 | wg3;
}
