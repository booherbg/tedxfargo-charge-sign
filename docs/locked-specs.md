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

## Bolt lens fit ✅ printed & snapped
- `bolt_lip_clear = -0.2` → lip Ø18.2 into the 18.0 channel (0.2mm interference). Material-robust
  (clear PETG + clear PLA). Dialed via `lens_fit_*` slices. The bolt is a **solid-stroke** channel;
  letters use the same channel construction along the neon path.

## Pixel clearance (matrix) ✅ collision-verified
- `led_void = 14.0`, `led_clear = 2.5`, masks on flared floor legs. `src/parts/lens_pixel_collision.scad`.

## Print orientation & support
- Everything prints **lens-up / plate-down, NO supports.** Chiral flip-to-use parts must be pre-mirrored
  (see the chiral-flip note) — but letters/testbox print in use-orientation, so it's moot for them.

## Still open
- **Centerline extractor** (skeletonize letters → place pixels at pitch) — the next build step.
- **Generate CHARGE** letters (3-color) + integrate the bolt.
- **Mounting:** rear rail / black backer board (hides wiring + controller). Deferred.
- **Full-billboard extras** (arrow, TEDxFargo badge, 2026, yellow border, truss) — later scope.
