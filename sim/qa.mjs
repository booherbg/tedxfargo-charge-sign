// Full QA of the CHARGE effect suite against the wasm build (node).
// Run via: sh sim/qa.sh   (builds a node wasm, then executes this)
//
// Per effect:
//  META    metadata well-formed: name, 2D flag, smart defaults present
//  DETERM  same seed + same ticks twice -> identical output
//  ALIVE   lights something at defaults; output animates over time
//  CLEAN   never writes a grid cell the ledmap doesn't route to a real LED
//  PARAMS  every declared slider/checkbox changes the rendered output
//  WRAP    survives ticks across the millis() 32-bit wraparound
//  AUDIO   (Pulse) output tracks the audio level
import { readFileSync } from "node:fs";
import ChargeSim from "./charge_sim_node.js";

const M = await ChargeSim();
M._sim_init();
const W = M._sim_grid_w(), H = M._sim_grid_h(), N = M._sim_num_pixels();
const gridPtr = M._sim_grid_ptr() >> 2;
const FRAMETIME = Math.floor(1000 / 42);

const ledmap = JSON.parse(readFileSync(new URL("../wled/word-controller/ledmap.json", import.meta.url)));
const mapped = new Set();
ledmap.map.forEach((v, g) => { if (v >= 0) mapped.add(g); });

// --- feed the palette registry (extracted data + device custom palettes) ---
const palData = JSON.parse(readFileSync(new URL("../docs/sign-preview/simulator/wled_palettes.json", import.meta.url)));
const palBuf = M._sim_pal_buf();
palData.fastled.forEach((p16, i) => {          // ids 6..12
  new Uint32Array(M.HEAPU8.buffer, palBuf, 16).set(p16);
  M._sim_pal_fixed16(6 + i);
});
palData.gradients.forEach((g, i) => {          // ids 13..71
  M.HEAPU8.set(g.slice(0, 72), palBuf);
  M._sim_pal_gradient(13 + i, Math.min(72, g.length));
});
let customCount = 0;
for (let ci = 0; ci < 3; ci++) {               // device palettes -> ids 200,199,198
  try {
    const cp = JSON.parse(readFileSync(new URL(`../wled/backups/palette${ci}.json`, import.meta.url)));
    const bytes = [];
    for (let k = 0; k + 1 < cp.palette.length; k += 2) {
      const v = parseInt(cp.palette[k + 1], 16);
      bytes.push(cp.palette[k], (v >> 16) & 255, (v >> 8) & 255, v & 255);
    }
    M.HEAPU8.set(bytes.slice(0, 72), palBuf);
    M._sim_pal_gradient(200 - ci, Math.min(72, bytes.length));
    customCount++;
  } catch {}
}
M._sim_pal_counts(customCount, 8);             // 8 goblin palettes registered by sim_init
if (palData.names.length !== 72) { console.log("FAIL palette names != 72"); process.exit(1); }

const SLIDER_KEYS = ["sx", "ix", "c1", "c2", "c3"], CHECK_KEYS = ["o1", "o2", "o3"];
const SLIDER_MAX = [255, 255, 255, 255, 31];
const sliderSet = [v => M._sim_set_speed(v), v => M._sim_set_intensity(v),
  v => M._sim_set_custom1(v), v => M._sim_set_custom2(v), v => M._sim_set_custom3(v)];
const checkSet = [v => M._sim_set_check1(v), v => M._sim_set_check2(v), v => M._sim_set_check3(v)];

function parseMeta(i) {
  const meta = M.UTF8ToString(M._sim_fx_meta(i));
  const secs = meta.split(";");
  const at = secs[0].indexOf("@");
  const plist = (at < 0 ? "" : secs[0].slice(at + 1)).split(",");
  const defaults = {};
  (secs[4] || "").split(",").forEach(kv => {
    const [k, v] = kv.split("=");
    if (k && v !== undefined) defaults[k.trim()] = +v;
  });
  return { meta, name: at < 0 ? secs[0] : secs[0].slice(0, at),
           flags: secs[3] || "", defaults,
           sliders: plist.slice(0, 5), checks: plist.slice(5, 8) };
}

