# TEDxFargo CHARGE — Firmware & Effects Handoff (2026-07-17)

**What this is:** the custom-effects subsystem, written to be picked up from a
clean session. 16 geometry-aware WLED effects run on the sign's word controller,
developed and QA'd in a bit-exact browser simulator, **flashed and confirmed on
hardware 2026-07-17**. The physical build is covered by `docs/HANDOFF.md`;
design rationale in `docs/superpowers/specs/2026-07-16-tedxfargo-effects-design.md`.

## 0. State at a glance
- **On the wall:** all effects working after OTA. 16 registered (Raider shelved
  behind `CHARGE_ENABLE_RAIDER`). Flash 85.4% of the 1.5 MB OTA slot — watch
  headroom as effects grow.
- **Two repos:** this one is the source of truth; the WLED clone
  (`~/workspace/WLED-charge`) is **disposable** — `sh tools/setup_wled.sh
  [--build]` rebuilds it from nothing (pins base commit `0e009863` of
  GLEDOPTO/WLED @ gledopto-16.0.1, patches the ini, syncs the usermod).
- **Everything lives in** `wled/usermods/tedxfargo/` + `sim/` + one ini line.
  WLED core is never modified.

## 1. The one-source-of-truth architecture
```
tools/gen_wiring.py ──► charge_geometry.h (PROGMEM tables: letter/col/row/height/xnorm
                        per chain index; letters are contiguous chain ranges)
wled/usermods/tedxfargo/charge_fx.h   ◄── ALL effect logic. No WLED includes.
        │                                  Compiled into BOTH targets:
        ├── tedxfargo.cpp + wled.h  ──► firmware (usermod; also registers the
        │                                8 goblin palettes as native usermod
        │                                palettes, IDs 255..248)
        └── sim/sim_main.cpp + sim/wled_shim.h ──► wasm simulator
```
The shim's fidelity tiers (in order): (1) **compile the real thing** —
`sim/vendor/fastled_slim.{h,cpp}` vendored byte-for-byte from the checkout;
(2) **verbatim ports with the source cited** — color_fade, color_blend,
ColorFromPalette, color_from_palette, loadPalette, allocateData; (3)
**documented approximations** — seeded PRNG, hash-based Random-Cycle palette.
Palette DATA is extracted from source by `sim/extract_palettes.py`, never
transcribed. **On WLED upgrade: re-vendor fastled_slim, re-run the extractor,
re-diff every cited port.**

## 2. Daily workflows
```bash
python3 sim/serve.py                  # sim at localhost:8000/sign-preview/simulator/
                                      #   (no-store headers — ALWAYS use this server;
                                      #    3 different stale-cache bugs died here)
sh sim/build.sh                       # rebuild wasm + refresh sim data files
sh sim/qa.sh                          # full QA (must stay green; see §4)
sh sim/test_native.sh                 # UBSan soak, 16 fx × 7 param corners × 20 min
sh tools/setup_wled.sh --build        # firmware build (also re-syncs the usermod)
node sim/render_dump.mjs DIR && python3 sim/render_sheets.py DIR
                                      # frame dumps + PNG contact sheets — LOOK at
                                      # them; visual review caught ~15 real issues
python3 tools/test_charge_geometry.py # geometry ↔ ledmap agreement (after regen)
```
**OTA:** upload `~/workspace/WLED-charge/build_output/release/WLED_16.0.1_GL-C-616WL.bin`
at `http://<device-ip>/update`. Via the device AP you must first uncheck the
same-subnet OTA guard (Config → Security & Updates). USB fallback:
`pio run -e GL-C-616WL -t upload`. Config/presets/ledmap survive OTA.

## 3. Hardware truths (each cost real debugging)
1. **Effects assume the clean full-canvas segment** — one segment, 0,0→134,25,
   grouping 1, spacing 0, reverse/mirror/transpose OFF. The device had
   reverse+spacing from an old preset → letters reversed + every-other-LED
   dark. Normalize in the UI, save as the boot preset.
