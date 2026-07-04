# Locked specs (validated)

Finalized, print-validated parameters for the **TEDxFargo CHARGE** neon-sign replica.
Change only with a new test. Full onboarding context: `docs/HANDOFF.md`.

## Bullet pixel — the hardware everything keys off
- dome **Ø8**, barrel **Ø12**, flange **Ø13.6 × 2mm**, dome-tip → flange **5.5mm**
- dome protrusion (`dome_clear`) = **4.0mm**; plate bore (`pixel_through`) = **12.3mm**
- calibrated press-fit collar `assets/bullet-collar.stl` (bore ~Ø12.19)
- 24V; **own 300, can buy up to 600**; 150W/24V PSU

## Diffusion recipe ✅ THE WIN
Cross-section = **white reflective shell + ~15mm air gap + chunky clear lens with a BAKED fuzzy top.**
- **Fuzzy winner = V3**: ~**1.5mm** bump cells, ~**0.8mm** bump height (`src/parts/fuzz_v3.dat`,
  regen `tools/make_fuzz.py OUT 1.5 0.8`). Best balance of texture + brightness; **hides individual
  LEDs**; pure heightfield → **no supports, no spaghetti**. (Bambu fuzzy-skin can't texture tops, so it's baked.)
- **Top surface pattern: Concentric.** Print **lens-UP**.
- **White interior recycles light** (fewer LEDs, more even). **Never a dark interior** facing the LEDs.
- Print settings (Adafruit-derived): 0.16mm layer · 0.42 line · 2 walls · 10% gyroid · 6 top/bottom ·
  supports off · brim · bridge fan on.

## LETTER cross-section — 3 colors (filament change)
1. **BLACK** — base/tile (billboard negative space) + channel outer structure.
2. **WHITE** — a couple layers lining the channel **rear (floor) + inner walls** (reflector).
3. **CLEAR** — chunky lens on top with the **V3 baked fuzzy skin**.

## Letters — faithful widened neon outline
- **Faithfully replicate the logo's hollow neon-outline letters** (`assets/svg/{C,H,A,R,G,E,CHARGE}.svg`,
  from EPS via `tools/eps2svg.sh`). **Both neon lines lit.**
- **Widen each neon tube +3mm/side → ~18mm channel** so the Ø12 pixel + collar fit; the hollow-outline
  look is preserved (verified in render).
- **NO letter splitting.** Cap height **270mm** — **rotate the wide letters 90°** so their width runs
  along the 320mm bed axis (at 270mm the widest letter H is ~320mm = the full bed; heights fit easily).
  Sign ≈ **1.6m** wide. (Absolute max ~310mm, but that splits ~5 of 6 letters for +40mm — not worth it.)
- **Pixel pitch ~17mm (TIGHT — chosen)** for a smooth "solid tube" glow → CHARGE + bolt ≈ **~510 pixels**
  at 270mm cap. Buy up to 600 (own 300 + 300 more). (Sparser ~32mm ≈ 270px is the fallback if budget bites.)
- Pixel placement needs a **tube-centerline extractor** (skeletonize each letter) — **TODO tooling.**

## Bolt lens fit ✅ printed & snapped — superseded by the INTEGRATED lens
- `bolt_lip_clear = -0.2` → lip Ø18.2 into the 18.0 channel (0.2mm interference). Material-robust
  (clear PETG + clear PLA). Dialed via `lens_fit_*` slices. The bolt is a **solid-stroke** channel;
  letters use the same channel construction along the neon path.
- **CURRENT (2026-07-02): the lens is co-printed** (`bolt_lens_integrated` in `src/bolt.scad`,
  print `stl/bolt2_2color.3mf`): welded roof + baked V3 fuzzy top, printed lens-UP in use
  orientation — no flip, no mirror, no press-fit. The -0.2 fit stays locked for any future
  separate-lens part. ALL-PETG build (same-material welds; settings-based haze levers dropped —
  tweaks proved unnoticeable; texture is baked geometry).
- **Slicing note (user-verified):** the baked fuzzy top staggers where top/bottom shells land in
  the thin lens → one mid-lens layer shows small "internal island" artifacts (a map of the tallest
  bumps). **Fix: bottom shell layers +1** (or lens infill 100%). Harmless either way — internal,
  hidden by the frosted top.

## Pixel clearance (matrix) ✅ collision-verified
- `led_void = 14.0`, `led_clear = 2.5`, masks on flared floor legs. `src/parts/lens_pixel_collision.scad`.

## Print orientation & support
- Everything prints **lens-up / plate-down, NO supports.** Chiral flip-to-use parts must be pre-mirrored
  (see the chiral-flip note) — but letters/testbox print in use-orientation, so it's moot for them.

## Bed envelope ✅ VALIDATED in Bambu Studio (2026-07-03)
- H2D dual-nozzle ("left/right nozzle only" side bands): the **both-nozzle zone fits the
  worst-case piece 316 × 295** placed 295-across / 316-deep — confirmed by placing
  `stl/bedcheck_316x295.stl` (chamfer = orientation) with the real 3-filament profile.
- Multi-color pieces must sit ENTIRELY between the side bands (every region needs both
  nozzles). Panelizer limits stay `--bed-long 316 --bed-short 296`.
- Print-card notes: prime tower OFF (purge to chute — no room), brim OFF on the long
  sides (~2mm spare); consider inner mouse-ears on big black plate corners.

## Letters — build pipeline ✅ LIVE (2026-07-02)
- **`tools/centerline.py`** (pure stdlib + ghostscript): EPS → raster → Zhang-Suen skeleton →
  ordered tube centerline(s) → pixel points at pitch → `src/parts/letter_<L>_data.scad`
  (+ a `.debug.ppm` overlay — always eyeball it). Letters are OPEN neon-tube runs, not closed
  outlines (the C = ONE 1161mm tube: outer sweep + mouth turn + inner sweep; 69 px @ 17mm).
- **`src/letter.scad`**: 3-color tile — BLACK base+outer wall / WHITE liner+inner wall+collars /
  CLEAR welded fuzzy lens. Channel cross-section identical to the bolt (18 interior / 22 outer).
- **C @ 270 cap**: tile 313×298×23mm — H2D fit only with width along the 320 axis, `lt_margin=2.5`.
  ⚠ At 270 cap the H's art is ~321mm wide and the +3mm/side WIDENED band ≈ **331mm → H will NOT
  fit the 320 axis**. When H's turn comes: cap ~255–260, or split H after all, or widen H's
  outer verticals inward-only. (Rotation can't save a 331×~290 tile on a 300×320 bed.)

## Still open
- **Generate the other letters** (H A R G E — extractor is generic) + integrate the bolt into the layout.
- **Mounting:** rear rail / black backer board (hides wiring + controller). Deferred.
- **Full-billboard extras** (arrow, TEDxFargo badge, 2026, yellow border, truss) — later scope.