function grid() { return M.HEAPU32.subarray(gridPtr, gridPtr + W * H); }
function fnv(acc, g) {
  for (let i = 0; i < g.length; i++) { acc ^= g[i]; acc = Math.imul(acc, 16777619) >>> 0; }
  return acc;
}
// audio: synthetic pump so audio-driven effects have signal during QA
function audioAt(t) { return [Math.round(127 + 127 * Math.sin(t / 111)), (t % 700) < FRAMETIME ? 1 : 0]; }

function run(e, params, frames, t0 = 0, collect = {}) {
  M._sim_select(e); M._sim_seed(42); M._sim_reset();
  const d = params.defaults;
  const palSel = params.over?.pal !== undefined ? params.over.pal : (d.pal || 0);
  M._sim_set_palette(palSel);
  M._sim_set_default_palette(d.pal || 6);
  M._sim_set_color(0, params.color0 !== undefined ? params.color0 : 0x00ffa000);
  SLIDER_KEYS.forEach((k, ix) => sliderSet[ix](
    params.over?.[k] !== undefined ? params.over[k] : (d[k] !== undefined ? d[k] : (ix < 2 ? 128 : 0))));
  CHECK_KEYS.forEach((k, ix) => checkSet[ix](
    params.over?.[k] !== undefined ? params.over[k] : (d[k] !== undefined ? d[k] : 0)));
  let acc = 2166136261 >>> 0, firstHash = null, sawChange = false, maxLit = 0, stray = -1;
  for (let f = 0; f < frames; f++) {
    const t = (t0 + f * FRAMETIME) >>> 0;
    const [lvl, pk] = params.audio ? params.audio(t) : audioAt(t);
    M._sim_set_audio(lvl, pk);
    M._sim_tick(t);
    const g = grid();
    const h = fnv(2166136261 >>> 0, g);
    if (firstHash === null) firstHash = h; else if (h !== firstHash) sawChange = true;
    acc = (acc ^ h) >>> 0; acc = Math.imul(acc, 16777619) >>> 0;
    if (f % 25 === 0) {
      let lit = 0;
      for (let gi = 0; gi < g.length; gi++) {
        if (g[gi]) { lit++; if (!mapped.has(gi) && stray < 0) stray = gi; }
      }
      if (lit > maxLit) maxLit = lit;
    }
  }
  collect.maxLit = maxLit; collect.stray = stray; collect.sawChange = sawChange;
  return acc;
}

const fxCount = M._sim_fx_count();
console.log(`QA: ${fxCount} effects, grid ${W}x${H}, ${N} px, ${mapped.size} mapped cells\n`);
let fails = 0, names = new Set();
const bad = (name, what) => { fails++; console.log(`  FAIL ${what}`); };

