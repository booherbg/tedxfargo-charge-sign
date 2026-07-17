# TEDxFargo custom WLED effects — design (2026-07-16)

Geometry-aware custom effects for the CHARGE sign, compiled into one small WLED
usermod. This spec is written to be built from a **clean session** with no
dependence on the conversation that produced it — every load-bearing WLED fact is
stated with a source reference so the builder never guesses.

---

## 1. Goal

A handful of bespoke effects that know what the pixels *are* (which letter, where
in space, where in the wiring chain) — things no stock effect can do because stock
effects only see an anonymous grid. First deliverable: the full build pipeline
proven end-to-end on hardware with **one** effect (the neon boot-up), flashable and
eyeball-verifiable. Everything after is thin additions.

**Non-goals (this spec):** the bolt/board controller (deferred — still being
built), any triggered/event-cued show logic, cross-controller sync, and the
multiplayer letter game. All explicitly out of scope (§12).

---

## 2. Current state (what already exists)

- **The sign — word controller only for now.** 459 WS281x pixels, 6 letters
  C H A R G E, wired as one greedy tube-order chain. Physically a lightning/neon
  aesthetic in electric cyan with yellow/red accents.
- **The device is in 2D matrix mode** via a flashed `ledmap.json` (134×25 grid,
  12 mm cells — committed at `ad19744`, hardware-confirmed). `isMatrix` is true;
  stock 2D effects render in true sign space. ~90% of the 3350 grid cells are `-1`
  gaps (no LED). Controller: Gledopto **GL-C-616WL** (ESP32, **no PSRAM**, ~73 KB
  free heap — this is why heavy 2D effects sometimes deplete RAM).
- **`tools/gen_wiring.py`** already loads `src/parts/word_pixmap.json`, computes
  each pixel's grid (col,row) at `WORD_CELL_MM = 12.0`, and emits the ledmap +
  presets. It is the single source of truth for geometry. We extend it to also
  emit the C header this design needs.
- **`src/parts/word_pixmap.json`** — the wiring truth. `pixels[]`, one per LED, in
  chain order (index 0..458). Fields per pixel: `x`, `y` (physical mm), `letter`
  (`"C".."E"`), `piece` (1..6, physical print piece), `chain` (== array index).
- **Letters are contiguous ranges in chain order** (verified): C 0–61, H 62–142,
  A 143–214, R 215–295, G 296–378, E 379–458. So "letter membership" is just a
  range test — no per-pixel lookup table needed for grouping.
- **Custom palettes on device** (`wled/backups/palette0-2.json`): electric cyan +
  yellow/red lightning accents. These are the effects' default color intent.

---

## 3. Key decisions (with rationale)

1. **2D substrate — keep the ledmap, do NOT switch to a 1D strip.** The user's
   favorite effects (Palette bars sweeping, Hiphotic, Fire-from-both-sides, Meteor,
   Shimmer, PS Vortex) are all *spatial* — color moving through 2D space, letters
   relating to each other. That is exactly what a 2D matrix provides and a 1D strip
   fundamentally cannot (a strip has only chain order, no vertical axis, no
   "across"). Going 1D would mean reimplementing every favorite *and* discarding the
   quality that makes them land. So the device stays 2D; custom effects address
   real LEDs via a baked geometry table + `setPixelColorXY`.
2. **A usermod is the container; the effects are ordinary custom effects.** New
   effect logic must be compiled in — presets/playlists/JSON can only recombine
   existing effects. The two homes are core `FX.cpp` (scatters our code through
   core, fights every WLED update) or a usermod (isolated in `usermods/tedxfargo/`,
   registers via `strip.addEffect()` in `setup()`, and is the natural home for the
   shared geometry helpers and the future letter-coloring HTTP endpoint). Usermod
   wins on every axis. It's lightweight: a folder + a small class + one build flag.
3. **Ambient loop.** Effects live in normal playlists next to stock effects. No
   trigger, cue, or sync layer. The "hero moment" (boot-up → strike → burst) is a
   single phased effect that loops, not an event system.
