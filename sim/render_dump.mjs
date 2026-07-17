// Dump sampled LED frames + temporal-smoothness metrics for every effect.
// Run after building the node wasm (sh sim/qa.sh builds it):
//   node sim/render_dump.mjs <outdir>
// Output: <outdir>/simdump.json — per effect: 8 routed-LED RGB snapshots at
// spread timestamps + per-frame luminance metrics over the whole run
// (flash events, biggest frame-to-frame jump, lit fraction).
import { readFileSync, writeFileSync } from "node:fs";
import ChargeSim from "./charge_sim_node.js";

const outdir = process.argv[2] || ".";
const M = await ChargeSim();
M._sim_init();
const W = M._sim_grid_w(), H = M._sim_grid_h(), N = M._sim_num_pixels();
const gridPtr = M._sim_grid_ptr() >> 2;
const FRAMETIME = Math.floor(1000 / 42);
const ledmap = JSON.parse(readFileSync(new URL("../wled/word-controller/ledmap.json", import.meta.url)));

// feed the palette registry (same as qa.mjs)
const palData = JSON.parse(readFileSync(new URL("../docs/sign-preview/simulator/wled_palettes.json", import.meta.url)));
const palBuf = M._sim_pal_buf();
palData.fastled.forEach((p16, i) => {
  new Uint32Array(M.HEAPU8.buffer, palBuf, 16).set(p16);
  M._sim_pal_fixed16(6 + i);
});
palData.gradients.forEach((g, i) => {
  M.HEAPU8.set(g.slice(0, 72), palBuf);
  M._sim_pal_gradient(13 + i, Math.min(72, g.length));
});
let customCount = 0;
for (let ci = 0; ci < 3; ci++) {
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
M._sim_pal_counts(customCount, 8);

const SLIDER_KEYS = ["sx", "ix", "c1", "c2", "c3"], CHECK_KEYS = ["o1", "o2", "o3"];
const sliderSet = [v => M._sim_set_speed(v), v => M._sim_set_intensity(v),
  v => M._sim_set_custom1(v), v => M._sim_set_custom2(v), v => M._sim_set_custom3(v)];
const checkSet = [v => M._sim_set_check1(v), v => M._sim_set_check2(v), v => M._sim_set_check3(v)];

function parseMeta(i) {
  const meta = M.UTF8ToString(M._sim_fx_meta(i));
  const secs = meta.split(";");
  const at = secs[0].indexOf("@");
  const defaults = {};
  (secs[4] || "").split(",").forEach(kv => {
    const [k, v] = kv.split("=");
    if (k && v !== undefined) defaults[k.trim()] = +v;
  });
  return { name: at < 0 ? secs[0] : secs[0].slice(0, at), defaults };
}

// synthetic beat like the page (124 bpm kick w/ 45ms attack + accents)
function audioAt(t) {
  const beatMs = 60000 / 124;
  const phMs = t % beatMs;
  const accent = (Math.floor(t / beatMs) % 4 === 0) ? 1.0 : 0.72;
  const atk = Math.min(1, phMs / 45);
  const dec = Math.exp(-Math.max(0, phMs - 45) / 240);
  return [Math.min(255, Math.round(255 * accent * atk * dec) + 18),
          (phMs >= 40 && phMs < 70) ? 1 : 0];
}

const DURATION = 22500;                      // covers a full Premiere loop
const SAMPLE_FRACS = [0.02, 0.14, 0.27, 0.40, 0.55, 0.70, 0.82, 0.94];

const dump = { N, effects: [] };
const fxCount = M._sim_fx_count();
for (let e = 0; e < fxCount; e++) {
  const p = parseMeta(e);
  M._sim_select(e); M._sim_seed(42); M._sim_reset();
  M._sim_set_palette(p.defaults.pal || 0);
  M._sim_set_default_palette(p.defaults.pal || 6);
  M._sim_set_color(0, 0x00ffa000);
  SLIDER_KEYS.forEach((k, ix) => sliderSet[ix](p.defaults[k] !== undefined ? p.defaults[k] : (ix < 2 ? 128 : 0)));
  CHECK_KEYS.forEach((k, ix) => checkSet[ix](p.defaults[k] !== undefined ? p.defaults[k] : 0));

  const led = new Uint32Array(N);
  const sampleAt = SAMPLE_FRACS.map(f => Math.round(DURATION * f / FRAMETIME));
  const samples = [];
  let prevL = null, maxJump = 0, flashes = 0, sumLit = 0, frames = 0, minLit = 1, maxLit = 0;
  let prevLed = null, maxPxJumpFrac = 0;

  for (let f = 0; f * FRAMETIME < DURATION; f++) {
    const t = f * FRAMETIME;
    const [lvl, pk] = audioAt(t);
    M._sim_set_audio(lvl, pk);
    M._sim_tick(t >>> 0);
    const g = M.HEAPU32.subarray(gridPtr, gridPtr + W * H);
    for (let gi = 0; gi < ledmap.map.length; gi++) {
      const li = ledmap.map[gi];
      if (li >= 0) led[li] = g[gi];
    }
    // metrics
    let L = 0, lit = 0, moved = 0;
    for (let i = 0; i < N; i++) {
      const c = led[i], r = (c >> 16) & 255, gg = (c >> 8) & 255, b = c & 255;
      const y = r + gg + b;
      L += y;
      if (y > 24) lit++;
      if (prevLed) {
        const pc = prevLed[i];
        const dy = Math.abs(y - ((((pc >> 16) & 255)) + ((pc >> 8) & 255) + (pc & 255)));
        if (dy > 220) moved++;
      }
    }
    const litFrac = lit / N;
    sumLit += litFrac; frames++;
    if (litFrac < minLit) minLit = litFrac;
    if (litFrac > maxLit) maxLit = litFrac;
    if (prevL !== null) {
      const jump = Math.abs(L - prevL) / (N * 765);        // fraction of absolute max
      if (jump > maxJump) maxJump = jump;
      if (jump > 0.12) flashes++;
    }
    if (prevLed) {
      const mf = moved / N;
      if (mf > maxPxJumpFrac) maxPxJumpFrac = mf;
    }
    prevL = L;
    prevLed = Uint32Array.from(led);
    if (sampleAt.includes(f)) {
      const rgb = [];
      for (let i = 0; i < N; i++) rgb.push(led[i] & 0xFFFFFF);
      samples.push({ tms: t, rgb });
    }
  }
  dump.effects.push({
    name: p.name, samples,
    metrics: {
      meanLitFrac: +(sumLit / frames).toFixed(3),
      minLitFrac: +minLit.toFixed(3), maxLitFrac: +maxLit.toFixed(3),
      maxLumJumpFrac: +maxJump.toFixed(4),
      flashFrames: flashes,
      maxPxJumpFrac: +maxPxJumpFrac.toFixed(3),
    },
  });
  console.log(`${p.name.padEnd(20)} lit ${(sumLit / frames).toFixed(2)} (min ${minLit.toFixed(2)}) ` +
    `maxΔlum ${(maxJump * 100).toFixed(1)}% flashes ${flashes} maxPxΔ ${(maxPxJumpFrac * 100).toFixed(0)}%`);
}
writeFileSync(`${outdir}/simdump.json`, JSON.stringify(dump));
console.log(`wrote ${outdir}/simdump.json`);
