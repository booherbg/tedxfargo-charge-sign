# TEDxFargo CHARGE — Sign Build Handoff (refreshed 2026-07-05, overnight bolt sprint)

**What this is:** a 3D-printed, LED-lit replica of the TEDxFargo CHARGE 2026 neon-billboard logo
(`assets/tedxfargo-full-logo.png`). White-reflector channels + frosted clear lenses, lit from
behind by 12 mm bullet pixels. Read top-to-bottom for full context; numeric truth lives in
`docs/locked-specs.md`; print/assembly steps in `docs/assembly-charge.md`.

## 0. State at a glance
- **CHARGE word: DONE and sliceable.** Six 3-color pieces (`stl/piece1..6_3color.3mf`), all
  bed-validated, mesh-audit clean, 2,189 g total, **454 pixels**. User has successfully sliced;
  first prints pending white PETG delivery. Do not regenerate unless design changes.
- **Bolt board: GEOMETRY FINAL, plates BUILT (overnight 2026-07-04→05).** The wrong-vector
  blocker is resolved: board now uses **element 6** (the logo's actual left panel — flat-top
  bolt + X fused as ONE yellow outline) with the billboard's red zigzag inside. 410×550 face,
  **4 plates** (piecewise seams), 141 px @20 mm, **sign total 595 px**. `stl/board1..4_3color.3mf`.
  User has NOT yet reviewed the design or sliced — morning review pending.
- **PETG fuzz bake-off** (testboxes v3–v6, picks the lens texture): ready to print on the
  ~100 g white remnant; a texture change is a one-line .dat swap + clear-body re-render.
- Wood frame, wiring, mounting: user-built later; interface specs in the assembly card.

## 1. Locked build facts (never re-derive)
- Word: cap 250 mm uniform; face 1597×295; 6 pieces, corridor cuts through black only; auto-kern
  applied (A|R +1.2, R|G +5.9). Letters @17 mm pitch.
- Cross-section (word AND board): black 2 mm plate + 1.2 black outer wall / 0.4 white liner +
  0.8 white inner wall / 19 mm channel (18 interior) / 1.2 clear lens + baked V3 fuzz
  (dead-banded ±50 µm). ALL-PETG, 3 colors.
- Pixels: Ø12 bullets, flange Ø13.6 (**14.5 mm min spacing; 13.0–14.5 = snug/flange-snip**),
  collar `assets/bullet-collar.stl`. 4-inch strings.
- Bed truth (H2D, validated `stl/bedcheck_316x295.stl`): both-nozzle zone 316×295; place 295
  across, long side deep. Multi-color parts must sit between the nozzle bands.
- Slicing: 0.20 Standard + card overrides; clear shares the WHITE nozzle (only swap ≈ z21);
  prime tower in the right-nozzle column or OFF + flush-into-objects; skirt/brim OFF.
- Power: **595 px** ≈ full-white edge of the 150 W PSU → cap ~80% or add PSU.

