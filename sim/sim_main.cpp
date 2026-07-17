// Emscripten entry for the CHARGE effect simulator.
// Compiles the EXACT charge_fx.h the firmware ships (symlinked/relative
// include), against the wled_shim.h API port. The JS harness drives time,
// sliders, and reads the grid framebuffer + geometry tables from wasm memory.
#include "wled_shim.h"
#include "../wled/usermods/tedxfargo/charge_fx.h"

#include <emscripten/emscripten.h>

static uint32_t grid_buf[CHARGE_GRID_W * CHARGE_GRID_H];
static int cur_fx = 0;

extern "C" {

EMSCRIPTEN_KEEPALIVE int sim_grid_w() { return CHARGE_GRID_W; }
EMSCRIPTEN_KEEPALIVE int sim_grid_h() { return CHARGE_GRID_H; }
EMSCRIPTEN_KEEPALIVE int sim_num_pixels() { return CHARGE_NUM_PIXELS; }
EMSCRIPTEN_KEEPALIVE uint32_t* sim_grid_ptr() { return grid_buf; }

// geometry tables — same arrays the firmware bakes in; JS reads them from HEAP
EMSCRIPTEN_KEEPALIVE const uint8_t*  sim_tab_letter() { return CHARGE_LETTER; }
EMSCRIPTEN_KEEPALIVE const uint8_t*  sim_tab_col()    { return CHARGE_COL; }
EMSCRIPTEN_KEEPALIVE const uint8_t*  sim_tab_row()    { return CHARGE_ROW; }
EMSCRIPTEN_KEEPALIVE const uint8_t*  sim_tab_height() { return CHARGE_HEIGHT; }
EMSCRIPTEN_KEEPALIVE const uint8_t*  sim_tab_xnorm()  { return CHARGE_XNORM; }

EMSCRIPTEN_KEEPALIVE int sim_fx_count() { return CHARGE_FX_COUNT; }
EMSCRIPTEN_KEEPALIVE const char* sim_fx_meta(int i) {
  return (i >= 0 && i < CHARGE_FX_COUNT) ? CHARGE_FX_LIST[i].meta : "";
}

// Mirrors WLED's effect-change reset: runtime state zeroed, UI fields kept.
EMSCRIPTEN_KEEPALIVE void sim_reset() {
  sim_segment.step = 0;
  sim_segment.call = 0;
  sim_segment.aux0 = 0;
  sim_segment.aux1 = 0;
  sim_segment.fill(BLACK);
}

EMSCRIPTEN_KEEPALIVE void sim_select(int i) {
  if (i >= 0 && i < CHARGE_FX_COUNT && i != cur_fx) { cur_fx = i; }
  sim_reset();
}

EMSCRIPTEN_KEEPALIVE void sim_set_speed(int v)     { sim_segment.speed = (uint8_t)v; }
EMSCRIPTEN_KEEPALIVE void sim_set_intensity(int v) { sim_segment.intensity = (uint8_t)v; }
EMSCRIPTEN_KEEPALIVE void sim_set_custom1(int v)   { sim_segment.custom1 = (uint8_t)v; }
EMSCRIPTEN_KEEPALIVE void sim_set_custom2(int v)   { sim_segment.custom2 = (uint8_t)v; }
EMSCRIPTEN_KEEPALIVE void sim_set_custom3(int v)   { sim_segment.custom3 = (uint8_t)(v > 31 ? 31 : v); }  // 5-bit in WLED
EMSCRIPTEN_KEEPALIVE void sim_set_check1(int v)    { sim_segment.check1 = v != 0; }
EMSCRIPTEN_KEEPALIVE void sim_set_check2(int v)    { sim_segment.check2 = v != 0; }
EMSCRIPTEN_KEEPALIVE void sim_set_check3(int v)    { sim_segment.check3 = v != 0; }
EMSCRIPTEN_KEEPALIVE void sim_seed(uint32_t s)     { sim_rng_state = s ? s : 1; }

// audio glue for charge_fx.h — the page feeds a level each frame
// (synthetic beat or real browser microphone)
static uint8_t g_audio = 0, g_peak = 0;
EMSCRIPTEN_KEEPALIVE void sim_set_audio(int level, int peak) {
  g_audio = (uint8_t)(level < 0 ? 0 : (level > 255 ? 255 : level));
  g_peak = peak ? 1 : 0;
}

// One WLED service pass: strip.now <- now_ms, run the mode fn, call++.
EMSCRIPTEN_KEEPALIVE void sim_tick(uint32_t now_ms) {
  strip.now = now_ms;
  CHARGE_FX_LIST[cur_fx].fn();
  sim_segment.call++;
}

EMSCRIPTEN_KEEPALIVE void sim_init() {
  sim_segment.W = CHARGE_GRID_W;
  sim_segment.H = CHARGE_GRID_H;
  sim_segment.buf = grid_buf;
  sim_reset();
}

}  // extern "C"

uint8_t charge_audio() { return g_audio; }
uint8_t charge_audio_peak() { return g_peak; }
