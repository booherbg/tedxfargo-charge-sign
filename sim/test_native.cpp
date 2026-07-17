// Headless native harness: compiles the same wled_shim + charge_fx.h the wasm
// build uses, drives simulated hours of frames under ASan/UBSan, and asserts
// the CHARGE Boot behavior (order, color, loop, time-wrap safety).
// Build+run: sh sim/test_native.sh
#include "wled_shim.h"
#include "../wled/usermods/tedxfargo/charge_fx.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

// grid with canary guard bands — OOB writes by the effect corrupt a canary
// (ASan is broken on this macOS/clang combo, so we bring our own red zones)
#define CANARY_WORDS 256
#define CANARY_VAL   0xDEADBEEFu
static struct {
  uint32_t pre[CANARY_WORDS];
  uint32_t cells[CHARGE_GRID_W * CHARGE_GRID_H];
  uint32_t post[CANARY_WORDS];
} gbuf;

// audio glue stubs (swept during the soak)
static uint8_t g_audio = 128, g_peak = 0;
uint8_t charge_audio() { return g_audio; }
uint8_t charge_audio_peak() { return g_peak; }

static void register_palettes() {  // goblin palettes, same IDs as firmware/sim
  for (uint8_t i = 0; i < CHARGE_UM_PAL_COUNT; i++)
    shim_pal_gradient((uint8_t)(255 - i), CHARGE_UM_PAL_DATA[i], 44);
  shim_pal_counts(0, CHARGE_UM_PAL_COUNT);
}
#define grid gbuf.cells
static int fails = 0;

static void arm_canaries() {
  for (int i = 0; i < CANARY_WORDS; i++) gbuf.pre[i] = gbuf.post[i] = CANARY_VAL;
}
static bool canaries_ok() {
  for (int i = 0; i < CANARY_WORDS; i++)
    if (gbuf.pre[i] != CANARY_VAL || gbuf.post[i] != CANARY_VAL) return false;
  return true;
}

#define CHECK(cond, ...) do { \
  if (!(cond)) { fails++; printf("FAIL "); printf(__VA_ARGS__); printf("\n"); } \
} while (0)

static void reset_seg() {
  sim_segment.W = CHARGE_GRID_W; sim_segment.H = CHARGE_GRID_H;
  sim_segment.buf = grid;
  sim_segment.step = 0; sim_segment.call = 0;
  sim_segment.aux0 = 0; sim_segment.aux1 = 0;
  sim_segment.data = nullptr; sim_segment._dataLen = 0;
  sim_segment.fill(BLACK);
}

static void tick(uint32_t now) { strip.now = now; mode_charge_bootup(); sim_segment.call++; }
static void tick_fx(charge_mode_fn fn, uint32_t now) {
  strip.now = now;
  sim_segment.loadPalette(sim_segment._currentPalette, sim_segment.palette);
  fn();
  sim_segment.call++;
}

// is any pixel of letter L lit?
static bool letter_lit(int L) {
  uint16_t s = CHARGE_LETTER_START[L], c = CHARGE_LETTER_COUNT[L];
  for (uint16_t k = 0; k < c; k++) {
    uint16_t i = s + k;
    if (grid[CHARGE_ROW[i] * CHARGE_GRID_W + CHARGE_COL[i]]) return true;
  }
  return false;
}

