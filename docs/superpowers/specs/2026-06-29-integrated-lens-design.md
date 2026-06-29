# Integrated lit-lens design — diffusion test matrix

**Date:** 2026-06-29
**Status:** implemented; STLs ready for a first print/eval pass
**Eventual goal:** a glowing **TEDxFargo** logo. These square cells are the optical
*coupon* — they find the cross-section (depth, mask, material split) that gives an
even, "sourceless" neon-style glow; that recipe then transfers to the letter-stroke
channels of the logo (the lightning-bolt work was the stroke-geometry precursor).

## Goal & principle

One **single-print, dual-material** cell that is *integrated* (no separate snap-in
lens, no assembly beyond inserting the pixel). The geometry simultaneously holds the
pixel, structures the light, and diffuses it. Primary visual target: **even sourceless
glow** (individual LED invisible), brightness second. Tension acknowledged up front:
"pull light forward" (brightness) and "scatter perfectly" (evenness) oppose each
other; the matrix samples several points on that trade-off.

## Hardware context

- **Printer:** Bambu **H2D**, dual independent nozzles → two materials co-printed in
  the same layer with minimal purge. Build vol (dual) 300×320×325; 350°C / 65°C chamber.
- **Material pair:** **white PETG + clear PETG** (same family → fused boundary; PETG
  heat-tolerant next to warm LEDs; ~95% white reflectance vs ~70% for white PLA).
- **Pixel:** 12mm bullet pixel, dome ~4mm above the plate (`dome_clear`), in the
  calibrated press-fit collar (`collar.scad`), bore Ø12.3.

## Cell architecture (`src/lens_cell.scad`)

Print **plate-down** (collar on bed, optic on top): no flip, **no chirality trap**
(see `[[chiral-flip-mirror-gotcha]]`), pixel inserts from the back afterward.

- **30mm interior square**, 2mm white walls (opaque → no cross-cell light bleed),
  6mm gaps, all tied to **one base slab** = a handleable tray.
- **Material split:** WHITE = base + walls + masks/reflectors (nozzle 1); CLEAR =
  face / fill / puck (nozzle 2). White and clear **abut with 0.1mm overlap** so the
  slicer fuses them.
- **Output:** two **co-registered** STLs — `stl/matrix_white.stl`, `stl/matrix_clear.stl`
  (same origin; verified bbox X −17..137, clear inset 1mm). Load both, assign nozzles,
  print as one job.
- **Labels:** each cell has *N* debossed dots on the tray bottom (cell index 1–8).

## Families & test matrix (8 cells, 4×2)

| # | Code | Family | Key params |
|---|------|--------|-----------|
| 1 | A0 | Masked cavity — baseline | no mask, gap 15 |
| 2 | A1 | Masked cavity | **perforated white dot d14, 5mm above dome**, gap 15 |
| 3 | A2 | Masked cavity | perforated dot d16, gap 15 |
| 4 | A3 | Masked cavity — deeper | perforated dot d14, gap 18 |
| 5 | R1 | Reflector cone | white "volcano" around LED, gap 15 |
| 6 | B1 | Volumetric scatter | clear fill → **slice with ~15% gyroid infill**, gap 15 |
| 7 | C1 | TIR puck | clear + 90° center cone refractor, gap 15 |
| 8 | C2 | TIR puck | clear + 60° center cone refractor, gap 15 |

The **mask is perforated (~43% open), floated close to the LED** — this is the crucial
detail: it attenuates+recycles the central peak with a soft penumbra. An *opaque* mask
near the face creates a dark spot (see physics below). Family A is the workhorse; R/B/C
are exploratory points (efficiency vs evenness vs "alien" aesthetic).

## Research basis (sources)

- Hotspot masking → use **semi-transparent / perforated** masks, not opaque; reflective
  white dot recycles blocked light. [masking study](https://www.sciencedirect.com/science/article/abs/pii/S0030401813010419),
  [diffuser-dot patent](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11719978)
- Uniformity geometry: D/H ≈ 3 → uniformity > 0.88; gap/width ≈ 0.5 → **gap ≈ 15mm**.
  [panel design](https://www.researchgate.net/publication/286536701_Direct-down_LED_panel_light_design_for_uniform_illumination)
- White reflectance & per-bounce loss (~5%/bounce, compounding) → **white PETG**, keep
  bounce budget low. [reflector patent](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8740442)
- 3D-printed diffuser recipe: gyroid ~10–20%, few top layers, thin walls.
  [Adafruit neon](https://learn.adafruit.com/led-neon-signs-with-neopixels/3d-printing),
  [gyroid as diffuser](https://bigrep.com/posts/gyroid-infill-3d-printing/)
- TIR/batwing cone 60–90° spreads the forward beam sideways. [TIR optics](https://www.tandfonline.com/doi/full/10.1080/15980316.2019.1693436)

## Physics validation (2D Monte-Carlo, `analysis/cavity_sim.py`)

R_wall=0.92, 120k rays. peak/mean 1.0 = flat; CoV lower = more even.

| Config | Eff | peak/mean | CoV |
|---|---|---|---|
| A0 no mask | 94% | 1.21 | 14.8% |
| A1 perforated d14 | 82% | 1.07 | 5.0% |
| A2 perforated d16 | 81% | 1.07 | 6.4% |
| A3 perforated, gap18 | 81% | 1.06 | 5.2% |
| A1 *opaque* (contrast) | 66% | 1.22 | **center inverts → dark spot** |

Confirms: perforated dot flattens the hotspot (CoV 15→5%) at modest brightness cost;
opaque masking is the documented failure mode. 2D + idealized (no Fresnel/face
refraction) → trends/ranking, not absolute photometry.

## Known risks

- **A/R clear faces bridge ~30mm** (open cavity). Print with strong part cooling + a few
  solid top layers (Adafruit-proven). Minor sag is acceptable (adds diffusion). If it
  fails: add a 2mm crown or a clear cross-rib (round 2).
- **Perforations may clog** (over-extrusion shrinks holes) → would read as a dark center;
  fix by widening holes / pitch. The sim's opaque-contrast row is the tell.
- **C1 90° cone** sidewalls are at the ~45° self-support limit; C2 (60°) is safer.
- **B1** needs a per-object gyroid infill setting in the slicer (graceful: prints as a
  solid clear block if forgotten — still a diffuser, just not volumetric).

## Path to TEDxFargo

The winning cross-section (gap + mask/optic + white/clear split) becomes the channel
profile applied along the **TEDxFargo letter strokes** (stadium cross-section like the
bolt channel). Pixel pitch along strokes and per-letter wiring are later sub-projects.