## 2. Bolt board — final design (element 6, C1 colorway)
- **Source truth:** `RedNeon/TEDx_RedNeon_6.psd` = the logo's left panel: flat-top bolt and X
  are ONE fused outline (one closed loop in art, painted with a neon break at the bolt-tail
  tip + two kiss-junctions where the tail weaves the X's top bar). Extraction:
  `assets/bolt_element6.pgm` → `tools/centerline.py --target-h 505` → `src/parts/boltx_data.scad`
  (3 open runs, 2,456 mm tube, centerline bbox 355×493, panel ≈ 2.06× letter cap — the
  deployed-logo proportion).
- **Red inner:** the billboard's red is a SINGLE-STROKE zigzag tube (not an outline): top tip →
  long diagonal down-left → flat bar right → long diagonal down to a tip just below the weave.
  Ours is 4 vertices, hand-fit to the billboard and clearance-audited legal (26 mm rule):
  `RED_PATH` in `tools/bolt_compose6.py` = (228,466)→(118,349)→(253,349)→(194,239) in boltx
  data coords. **Billboard-fidelity compromises (physics, not taste):** the bar can't tilt
  up-right (X-top-bar/notch-shelf corridor is exactly 0 mm at 22 mm bands) and the tail stops
  at y≈239 (wedge corridor pinches shut below). An 18 mm red band would buy only ~10 mm more
  tail — not worth a second cross-section.
- **Board:** 410×550, content margins ~17 mm. **Piecewise seams** (a full-height vertical seam
  cannot avoid grazing the X's near-vertical legs): y=255 full width, then top row splits at
  x=126, bottom row at x=153. Plates B1 153×255 / B2 257×255 / B3 126×295 / B4 284×295 — all
  fit 316×295. **7 breaks**, all engineered pullbacks (13 mm PERPENDICULAR to the seam —
  shallow crossings get proportionally longer arc trims). The red crosses NO seam.
- **Pixels:** 141 (119 yellow / 22 red) @20 mm pitch, relaxation-solved, 3 snug pairs,
  2 dropped at crossings. `src/parts/bolt_pixmap.json` = per-pixel color zone + plate.
- The y-seam reads as 4 aligned neon breaks across the X's waist (same engineered-break
  pattern the user approved for the old 2-plate C1). Bed depth pins the seam at 255; the red
  tail tip pins it from above — it cannot move.

## 3. Pipeline (all committed, reproducible)
Word: `tools/centerline.py` → `tools/panelize.py` → `tools/gen_pieces.py` →
`src/parts/piece.scad` → `build_pieces.sh` → `tools/make_3mf.py` (manifold audit inline).
Board: `tools/bolt_compose6.py` (composition + piecewise seam scan + splits; graze check,
corner keepout, tangent-apex rejection) → `tools/boltboard.py --pitch 20` (pixels/screws/
ties/fuzz/pixmap) → `src/parts/bolt_piece.scad -D PIECE=1..4 -D COL=1..3` → `build_board.sh`.
Audits: `tools/clearance_audit.py` (26 mm channel rule with crisp-crossing exemption — run it
on any new path vs the yellow), `tools/bolt_preview.py` (fast raster comps).
Letter pixel truth: `src/parts/word_cuts.json` (454). Board: `bolt_el6.json` + pixmap.

## 4. Morning-review queue (user)
0. The overnight review artifact (lit-sign render, billboard gate-check, physics notes,
   iteration verdicts, wiring chain, print queue, phase-2 accents teaser):
   https://claude.ai/code/artifact/1eb4e351-e13a-43f7-a56d-8fafd92376fa
1. Look at `docs/sign-preview/full-sign.html` (regenerate: `python3 tools/gen_preview.py`)
   and the artifact — composition, seams, red shape.
2. If the red gesture or seam positions want tweaking: edit `RED_PATH` / re-run composer
   (the seam scanner re-picks automatically), then `boltboard.py`, then `build_board.sh`.
3. Slice `stl/board1..4_3color.3mf` in the GUI (same 0.20 process as the word; plates are
   smaller). Note: Bambu's headless CLI was probed overnight — it only slices project 3MFs
   with plate metadata and silently no-ops on our geometry 3MFs, so GUI import remains the
   flow (our 3MFs load as ONE co-registered multi-part object, verified).
4. Bolt-vs-word hang alignment is a frame decision (word band currently centered on 550).

## 5. Non-obvious gotchas (hard-won, keep)
- Skeleton tips have no degree-1 endpoints (ZS clumps) → open/closed by walk behavior.
- The art paints breaks as notches; element 6's outline is 3 open runs, not a closed loop —
  two of the six ends are kiss-junctions that FUSE in the 22 mm band (by design).
- A vertical seam through this art almost always grazes a steep stroke — the graze check in
  bolt_compose6.py is what makes seams legal; don't bypass it. Pullbacks are perpendicular-
  normalized (arc = 13/sin θ), else shallow cuts leave <13 mm true seam clearance.
- Fuzz heightfields near the lens plane make CGAL micro-slivers → 0.02 floor + off-lattice
  base (0.1504) + ±50 µm dead-band; `make_3mf.py` audits every mesh.
- Bambu: "filament change times" on H2D = free per-layer nozzle swaps, not purges. 3MF-imported
  filaments are unbound until synced; verify mapping in the send dialog. AMS backup = identical
  preset+color in two slots on the SAME side. Left nozzle has no AMS (weigh before big blacks).
- Nesting two 22 mm channels needs ≥26 mm centerline gap; long parallel sub-26 = rejected mush;
  crisp crossings/pockets = accepted (letter-A precedent). `clearance_audit.py` encodes this.
- OBSOLETE (deleted 2026-07-05): el-5 bolt artifacts (bolt5*_data, bolt_final2.json c1/c2,
  bolt_c1_clean.json, old 2-plate board*_c* STLs/3MFs, tools/bolt_compose.py). Element 5
  turned out to BE the red inner's slim-bolt shape, not the panel outline.