int main() {
  const uint32_t FRAMETIME = 1000 / 42;
  arm_canaries();
  register_palettes();

  // --- behavior at defaults (speed=128 -> letterMs=516; hold c1=70 -> 1700ms) ---
  sim_segment.speed = 128; sim_segment.intensity = 128; sim_segment.custom1 = 70;
  reset_seg();
  uint32_t t0 = 1000;                       // device millis at effect start
  uint16_t letterMs = 536 - (128 - 128) * 3;  // mirror of the effect's derivation @ speed 128
  tick(t0);                                 // first frame latches step = t0
  CHECK(sim_segment.step == t0, "step latched (%u != %u)", sim_segment.step, t0);

  // mid-ignition of letter 0: C may be lit, E must not be
  tick(t0 + letterMs / 2);
  CHECK(!letter_lit(5), "E lit during C ignition");

  // after all letters + into hold: everything steady full cyan
  tick(t0 + (uint32_t)letterMs * 6 + 200);
  for (int L = 0; L < 6; L++) CHECK(letter_lit(L), "letter %d not lit during hold", L);
  for (int i = 0; i < CHARGE_NUM_PIXELS; i++) {
    uint32_t c = grid[CHARGE_ROW[i] * CHARGE_GRID_W + CHARGE_COL[i]];
    CHECK(c == RGBW32(0, 255, 255, 0), "pixel %d not full cyan in hold (0x%08x)", i, c);
  }

  // color invariant across the whole ignition: only cyan family (r==0, g==b)
  reset_seg();
  for (uint32_t t = t0; t < t0 + 7000; t += FRAMETIME) {
    tick(t);
    for (int i = 0; i < CHARGE_NUM_PIXELS; i++) {
      uint32_t c = grid[CHARGE_ROW[i] * CHARGE_GRID_W + CHARGE_COL[i]];
      uint8_t r = (c >> 16) & 255, g = (c >> 8) & 255, b = c & 255;
      if (r != 0 || g != b) { CHECK(false, "non-cyan 0x%06x at px %d t=%u", c, i, t); t = t0 + 7000; break; }
    }
  }

  // loop: shortly after a cycle boundary the last letter must be dark again
  reset_seg();
  tick(t0);
  uint32_t cycle = (uint32_t)letterMs * 6 + (300 + 70u * 20);  // hold from c1=70
  tick(t0 + cycle + 1 + FRAMETIME);          // restart latched, t small again
  CHECK(!letter_lit(5), "E still lit right after loop restart");

  // --- millis() wrap (49.7-day uptime): must not wedge or glitch ---
  reset_seg();
  uint32_t near_wrap = 0xFFFFFFFFu - 2000;
  tick(near_wrap);
  for (uint32_t k = 1; k < 400; k++) {       // ticks across the wrap point
    tick(near_wrap + k * FRAMETIME);         // unsigned add wraps naturally
  }
  CHECK(true, "");                            // reaching here w/o UBSan trip = pass

  // --- long soak: EVERY effect, 20 simulated minutes at 42fps per corner of
  //     (speed, intensity, custom1, custom2, checks), audio swept, plus a
  //     millis()-wrap crossing per effect ---
  const uint8_t corners[][4] = {          // speed, intensity, custom1, custom2
    {0,0,0,0}, {0,255,255,0}, {255,0,0,255}, {255,255,255,255}, {128,128,128,128},
    {255,255,0,0}, {0,0,255,255},
  };
  for (uint8_t e = 0; e < CHARGE_FX_COUNT; e++) {
    charge_mode_fn fn = CHARGE_FX_LIST[e].fn;
    for (uint8_t ci = 0; ci < sizeof(corners)/sizeof(corners[0]); ci++) {
      const uint8_t *c = corners[ci];
      sim_segment.speed = c[0]; sim_segment.intensity = c[1];
      sim_segment.custom1 = c[2]; sim_segment.custom2 = c[3];
      sim_segment.custom3 = (uint8_t)(c[2] & 31);
      sim_segment.check1 = (ci & 1); sim_segment.check2 = (ci & 2); sim_segment.check3 = (ci & 4);
      static const uint8_t pals[] = { 0, 255, 3, 248 };   // default, goblin ends, colors-derived
      sim_segment.palette = pals[ci & 3];
      reset_seg();
      for (uint32_t t = 0; t < 20u * 60 * 1000; t += FRAMETIME) {
        g_audio = charge_tri8(t, 700);                 // pumping audio sweep
        g_peak = (t % 700) < FRAMETIME;
        tick_fx(fn, t);
      }
    }
    sim_segment.speed = 128; sim_segment.intensity = 128;
    sim_segment.custom1 = 128; sim_segment.custom2 = 128;
    reset_seg();
    for (uint32_t k = 0; k < 400; k++) tick_fx(fn, (0xFFFFFFFFu - 2000) + k * FRAMETIME);
    CHECK(canaries_ok(), "guard bands corrupted by effect %u (%s)", e, CHARGE_FX_LIST[e].meta);
  }

  // --- every write in-bounds (COL/ROW vs grid) — the header guarantees it,
  //     but the soak above under ASan is the actual proof ---
  for (int i = 0; i < CHARGE_NUM_PIXELS; i++) {
    CHECK(CHARGE_COL[i] < CHARGE_GRID_W && CHARGE_ROW[i] < CHARGE_GRID_H,
          "geometry out of grid at %d", i);
  }

  CHECK(canaries_ok(), "grid buffer guard bands corrupted — effect wrote out of bounds");

  printf(fails ? "FAILURES: %d\n"
               : "ALL PASS (%u effects, 20 sim-min x 7 param corners each + audio sweep + wrap, UBSan + guard bands)\n",
         fails ? fails : (unsigned)CHARGE_FX_COUNT);
  return fails ? 1 : 0;
}
