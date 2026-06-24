# CHARGE LED Sign — Parametric STL Generator

**Date:** 2026-06-24
**Status:** Approved (design); coupon fast-tracked for first print

## Goal

Generate 3D-printable STLs for an illuminated sign based on the TEDxFargo
"CHARGE" logo. Each letter is a channel-letter-style shell lit from behind by
12mm bullet pixels, with a clear printed diffuser face. Build the **CHARGE**
word first; the X/lightning bolt and other elements are stretch goals.

## Physical concept (per-letter stackup)

Front (viewer) → back (wall):

1. **Diffuser face** — clear filament; tunable thickness + slicer infill.
2. **Light-mixing air gap** — the main optical distance (LED tip → diffuser).
3. **Bullet pixel** — 12mm, press-fit nose-forward through a calibrated collar.
4. **Rear collar wall** — printed wall; collars merged in at each pixel.
5. **Mounting / wiring cavity** — room for wires + flat wall mount (later).
6. **Cover / backing panel** — separate, optional, added once optics work.

## Key decisions

- **Print strategy B (chosen):** print the shell *rear-wall-down* (collar holes
  flat on the bed for the crispest press-fit), front open; the **diffuser is a
  separate flat panel** that drops into / glues onto the front. This eliminates
  trapped supports and makes diffusers swappable for testing. Strategy A
  (one-piece, sparse transparent infill standing in for the air gap + support)
  is kept as a later optical experiment.
- **Collar:** `assets/bullet-collar.stl` is a pre-calibrated press-fit ring,
  OD 16mm, bore Ø12.19 necking to a Ø11.44 retention lip at mid-height, 2mm
  tall, **symmetric** (insertion direction agnostic). It is **merged (unioned)
  into the rear wall** at each pixel position; the wall gets a Ø12.3 clearance
  hole and the collar re-establishes the calibrated grip.
- **Toolchain:** **OpenSCAD**. Decisive because it natively imports the collar
  mesh and boolean-unions it at N positions, and exports STLs headlessly via
  CLI. (build123d/CadQuery rejected: poor mesh-STL booleans, would force
  re-modeling the collar and losing its calibration.)
- **Letters:** supplied as Illustrator EPS (vector). For OpenSCAD they must
  become SVG/DXF — export SVG from the `.ai` (preferred) or install
  `ghostscript`/`inkscape`. Not needed for the coupon.
- **Diffuser tuning split:** *thickness* = STL parameter (print slabs at
  1/2/3mm); *infill pattern/density* = Bambu Studio slicer setting on those
  slabs (gyroid/grid, top & bottom solid layers = 0 so the infill diffuses).
- **Pixel layout:** parameterized **density** — `pixel_pitch` along the path
  and `pixel_rows` across the stroke width (single centerline row for small
  letters; multiple rows when the stroke is wide).
- **Printer:** Bambu H2D (~350×320×325mm build volume). A single letter at
  ~300mm tall fits the bed.

## System architecture (OpenSCAD)

```
src/config.scad      all tunable knobs + derived values (the file you edit)
src/collar.scad      import bullet-collar.stl; place_collar(x,y)
src/diffuser.scad    diffuser_panel(thickness)
src/coupon.scad      depth-ladder test coupon
src/letter.scad      (later) outline -> shell -> collars -> rebate
src/pixel_layout.scad(later) outline/path -> pixel positions
src/main.scad        build entry point; selects part via -D part="..."
build.sh             openscad CLI -> exports STLs to ./stl/
assets/              bullet-collar.stl, *.eps, (later) *.svg
stl/                 generated output (git-ignored)
```

One module = one job. `build.sh` regenerates every STL from `config.scad`.

## Deliverable 1 — Stackup coupon (first print)

A single shared rear plate (2mm, on the bed, 3 merged collars) with **three
chimneys of different heights** = a depth ladder. Chimney heights set
`led_gaps` = 20 / 35 / 50mm clear LED-to-panel distance. Each chimney is a plain
open box; the diffuser panel **press-fits** straight into the opening
(`panel_press_clear` undersize), so panel thickness can vary freely and the
print stays support-free (every face is on the bed or an open top).

Print: 1 coupon body + diffuser panels at 1/2/3mm. Vary slicer infill on the
panels. Outcome: read distance × thickness × infill against each other, and
verify the real press-fit in a printed collar.

Tunables that matter: `dome_clear` (dome protrusion above the plate — measure on
the actual pixel), `led_gaps`, `panel_thicks`, `pixel_through`.

## Deliverable 2 — Mini "C" (150mm)

`C.svg` → `linear_extrude` open-front shell → `pixel_layout` places collars
along the stroke (`pixel_pitch`, `pixel_rows`) → front rebate → diffuser panel.
Applies the optical recipe found by the coupon and validates the EPS→collar
pipeline.

## Validation loop

Press a real pixel into a printed collar (calibration) → light it → compare
wells and panels → lock the recipe into `config.scad` → print the C.

## Open / deferred

- Exact `dome_clear` for the specific bullet pixel (measure).
- How literally to follow the neon-tube outline aesthetic vs. solid channel
  letters (a later letterform decision).
- EPS→SVG conversion path (Illustrator export vs. installed tool).
- Backing/cover, heat-sink posts, mounting features (after optics are proven).