4. **Base repo: direct clone of `GLEDOPTO/WLED` @ `gledopto-16.0.1`.** This is the
   exact firmware already running on the sign — stock WLED 16.0.1 plus a thin
   Gledopto config commit (board env, onboard mic, branding). Cloning it directly
   guarantees we build against a known-good config and only add our usermod.
   (Fork-strategy cleanup — rebasing onto a clean WLED fork — is deferred; "rectify
   later.") Every API fact below was verified against WLED 16.0.1, which this
   branch is.

---

## 4. Architecture

```
src/parts/word_pixmap.json ──► tools/gen_wiring.py ──► usermods/tedxfargo/charge_geometry.h
                                                              │
                                                              ▼
        usermods/tedxfargo/usermod_tedxfargo.h  (Usermod class)
          • setup(): strip.addEffect(255, &mode_fn, PSTR("meta")) per effect
          • owns geometry helpers over charge_geometry.h (the 5 primitives)
          • (later) registers the letter-coloring HTTP endpoint
                                                              │
             mode functions: mode_charge_bootup(), ...        │  each ~20 lines
                                                              ▼
        platformio env GL-C-616WL:  custom_usermods = tedxfargo
                                                              │
                                                              ▼
                              build ──► flash ──► effect appears in WLED effect list
```

Every effect follows one uniform pattern: iterate the 459 pixels, compute a color
from the baked fields (letter / x / y / height / chain), and place it with
`SEGMENT.setPixelColorXY(col, row, color)`. The ledmap routes (col,row) → the
physical LED. **Effects assume a full-canvas 2D segment anchored at (0,0)** (the
default segment), so segment-relative XY equals absolute grid XY.

---

## 5. The baked geometry header (`charge_geometry.h`)

Emitted by `gen_wiring.py`, indexed by chain index `i` (0..458). All arrays
`PROGMEM`, ~3 KB flash total.

```c
// Generated by tools/gen_wiring.py — DO NOT EDIT. Regenerate with the ledmap so
// COL/ROW stay in sync with the flashed ledmap.json (same WORD_CELL_MM).
#define CHARGE_NUM_PIXELS  459
#define CHARGE_NUM_LETTERS 6
#define CHARGE_GRID_W      134   // must equal the active ledmap width
#define CHARGE_GRID_H      25    // must equal the active ledmap height

// enum order = chain order of first appearance: C,H,A,R,G,E
const uint8_t  CHARGE_LETTER[459] PROGMEM = { 0,0,...,5 };  // 0=C .. 5=E
const uint8_t  CHARGE_COL[459]    PROGMEM = { ... };        // grid col 0..133
const uint8_t  CHARGE_ROW[459]    PROGMEM = { ... };        // grid row 0..24 (0=top)
const uint8_t  CHARGE_HEIGHT[459] PROGMEM = { ... };        // 0..255, 0 = base of its letter, 255 = top
const uint8_t  CHARGE_XNORM[459]  PROGMEM = { ... };        // 0..255 x across whole sign (left..right)

// letters are contiguous in chain order → ranges, not a lookup
const uint16_t CHARGE_LETTER_START[6] PROGMEM = { 0, 62, 143, 215, 296, 379 };
const uint16_t CHARGE_LETTER_COUNT[6] PROGMEM = { 62, 81, 72, 81, 83, 80 };
```

Derivations (all in `gen_wiring.py`, from the same data that builds the ledmap):
- `CHARGE_COL/ROW[i]` = `gen_wiring`'s existing grid mapping at `WORD_CELL_MM`
  (`gx = int((x-ox)/cell)`, `gy = int((h_mm-(y-oy)-eps)/cell)`). **Must match the
  flashed ledmap** — regenerate both together.
- `CHARGE_HEIGHT[i]` = normalize `y` within pixel i's letter's [ymin,ymax] → 0..255,
  base=0. (Physical y increases upward; base = smallest y.)
- `CHARGE_XNORM[i]` = normalize `x` across the whole sign [xmin,xmax] → 0..255.
- `CHARGE_LETTER_START/COUNT` computed from `letter` runs (assert contiguity).

**Coupling note:** the header's COL/ROW and the flashed `ledmap.json` are two
outputs of the same mapping. If `WORD_CELL_MM` changes, regenerate both and
re-flash both. `gen_wiring.py` emits them in one run — keep it that way.

---

## 6. The five primitives (helpers on the usermod class)

Thin accessors over the header. This is the entire shared surface every effect uses.

1. **Letter groups** — `for (i = LETTER_START[L]; i < LETTER_START[L]+LETTER_COUNT[L]; i++)`.
   Powers: boot-up, per-letter Pac-Man, per-letter Fireworks, letter flicker.
2. **Tube order within a letter** — chain order *is* tube order (wiring is greedy
   along the neon path), so iterating a letter's range walks its tube. Powers:
   tube-trace, flames climbing into a letter.
3. **Height within letter** — `CHARGE_HEIGHT[i]` (0=base). Powers: flames rising,
   bottom-up fills.
4. **X across the sign** — `CHARGE_XNORM[i]`. Powers: jet-stream / lightning /
   meteor sweeps, with letters as spatial waypoints.
5. **Audio** — the AudioReactive usermod is compiled into this build (§10). Effects
   read its shared FFT data (`um_data` bins) for reactive flames. (Access pattern:
   the standard `usermods.getUMData(&um_data, USERMOD_ID_AUDIOREACTIVE)` handshake —
   verify signature against the audioreactive usermod at build time.)

Place with `SEGMENT.setPixelColorXY(CHARGE_COL[i], CHARGE_ROW[i], color)`.

---

## 7. The usermod

Scaffold by **copying an in-repo template** so registration boilerplate is exact:
`usermods/EXAMPLE/` (general) and `usermods/PS_Comet/` (a usermod that adds an
effect — the closest reference). Do not hand-write the registration macro from
memory; copy it.

```
usermods/tedxfargo/
  charge_geometry.h        # generated (§5)
  usermod_tedxfargo.h      # Usermod subclass
```

`usermod_tedxfargo.h` responsibilities:
- Include `charge_geometry.h`.
- Define each effect's `mode_*` function + its metadata string (§8).
- In `setup()`: `strip.addEffect(255, &mode_charge_bootup, _data_CHARGE_BOOTUP);`
  once per effect. `id == 255` means "append to the next free slot" (verified,
  `FX.cpp` `addEffect`). Returns the assigned id, or 255 on failure — log if 255.
- Self-register with the same static-instance + registration macro the template
  uses.

Enable it in the board env: `custom_usermods = tedxfargo` (§10; the Gledopto env
enables the mic via a legacy define, so ours is the only `custom_usermods` entry).
The `pre:pio-scripts/load_usermods.py` script includes it from the folder name.

---

## 8. Writing an effect (verified API)

A WLED effect is a free/static function `void mode_x()` (WLED 16.0.1 —
`typedef void (*mode_ptr)()`; older WLED returned `uint16_t`). It reads/writes
through the `SEGMENT` macro; frame timing is derived from `strip.now`
(frame-coherent millis) inside the effect, not from a return value.

```c
static const char _data_CHARGE_BOOTUP[] PROGMEM = "CHARGE Boot@Speed,Flicker;;!;2";

void mode_charge_bootup() {
  // strip.now = frame-coherent millis (drive time-based animation from this)
  // SEGENV.step / .aux0 = free per-segment state; SEGENV.call = frame counter
  // SEGMENT.speed, SEGMENT.intensity = the two sliders (0..255)
  // ... compute per pixel, then:
  //   SEGMENT.setPixelColorXY(pgm_read_byte(&CHARGE_COL[i]),
  //                           pgm_read_byte(&CHARGE_ROW[i]), color);
  // no return (void)
}
```

**Metadata `@`-string format** (from `FX.cpp` `_data_FX_MODE_*`, verified examples):
`"Name@slider1,slider2,...;color1,color2,...;palette;flags;defaults"`
- `!` = use the default label (Speed, Intensity, `!` color = primary, etc.).
- Empty slot = hide that control.
- `flags`: `1`=offer in 1D, `2`=offer in 2D, `12`=both. **Ours use `2`** (we call
  `setPixelColorXY`, so they must be 2D-capable / offered in 2D mode).
- `defaults` (optional): e.g. `sx=128,ix=200,pal=6`.
- Real references: `"Meteor@!,Trail,,,,Gradient,,Smooth;;!;1"`,
  `"Fireworks@,Frequency;!,!;!;12;ix=192,pal=11"`. Copy the shape from the closest
  stock effect.

Verified API surface (all in the clean WLED 16.0.1 checkout):
| Need | Symbol | Source |
|---|---|---|
| Register an effect (append) | `strip.addEffect(255, fn, meta)` | `FX.h` decl / `FX.cpp` body |
| Current segment | `SEGMENT` macro | `FX.h` (`*strip._currentSegment`) |
| Place a 2D pixel | `SEGMENT.setPixelColorXY(x,y,color)` | `FX.h` |
| Per-segment runtime state | `SEGENV.call/.step/.aux0/.aux1`, `SEGENV.allocateData()` | `FX.h` |
| Sliders / options | `SEGMENT.speed/.intensity/.custom1..3/.check1..3` | `FX.h` |
| Palette color | `SEGMENT.color_from_palette(...)` | `FX.cpp` |
| Frame timing | `strip.now` (frame-coherent millis); mode fn is `void` | `FX.h` / `FX_fcn.cpp` |
| Is this segment 2D | `SEGMENT.is2D()`, `.virtualWidth()`, `.virtualHeight()` | `FX.h` |

---

## 9. First cut — "neon boot-up" (the deliverable to flash and see)

**What the first plan builds:** the whole pipeline — `gen_wiring.py` emits
`charge_geometry.h`; the `usermods/tedxfargo/` scaffold; one registered effect; the
`GL-C-616WL` env with the usermod enabled; a successful build; flash — proven by
one effect on the wall.

**Effect: "CHARGE Boot".** The sign ignites like a neon sign warming up.
- Letters light in chain order C → H → A → R → G → E, one at a time, paced by
  `Speed`.
- Each igniting letter flickers on — a few random on/off dips (amount = `Flicker`
  / `intensity`) before settling to steady cyan (the CHARGE electric color).
- Once all six are lit, hold briefly, then loop (re-ignite).
- Primitives used: **1** (letter groups) + light use of flicker randomness. Color:
  fixed electric cyan for v1 (palette wiring can come later).

**Why this is first light:** it exercises letter grouping *and* placement, and it's
trivially falsifiable — if letters light **in the right places and the right
order**, the entire chain (header correctness, COL/ROW ↔ ledmap agreement,
`addEffect` registration, `setPixelColorXY` routing, the build/flash) is proven at
once. If a letter lights in the wrong spot, the geometry header is wrong; if
nothing lights, registration/build is wrong. Clean signal either way.

**Verification (definition of done for cut 1):**
1. Build the `GL-C-616WL` env succeeds; "CHARGE Boot" appears in the effect list.
2. On hardware: selecting it makes the six letters ignite in order, in their
   correct physical positions, with visible flicker, then hold and loop.
3. Stock 2D effects still work (usermod didn't disturb the matrix).

---

## 10. Build & flash

**Base:** direct clone of `GLEDOPTO/WLED`, branch `gledopto-16.0.1` — the exact
build on the sign. Do our work on a new branch off it. `[env:GL-C-616WL]` already
exists there and already configures the board: `extends = esp32_eth`, relay
GPIO18, button GPIO17, data pins 16 & 2, Ethernet (`WLED_ETH_DEFAULT=13`), and the
onboard PDM mic via `${mic_pdm.build_flags}` (`-D UM_AUDIOREACTIVE_ENABLE`,
I2S SD=32 WS=15). We do **not** recreate any of that.

**Only env change — enable our usermod.** Add one line to `[env:GL-C-616WL]`:

```ini
custom_usermods = audioreactive tedxfargo
```

Notes:
- **`audioreactive` MUST be relisted** (corrected 2026-07-16 during the build,
  verified against the checkout): the parent `[env:esp32_eth]` sets
  `custom_usermods = audioreactive`, and defining the option in the child env
  REPLACES the inherited value — `custom_usermods = tedxfargo` alone silently
  drops the audioreactive usermod (mic + all AR effects gone). The env's
  `-D UM_AUDIOREACTIVE_ENABLE` does *not* compile the usermod in; in 16.0.1 it
  only flips the usermod's boot-time `enabled` default (audio_reactive.cpp).
- The real 459-LED count comes from the device config already on the controller —
  nothing to set in the env.
- Flash: `pio run -e GL-C-616WL -t upload` (USB) or OTA. Back up config + presets
  first (WLED UI → Backup).

**Toolchain:** VS Code + PlatformIO, or `pio run -e GL-C-616WL`.

---

## 11. Effect backlog (post-cut-1, each a thin function over §6)

Grouped by the primitive they lean on. Build/iterate in roughly this order.

- **Per-letter (prim 1,2):** per-letter Pac-Man; per-letter Fireworks (TedX
  colors); letter flicker (blue ↔ TedX morph); tube-trace comet.
- **Base-up + audio (prim 1,3,5):** flames at each letter's base, rising into the
  letter, height/energy driven by that letter's audio band; over a solid / gradient
  / slowly-rotating palette background.
- **Cross-sign sweeps (prim 4):** jet-stream pulse (burning edge sweeping across all
  letters, red bg / blue-yellow front); lightning that forks across the letters;
  meteor variants.
- **Composited:** sparkle / "electrical" layer (popcorn-style) over a palette field
  — mirrors the segment-overlay look the user already likes, as one effect.
- **Hero narrative (composes prim 1,4):** boot-up → hold → pause → lightning strike
  through all six letters → multicolor 2D burst finale → reset → loop.

The six stock 2D keepers (Hiphotic, Palette, PS Vortex, Shimmer+transpose, Fire
2012 both-sides, Meteor) stay as-is in playlists — no work.

**Letter-coloring HTTP app (later):** a usermod web endpoint that colors pixels by
`CHARGE_LETTER[i]` (zero bleed, unlike 2D rectangles). Lives in this usermod.

---

## 12. Out of scope

- **Bolt/board controller** — still being physically built; its geometry header,
  zones, and effects come later (the pattern here ports directly).
- **Multiplayer letter-completion game** — a networked, stateful, multi-client app,
  not an effect. Separate project.
- **1D device mode** — rejected (§3.1).
- **Triggered/cued show control & cross-controller sync** — ambient loop only.

---

## 13. Risks, gotchas, assumptions to verify at build start

- **Header ↔ ledmap sync.** COL/ROW must match the flashed ledmap grid. Both come
  from `gen_wiring.py` at `WORD_CELL_MM=12`; regenerate and re-flash together.
- **Ledmap byte-format gotcha (already handled, keep handled).** WLED finds the map
  with a raw byte search for `"map":[` — a space after the colon loads zero cells
  silently. `gen_wiring.py` already dumps compact + asserts; `tools/test_wled_ledmap.py`
  guards it. Not our code to touch, but don't regress it.
- **RAM.** Custom effects on the 459-real-LED set are light (iterate 459, one
  `setPixelColorXY` each — no big buffers). Safe on the 73 KB heap. Only avoid
  allocating a full W×H shadow buffer.
- **Usermod-enable.** `custom_usermods = audioreactive tedxfargo` — audioreactive
  must be relisted because setting the option in `[env:GL-C-616WL]` replaces the
  value inherited from `[env:esp32_eth]` (see §10 note; the original claim here
  was wrong and was corrected during the build).
- **Audio data access.** The `um_data` handshake signature — verify against the
  audioreactive usermod in the checkout before writing flame effects (not needed
  for cut 1).
- **Segment assumption.** Effects assume a full-canvas 2D segment at origin. If a
  preset uses a sub-segment, XY is segment-relative — document this for effect users.
- **`addEffect` returns 255 on failure** (list full / id clash). Log it in `setup()`.

---

## 14. Verification & testing

- **Unit-ish (host):** extend `tools/test_wled_ledmap.py` or add a small check that
  `charge_geometry.h` is internally consistent — letter ranges contiguous and
  covering 0..458, COL/ROW within grid bounds, every pixel's COL/ROW equals the
  ledmap's position for that physical index (header ↔ ledmap agreement).
- **On hardware (cut 1):** the boot-up acceptance in §9.
- **Regression:** stock 2D effects still render correctly after flashing the usermod
  build (the matrix/ledmap path is untouched).

---

## 15. Build order (for the implementation plan)

1. `gen_wiring.py`: emit `usermods/tedxfargo/charge_geometry.h` (+ host consistency
   check).
2. Scaffold `usermods/tedxfargo/` from the `EXAMPLE`/`PS_Comet` template; empty
   `setup()` that registers nothing yet; get it building + enabled in the env.
3. Add `mode_charge_bootup` + metadata; register in `setup()`.
4. Build `GL-C-616WL`, flash, run the §9 acceptance.
5. Then iterate the §11 backlog, one thin function at a time.