2. **WLED recycles effect data buffers without zeroing.** Stateful effects
   (Pac-Man, Ants, Gravity tube-fall) MUST use magic-byte init guards
   (0x9C / 0xA7 / 0x6B) — `inited == 1` trusts garbage. The sim's zeroed pool
   cannot reproduce this class; only hardware shows it.
3. **WLED-macro collisions:** FX.h defines WHITE, GREY, RED, ORANGE, PINK…
   Locals with those names break ONLY the firmware build (the shim compiled
   fine both times it happened). Prefer `duskC`-style names.
4. **WLED's web UI caches effect metadata keyed by version** — both firmwares
   say 16.0.1, so hard-refresh the device UI after flashing or new
   sliders/checkboxes silently don't appear.
5. **Timeline effects must anchor to effect start** (`SEGENV.step` latch),
   never `now % total` — or selecting the effect joins mid-scene.
6. Effect **indices shift** when the registry changes → re-save any presets
   that reference effect IDs after flashing.

## 4. Effect-code rules (QA enforces most)
- Names start with **"CHARGE "** (QA-enforced). Metadata carries smart
  defaults; palette-aware effects declare `!,!,!;!` + a `pal=` default and keep
  **palette Default = the classic look** (Boot cyan, Lava classic, Storm
  electric…). `custom3` is WLED's 5-bit slider (0..31).
- **Frame-coherent randomness:** persistent choices come from `charge_hash()`
  of stable inputs; `hw_random8()` is for ephemeral flicker only. Timers
  compare wrap-safe: `(int32_t)(now - deadline) >= 0`.
- **Palette blend zones:** WLED palettes resample to 16 entries and always
  interpolate between adjacent entries, so hard-banded palettes (TEDx) have
  ~16/255-wide washed transitions. Deliberate color *picks* go through
  `charge_cfp_vivid()` (nudges to the nearest saturated hue);
  `charge_letter_colors()` also keeps adjacent letters visibly different.
  Continuous gradients (Flow trail, Dreamwave field) stay raw on purpose.
- Brightness falloffs: prefer **hold-bright quadratics** (`255 - t²/256`) —
  linear/ease-out curves read dim on the wall (Comet tails, firework sparks).
- QA (`sim/qa.mjs`) checks: name prefix, defaults, determinism, liveness, no
  writes to unmapped cells, **every declared param changes output** (with a
  dependent-param retry), millis-wrap survival, palette response, audio
  response. Add effects ⇒ keep it green; it has caught real bugs (undeclared
  Tube fall checkbox, invisible ants).

## 5. The 16 effects (30-second tour)
Ambient: **Boot** (neon ignition; Electrify lightning, per-letter palette
colors), **Surge** (packets + arc-flashes; Accumulate → Color wave finale),
**Comet**, **Marquee** (Color-mode slider), **Neon Morph**, **Lava**, **Flow**
(synced palette comets), **Dreamwave** (letters take turns "speaking").
Games/sims: **Pac-Man** (real rules, portals from tube geometry, magic-pellet
2D shockwaves), **Ants** (colony economy — piles = palette colors, rich
colonies glow their letter), **Gravity** (bounce + Tube-fall marble drain).
Particles: **Fireworks** (PS-1D-style physics; Grand dial c3 = whole-sign
showpiece w/ flood), **Drip**, **Pulse** (audio: device mic / sim beat+mic).
Stories: **Premiere** (~22 s film: right-side spotlight sweep → fills →
lightning → full-color blast) and **Storm** (rain forever; stepped-leader
lightning loads letters C→E; barrage + shockwave finale).

## 6. Where discussion lives
- Spec: `docs/superpowers/specs/2026-07-16-tedxfargo-effects-design.md`
  (§10 corrected: `custom_usermods = audioreactive tedxfargo` — the child env
  REPLACES the inherited value; the legacy define never compiled the mic in).
- Plan (executed through hardware acceptance):
  `docs/superpowers/plans/2026-07-16-tedxfargo-effects-firstcut.md`.
- Session memory: `memory/charge-led-sign-project.md` +
  `memory/wled-firmware-build-gotchas.md` (pio needs Python ≤3.13; pipx venv
  needs ensurepip).
- Deferred: bolt/board controller effects (same pattern ports directly),
  Raider revival, show control/sync, the multiplayer letter game.
