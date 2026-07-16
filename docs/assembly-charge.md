# CHARGE billboard — print & assembly card

Six 3-color word pieces (`stl/piece<N>_3color.3mf`) + four bolt-board plates
(`stl/board<N>_3color.3mf`). Cut preview / seam map:
`docs/sign-preview/cut-preview.html`; full composition `docs/sign-preview/full-sign.html`.
Specs: `docs/locked-specs.md`,
`docs/superpowers/specs/2026-07-03-billboard-panelize-design.md`.

## Pieces (rendered weights, PETG @1.27)

Letterforms are the APPROVED originals (the art's open strokes are the font).
The 2026-07-05 bridging experiment was reverted at the user's direction — the
"no gaps" scope applies to the BOLT BOARD ONLY.

| # | letter | footprint (mm) | black | white | clear | total | pixels |
|---|--------|----------------|-------|-------|-------|-------|--------|
| 1 | C | 295 × 295 | 225 g | 60 g | 43 g | 328 g | 62 |
| 2 | H | 316 × 295 | 234 g | 78 g | 56 g | 368 g | 81 |
| 3 | A | 296 × 295 | 222 g | 63 g | 46 g | 331 g | 67 |
| 4 | R | 292 × 295 | 252 g | 80 g | 57 g | 389 g | 82 |
| 5 | G | 300 × 295 | 235 g | 79 g | 57 g | 371 g | 82 |
| 6 | E | 290 × 295 | 240 g | 78 g | 56 g | 374 g | 80 |
| | **total** | face 1597 × 295 | 1408 g | 438 g | 315 g | **2161 g** | **454** |

Pixel layout is relaxation-solved: min spacing 14.2 mm (flange is 13.6). Three snug pairs
sit in the R's lower leg (~x 957–989) — press those firmly; no trimming needed. One pixel
deliberately omitted at the A's tube crossing (shared light pocket).

## Bolt board (element 6: fused bolt+X, yellow + red inner)

Board face 410 × 550 mm, four plates, piecewise seams (y=255 full width; top row
splits at x=126, bottom row at x=153). CONTINUOUS MODE: channels cross the plate
joints (7 hairline lens joints; butt the plates snug — one global fuzz field keeps
the lens texture continuous). **SEAM STRAPS (2026-07-10, spec
`docs/superpowers/specs/2026-07-10-seam-bracket-design.md`): printed white splice
straps behind each seam replace the y-seam rail; LEDs run continuously across the
joints.** 137 pixels @ 21.5 mm (116 yellow / 21 red), pinned at every crossing
(±9.5 mm straddle); worst seam-adjacent spacing 23.5 mm (was 58). TWO pixels sit ON
a seam — their collars are embedded in straps S4/S3 (they seat 2 mm deeper; in the
validated optics window). `src/parts/bolt_pixmap.json` maps color zone + plate +
`mount` (plate|bracket) + chain (136 links; extension jumpers at chain 86 and 107).
Review page: `docs/sign-preview/bracket-preview.html`
(`python3 tools/gen_bracketpreview.py`).

| plate | position | footprint (mm) | black | white | clear | total | pixels |
|-------|----------|----------------|-------|-------|-------|-------|--------|
| B1 | bottom-left | 153 × 255 | 113 g | 22 g | 17 g | 152 g | 18 |
| B2 | bottom-right | 257 × 255 | 193 g | 44 g | 33 g | 270 g | 39 |
| B3 | top-left | 126 × 295 | 101 g | 13 g | 10 g | 124 g | 12 |
| B4 | top-right | 284 × 295 | 259 g | 78 g | 58 g | 395 g | 68 |
| | **total** | board 410 × 550 | 664 g | 157 g | 118 g | **939 g** | **137** |

Same 0.20 Standard process and filament layout as the word pieces (all plates are
smaller than the worst word piece; 295 side across the bed). Plates splice on the
printed straps (S1+S2 on y=255, butt joint x=145.5; S3 on x=126; S4 on x=153) with
**M4×8 black button-heads into captive hex nuts** (23 face holes along the seams);
the panel then mounts to the frame by **perimeter wood screws only** (Ø4.5, 14 —
bottom/top rails + side stiles; NO y-seam rail). Straps print in white PETG,
front-face-down, no supports (S1 37 g / S2 67 g / S3 68 g / S4 54 g ≈ 226 g total),
plus the pixel-pusher tool. Leg sockets (Ø10.2, three on the y-straps) stay empty
unless the mounted panel flexes — then print Ø10 friction legs at plenum depth.
Labels debossed on bed faces (B1–B4).

## Slicing (per validated specs)
- **CHOSEN LAYOUT (2026-07-05): black + clear on the RIGHT nozzle (AMS side), white on
  the LEFT (external spool).** 3MF filament order matches: **1 = black (right), 2 = clear
  (right), 3 = white (left)**. Load a second black spool in the right AMS as a
  same-filament backup pair (auto-failover on the heavy consumer — black is 2/3 of all
  filament). Black and white still sit on different nozzles → the per-layer wall
  alternation stays purge-free. The print's ONLY filament change is black→clear on the
  right nozzle at the lens (~z21, black is finished by then); bump the black→clear
  flush volume to ~700–800 mm³ — the prime tower absorbs it.
- Prime tower ON, placed in the right-nozzle-only column (fits all pieces; across-bed
  footprint is uniformly 295). Prepare-stage tower warnings that vanish after slicing
  are safe to ignore. Verify the filament→nozzle grouping in the slicer preview before
  sending (known Bambu Studio grouping quirk — use Rearrange Filament if needed).
- **These are SLICER settings — the 3MFs carry only geometry + filament order.** Set
  flush volumes / tower / nozzle mapping once per session, then **File → Import** each
  3MF into that one project (each becomes its own plate). Do NOT File → Open each file —
  that resets the project and your settings. Black→clear flush: verify the matrix cell
  (auto-calc is usually high for dark→light, but check ≈700–800 mm³).
- White (left, no backup): worst single piece uses ~81 g — weigh the spool before
  starting a piece if it's running low.
- **0.20 mm Standard** process validated in a test slice: ~8h51m/piece, ~0.25 g purged,
  ~106 "filament changes" = free per-layer nozzle swaps, not purges.
- Place **295-side across the bed** (between the H2D nozzle bands), 316-side deep. Validated
  with `stl/bedcheck_316x295.stl`.
- 0.16 mm layer · 0.42 line · 2 walls · 10% gyroid · 6 top / **7 bottom** (the +1 kills the
  fuzzy-top shell islands) · concentric top · supports OFF · **brim OFF** · bridge fan ON ·
  **prime tower ON** (see above — the tower is what absorbs the black→clear flush; do not
  re-flip this to OFF).
- Lens texture is **V8** (PETG bake-off winner): jittered pyramid facets, 2.0 mm cells /
  0.6 mm peaks — "uniform but scattered," brighter and clearer than the old V3 frost.
- **Import note:** R, G, E and board B4 may trigger Bambu's "model has issues → Fix?" on
  import — click **Fix** (it welds the µm-scale export slivers; validated benign class).
  C, H, A and B1–B3 import clean.
- Label (piece # + letter) is debossed on the bed face of each black body.

## Assembly
1. Wood frame (full sign ≈ 2.07 m wide: board 410 + 60 gap + word 1597; 50–75 mm standoff
   depth; thin back skin as shear web; PSU/controller on one side):
   - **Word zone**: top + bottom rails spanning the 1.6 m word run, catching each piece's
     corner/mid screws (as before).
   - **Board zone (seam-strap design, 2026-07-10)**: PERIMETER ONLY — bottom rail
     (screws at y≈6), top rail (y≈544), and side stiles (x≈6 / x≈404, mid-height
     screws). NO y-seam rail: the printed straps splice the plates into one rigid
     panel, and pixel bodies now live right at the seams where a rail would collide.
     Board is 550 tall vs the word's 295; share stiles at the 60 mm gap as before.
1b. **Board panel first, off the frame**: plates face-down and butted (B1|B2, B3|B4,
   rows together), M4 nuts dropped into the strap pockets, straps on (S1+S2 butt at
   x=145.5 — a screw pair flanks each side), M4×8 black button-heads from the front.
   THEN pixels — brackets-first means wires can never be pinched under a strap.
2. Word pieces butt left→right (1→6); seams are pre-relieved 0.12 mm/joint. Screw through
   the pre-drilled Ø4.5 holes (6 per piece: 4 corners + 2 mids) with black pan-heads into the rails.
   **Snug, not tight — let the pieces float.** PETG moves ~14× more than a wood rail along grain
   (70 vs 5 µm/m/°C): across the 1597 mm run a 10 °C rise wants 1.04 mm the frame won't give, and
   the 5 seams relieve only 0.6 mm total — the balance becomes bow, seam crush, or elongated holes
   (20 °C → 1.48 mm over). The LEDs make this a **standing** delta, not a seasonal one: they warm
   the PETG inside the plenum while the rail stays at ambient. If it bows, slot the outer holes on
   pieces 1 and 6. (Matched-CTE printed frame would remove it — priced and declined in
   `docs/superpowers/specs/2026-07-15-printed-frame-feasibility.md`.)
3. Pixels press into collars from behind, chained in path order within each letter, jumper
   slack across seams. 4-inch strings → ~85 mm folds; tuck loose in the plenum.
   (Zip-tie holes removed 2026-07-06: through-holes in the black face leak light
   as bright pinpricks with the plenum lit. Wood-screw holes remain.)
   **Board near-seam pixels** pass through the straps' Ø17 chamfered holes — seat them
   with the printed pusher (Ø14 slotted tube). The TWO on-seam pixels (marked
   `mount: bracket` in the pixmap, at (153,51) and (126,401)) press into the strap
   collars through the plates' Ø13 bites and sit 2 mm deeper — by design.
4. Pixels: **591 total** (454 word + 137 board) of EXACTLY 600 owned (strings of 50 —
   hard cap, user-confirmed). Leave the last string's unused 9-px tail ATTACHED and
   tucked in the plenum — it is the only spare stock (warranty covers DOA).
   Power: 591 also ≈ the 150 W/24 V PSU's full-white edge → cap ~80% or add a second PSU.
   Colors-only scenes draw far less.
5. Board wiring: ONE 137-px data chain (pixels are addressable; color zones are
   software) — follow the `chain` index in `bolt_pixmap.json`; extension jumpers
   at chain 86 and 107; jumper slack across seams like the word pieces.
6. Hardware shopping: 23× M4×8 black button-head + 23× M4 hex nut (+ spares).