for (let e = 0; e < fxCount; e++) {
  const p = parseMeta(e);
  console.log(`[${String(e).padStart(2)}] ${p.name}`);
  // META
  if (!p.name || names.has(p.name)) bad(p.name, `META name empty/duplicate: "${p.name}"`);
  names.add(p.name);
  if (!p.name.startsWith("CHARGE ")) bad(p.name, `META name must start with "CHARGE " (got "${p.name}")`);
  if (!p.flags.includes("2")) bad(p.name, `META flags "${p.flags}" lack 2D marker`);
  if (p.defaults.sx === undefined && p.defaults.ix === undefined)
    bad(p.name, "META no smart defaults (sx/ix) declared");
  for (const [k, v] of Object.entries(p.defaults)) {
    const ki = SLIDER_KEYS.indexOf(k);
    if (ki >= 0 && (v < 0 || v > SLIDER_MAX[ki])) bad(p.name, `META default ${k}=${v} out of range`);
  }
  // DETERM
  const h1 = run(e, { defaults: p.defaults }, 200);
  const h2 = run(e, { defaults: p.defaults }, 200);
  if (h1 !== h2) bad(p.name, "DETERM same seed+ticks gave different output");
  // ALIVE + CLEAN (longer run, defaults)
  const info = {};
  run(e, { defaults: p.defaults }, 420, 0, info);
  if (info.maxLit === 0) bad(p.name, "ALIVE lights nothing at defaults");
  if (!info.sawChange) bad(p.name, "ALIVE output is static (no animation)");
  if (info.stray >= 0) bad(p.name, `CLEAN wrote unmapped grid cell ${info.stray} (no LED there)`);
  // PARAMS: each declared control must change the output
  const declared = [];
  p.sliders.forEach((lab, k) => { if (lab) declared.push([SLIDER_KEYS[k], 0, SLIDER_MAX[k], lab]); });
  p.checks.forEach((lab, k) => { if (lab) declared.push([CHECK_KEYS[k], 0, 1, lab]); });
  for (const [key, lo, hi, lab] of declared) {
    let same = run(e, { defaults: p.defaults, over: { [key]: lo } }, 300) ===
               run(e, { defaults: p.defaults, over: { [key]: hi } }, 300);
    if (same) {
      // param may depend on other state: a palette (Boot's "Letter colors" on
      // Default), other checkboxes (Surge's "Color wave" needs Accumulate), or
      // slow cycles (Surge's wave fires after a full accumulate round) — retry
      // with a palette, every other checkbox on, max rate, and a long window
      const retry = { pal: 35, c1: 255 };
      p.checks.forEach((cl, k) => { if (cl) retry[CHECK_KEYS[k]] = 1; });
      delete retry[key];                       // never override the param under test
      same = run(e, { defaults: p.defaults, over: { ...retry, [key]: lo } }, 1600) ===
             run(e, { defaults: p.defaults, over: { ...retry, [key]: hi } }, 1600);
    }
    if (same) bad(p.name, `PARAMS "${lab}" (${key}) has no effect on output`);
  }
  // WRAP
  try { run(e, { defaults: p.defaults }, 400, (0xFFFFFFFF - 2000) >>> 0); }
  catch (err) { bad(p.name, `WRAP crashed across millis wrap: ${err}`); }
  // PALETTE: palette-aware effects must respond to the native palette system
  const palAware = (M.UTF8ToString(M._sim_fx_meta(e)).split(";")[2] || "") === "!";
  if (palAware) {
    // some effects gate their palette path behind a checkbox (e.g. Lava's
    // Trippy wax) — the palette must matter at defaults OR with checks on
    const checksOn = {};
    p.checks.forEach((lab, k) => { if (lab) checksOn[CHECK_KEYS[k]] = 1; });
    const differs = (overA, overB) => {
      if (run(e, { defaults: p.defaults, over: overA.over, color0: overA.color0 }, 260) !==
          run(e, { defaults: p.defaults, over: overB.over, color0: overB.color0 }, 260)) return true;
      return run(e, { defaults: p.defaults, over: { ...overA.over, ...checksOn }, color0: overA.color0 }, 260) !==
             run(e, { defaults: p.defaults, over: { ...overB.over, ...checksOn }, color0: overB.color0 }, 260);
    };
    if (!differs({ over: { pal: 35 } }, { over: { pal: 41 } }))
      bad(p.name, "PALETTE switching gradient palettes has no effect");
    if (!differs({ over: { pal: 2 }, color0: 0xff0000 }, { over: { pal: 2 }, color0: 0x0000ff }))
      bad(p.name, "PALETTE color-derived palette ignores segment color");
  }
  // AUDIO (audio-driven effects must track level)
  if (p.name === "CHARGE Pulse") {
    const quiet = run(e, { defaults: p.defaults, audio: () => [0, 0] }, 200);
    const loud  = run(e, { defaults: p.defaults, audio: () => [255, 0] }, 200);
    if (quiet === loud) bad(p.name, "AUDIO output ignores the audio level");
  }
  const pa = (M.UTF8ToString(M._sim_fx_meta(e)).split(";")[2] || "") === "!";
  console.log(`  ok — peak lit ${info.maxLit} cells, ${declared.length} params verified${pa ? ", palette-aware" : ""}`);
}

console.log(fails ? `\n${fails} FAILURES` : "\nQA ALL PASS");
process.exit(fails ? 1 : 0);
