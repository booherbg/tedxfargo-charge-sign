# CHARGE billboard — whole-word panelization + wood-frame mount (approved 2026-07-03)

Supersedes the per-letter rectangular-tile plan. The sign face is designed as ONE continuous
billboard and then cut into printable pieces; a wooden frame mounts it and swallows the wiring.
Cross-section/diffusion recipe is unchanged from `docs/locked-specs.md`.

## Size & face
- **Cap height 250 mm, uniform** (no per-letter distortion; the shared horizontal cut line across
  all letters aligns by construction). CHARGE face ≈ **1.56 m wide**.
- **Piece height uniform ≈ 295 mm** (tallest letters ~257 + top/bottom screw bands ~14 mm each;
  also keeps every piece ≤ 300 mm on the bed's short axis). Final number set by the generator.
- Face is **continuous black between letters** — no gaps, no per-letter tiles.
- Letters: hollow neon outlines from `assets/letters/*.eps`, tube centerlines extracted, channels
  widened to the locked **18 mm interior / 22 mm outer**; pixels at **~17 mm pitch** (~420 px for
  CHARGE; +22 bolt; 600 owned/ordered).
- Cross-section (locked): black 2 mm base + 1.2 black outer wall / 0.4 white liner + 0.8 white
  inner wall / 19 mm channel / 1.2 welded clear lens, baked fuzzy top (texture .dat swappable
  after the PETG fuzz bake-off). **All-PETG, 3-color** (black/white/clear → extruders 1/2/3).

## Panelization
- Generate the whole word, then cut into **~6 full-height pieces** along **corridor cuts**:
  top-to-bottom paths threaded entirely through black field, **≥5 mm clearance from any channel
  outer wall** — a seam never crosses a lit tube.
- **Flat butt joints**, ~0.12 mm clearance per cut face. No interlock tabs in v1 (wood rails do
  registration); optional printed back straps across a seam if needed.
- Panelizer must **verify every piece against the bed** (H2D 300×320; targets ≤296 short axis,
  ≤316 long axis) and fail loudly with dimensions if a piece won't fit.

## Wood frame (user-built; printed parts only interface with it)
- **Top + bottom horizontal rails** behind fixed bands; pieces screw to rail faces:
  **Ø4.5 screw holes, ≥2 top + 2 bottom per piece**, auto-placed in black field only.
  Black pan-head screws — invisible on the black face at distance.
- Rails lift the face **50–75 mm** → the cable plenum (pixel ~25 mm + ~85 mm folds hang loose).
  Free **Ø3.2 zip-tie hole pairs** along the path as transport insurance.
- Side verticals complete the rectangle; **PSU/controller board** on one side; **thin back skin**
  (hardboard/ply or printed) screwed to rails = anti-racking shear web. French-cleat or
  truss-mount the assembled box.

## Electrical
- **4-inch-pitch strings** chained in path order; jumpers with slack across piece seams.
- ~440 px ≈ 130 W at full white ≈ the 150 W/24 V PSU's edge → cap brightness ~80% or add a PSU.

## Pipeline (implementation scope)
1. **Extractor upgrade** (`tools/centerline.py`): graph-based segment decomposition (junction
   clusters, sliver-rung dropping) so the A extracts correctly; whole-word extraction from
   `CHARGE.eps` in one pass (all letters in shared word coordinates, cap 250 via H reference).
2. **Panelizer** (`tools/panelize.py`): clearance field on a coarse grid → corridor cuts between
   adjacent letters → piece regions, bboxes, bed-fit report; screw + zip-tie hole placement.
3. **Billboard generator** (OpenSCAD): continuous face from word paths; per-piece 3-color
   geometry clipped at cuts; per-piece 3MFs via `tools/make_3mf.py`.
4. **Cut preview** (web view): word bands + cut paths + piece dims/weights/pixel counts for
   approval BEFORE any geometry is rendered.
5. **Assembly map**: seams, screw positions, rail lines, wiring direction, per-piece stats.

## Estimates
~330 g and ~6–8 h per piece → **~2.0 kg, ~40 h print for CHARGE** (plus bolt).

## Later scope (explicitly deferred)
- **Bolt at logo proportion** (current `bolt2` print validates construction; final bolt is larger,
  gets its own board left of CHARGE, likely its own panelization).
- **Yellow accents** like the original billboard (yellow border tube, arrow, X-brace) — same
  channel construction with yellow/amber lensing or warm pixels; revisit after CHARGE.
- Full-billboard extras (TEDxFargo badge, 2026, truss dressing).
