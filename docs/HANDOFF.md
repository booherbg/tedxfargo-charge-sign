# TEDxFargo CHARGE — Sign Build Handoff (refreshed 2026-07-05, overnight bolt sprint)

**What this is:** a 3D-printed, LED-lit replica of the TEDxFargo CHARGE 2026 neon-billboard logo
(`assets/tedxfargo-full-logo.png`). White-reflector channels + frosted clear lenses, lit from
behind by 12 mm bullet pixels. Read top-to-bottom for full context; numeric truth lives in
`docs/locked-specs.md`; print/assembly steps in `docs/assembly-charge.md`.

> **Firmware / effects / simulator have their own handoff:** `docs/HANDOFF-FIRMWARE.md`
> (16 custom WLED effects, flashed and confirmed on hardware 2026-07-17).

## 0. State at a glance
- **CHARGE word: RESTORED to the APPROVED design (2026-07-05) — do not restyle.**
  A bridging experiment (closing the letterforms' open strokes) was built and then
  REVERTED at the user's direction: the open strokes ARE the font; "no gaps" applies to
  the BOLT BOARD ONLY. Word = the approved 454 px / original letterforms / original cuts.
  Pieces re-rendered from the restored data (identical inputs to what the user sliced);
  prints pending white PETG delivery. tools/bridge_word.py remains in the repo but MUST
  NOT be run on the word.
- **Bolt board: CONTINUOUS MODE, plates rebuilt 2026-07-05.** Element 6 (the logo's left
  panel) as ONE bridged closed loop + the billboard's red zigzag. 410×550 face, 4 plates;
  channels now CROSS the plate joints (no pullback breaks — user chose continuity over
  joint-free lenses); 7 hairline lens joints; one global fuzz field keeps texture continuous.
  137 px @20 mm, **sign total 591 px** (of EXACTLY 600 owned — hard inventory cap).
  `stl/board1..4_3color.3mf`. User approved the look; gaps feedback applied (BOLT ONLY);
  slicing pending.
- **PETG fuzz bake-off** (testboxes v3–v6, picks the lens texture): ready to print on the
  ~100 g white remnant; a texture change is a one-line .dat swap + clear-body re-render.
- Wood frame, wiring, mounting: user-built later; interface specs in the assembly card.

## 1. Locked build facts (never re-derive)
- Word: cap 250 mm uniform; face 1597×295; 6 pieces, corridor cuts through black only; auto-kern
  applied (A|R +1.2, R|G +5.9). Letters @17 mm pitch.
- Cross-section (word AND board): black 2 mm plate + 1.2 black outer wall / 0.4 white liner +
  0.8 white inner wall / 19 mm channel (18 interior) / 1.2 clear lens + baked **V8 texture**
  (jittered pyramid facets 2.0/0.6 mm, max-union tents, FLOATED 0.02 mm above the lens plane —
  no dead-band pass; see make_fuzz.py --mode=pyramid-jitter). ALL-PETG, 3 colors.
- Pixels: Ø12 bullets, flange Ø13.6 (**14.5 mm min spacing; 13.0–14.5 = snug/flange-snip**),
  collar `assets/bullet-collar.stl`. 4-inch strings.
- Bed truth (H2D, validated `stl/bedcheck_316x295.stl`): both-nozzle zone 316×295; place 295
  across, long side deep. Multi-color parts must sit between the nozzle bands.
- Slicing: 0.20 Standard + card overrides. LAYOUT (chosen 2026-07-05): black+clear on the
  RIGHT nozzle (AMS, black backup pair), white LEFT external; 3MF filament order 1=black,
  2=clear, 3=white. Only swap = black→clear ≈ z21 (flush 700–800 mm³); prime tower ON in
  the right-nozzle column; skirt/brim OFF.
- **PIXEL INVENTORY IS THE HARD CAP: user owns EXACTLY 600 (strings of 50).** Sign total
  **591** (word 454 + board 137 @20 mm) → 9 spares. Any change that adds pixels needs
  user sign-off. (Power is secondary: ~591 px also sits at the 150 W PSU's full-white
  edge → cap ~80% or add PSU.)

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
  fit 316×295. **CONTINUOUS MODE (2026-07-05):** channels cross the joints — 7 hairline lens
  joints instead of pullback breaks; graze/corner checks still gate seam placement;
  ONE global fuzz field (fuzz_board_global.dat).
- **SEAM STRAPS (2026-07-10, spec docs/superpowers/specs/2026-07-10-seam-bracket-design.md):**
  4 white PETG splice straps (S1+S2 y=255 butt @145.5 / S3 x=126 / S4 x=153; 48 wide, 4 web +
  8 rails, ~226 g) behind the seams REPLACE the y-seam wood rail. Plates screw to them with
  M4×8 + captive hex nuts (23); frame catches PERIMETER wood screws only (14). Straps carry
  Ø17 pass-holes for near-seam pixel bodies, leg sockets (Ø10.2 ×3, empty until sag says
  otherwise), and TWO embedded collars.
- **Pixels:** 137 (116 yellow / 21 red) @21.5 mm pitch, ANCHORED at the 7 seam crossings
  (straddle pinned at ±9.5 mm perpendicular, keepout floor 9.5 — 1.5 mm collar web).
  The two shallow crossings (31°/29°) pin the pixel ON the seam: collars live in the straps,
  plates get Ø13 bites, pixel seats 2 mm deeper (inside the 10–20 optics window). Worst
  seam-adjacent gap 23.5 mm (was 34–58). Assembly is BRACKETS-FIRST, then pixels through the
  strap holes (printed pusher) — wires always route behind. `src/parts/bolt_pixmap.json` =
  color zone + plate + `mount` (plate|bracket) + chain (136 links, jumpers at 86/107).
  Review page: docs/sign-preview/bracket-preview.html (tools/gen_bracketpreview.py).
- (Historic note: the earlier pullback design read as 4 aligned breaks across the X's waist;
  superseded by continuous mode per user feedback.)

## 3. Pipeline (all committed, reproducible)
Word: `tools/centerline.py` → `tools/panelize.py` → `tools/gen_pieces.py` →
`src/parts/piece.scad` → `build_pieces.sh` → `tools/make_3mf.py` (manifold audit inline).
Word bridging: `tools/bridge_word.py` (letters -> closed loops, in word_cuts.json).
Board: `tools/bolt_compose6.py` (bridge + piecewise seam scan, CONTINUOUS mode; graze check,
corner keepout, tangent-apex rejection) → `tools/boltboard.py` (anchored seam-crossing
placement, pitch auto-solved to the 137 budget; channel-aware seam screw pairs; emits
board_layout + bracket_layout + pixmap; zip-ties removed 2026-07-06 — light leaks) →
`src/parts/bolt_piece.scad -D PIECE=1..4 -D COL=1..3` + `src/parts/bracket.scad -D STRAP=1..4`
→ `build_board.sh` (plates, straps, pusher).
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
  bolt_compose6.py is what makes seams legal; don't bypass it. (Historic pullback-mode note:
  pullbacks must be perpendicular-normalized, arc = 13/sin θ.)
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
