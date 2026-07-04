# CHARGE billboard — print & assembly card

Six 3-color word pieces (`stl/piece<N>_3color.3mf`) + four bolt-board plates
(`stl/board<N>_3color.3mf`). Cut preview / seam map:
`docs/sign-preview/cut-preview.html`; full composition `docs/sign-preview/full-sign.html`.
Specs: `docs/locked-specs.md`,
`docs/superpowers/specs/2026-07-03-billboard-panelize-design.md`.

## Pieces (rendered weights, PETG @1.27)

| # | letter | footprint (mm) | black | white | clear | total | pixels |
|---|--------|----------------|-------|-------|-------|-------|--------|
| 1 | C | 295 × 295 | 225 g | 60 g | 47 g | 332 g | 62 |
| 2 | H | 316 × 295 | 234 g | 78 g | 61 g | 373 g | 81 |
| 3 | A | 296 × 295 | 222 g | 63 g | 50 g | 335 g | 67 |
| 4 | R | 292 × 295 | 252 g | 80 g | 62 g | 394 g | 82 |
| 5 | G | 300 × 295 | 235 g | 79 g | 62 g | 376 g | 82 |
| 6 | E | 290 × 295 | 240 g | 78 g | 61 g | 379 g | 80 |
| | **total** | face 1597 × 295 | 1408 g | 438 g | 343 g | **2189 g** | **454** |

Pixel layout is relaxation-solved: min spacing 14.2 mm (flange is 13.6). Three snug pairs
sit in the R's lower leg (~x 957–989) — press those firmly; no trimming needed. One pixel
deliberately omitted at the A's tube crossing (shared light pocket).

## Bolt board (element 6: fused bolt+X, yellow + red inner)

Board face 410 × 550 mm, four plates, piecewise seams (y=255 full width; top row
splits at x=126, bottom row at x=153). All seam crossings are engineered 13 mm
pullback neon breaks (7 total); the red zigzag crosses no seam. 141 pixels @ 20 mm
(119 yellow / 22 red), `src/parts/bolt_pixmap.json` maps every pixel's color zone +
plate for the controller.

| plate | position | footprint (mm) | black | white | clear | total | pixels |
|-------|----------|----------------|-------|-------|-------|-------|--------|
| B1 | bottom-left | 153 × 255 | 112 g | 21 g | 16 g | 149 g | 19 |
| B2 | bottom-right | 257 × 255 | 192 g | 44 g | 33 g | 269 g | 40 |
| B3 | top-left | 126 × 295 | 101 g | 12 g | 9 g | 123 g | 11 |
| B4 | top-right | 284 × 295 | 257 g | 77 g | 60 g | 393 g | 71 |
| | **total** | board 410 × 550 | 661 g | 155 g | 119 g | **934 g** | **141** |

Same 0.20 Standard process and filament layout as the word pieces (all plates are
smaller than the worst word piece; 295 side across the bed). Plates butt on the wood
frame: B1|B2 and B3|B4 on their vertical seams, the two rows on the y-seam rail.
Screws: per-plate corners + long-edge midpoints (Ø4.5, 24 total). Labels debossed on
bed faces (B1–B4).

## Slicing (per validated specs)
- Filaments: black and white MUST be on different nozzles (they alternate every layer,
  purge-free on the H2D); clear shares a nozzle and triggers the print's ONLY filament
  change at the lens (~z21). Two workable layouts:
  (a) **white+clear on the AMS side, black external** — the swap residue (white→clear)
  is invisible in the weld; black has no auto-backup, so weigh the spool (needs ~260 g).
  (b) **black+clear on the AMS side, white external** — black gets a same-filament AMS
  backup pair (auto-failover on the heavy consumer); bump the black→clear flush volume
  to ~700–800 mm³. Preferred once two black spools are on hand.
- Prime tower: sliced fine tiny (≈9 g) — keep it, or tower OFF + flush-into-objects.
  Prepare-stage tower warnings that vanish after slicing are safe to ignore.
- **0.20 mm Standard** process validated in a test slice: ~8h51m/piece, ~0.25 g purged,
  ~106 "filament changes" = free per-layer nozzle swaps, not purges.
- Place **295-side across the bed** (between the H2D nozzle bands), 316-side deep. Validated
  with `stl/bedcheck_316x295.stl`.
- 0.16 mm layer · 0.42 line · 2 walls · 10% gyroid · 6 top / **7 bottom** (the +1 kills the
  fuzzy-top shell islands) · concentric top · supports OFF · **brim OFF** · bridge fan ON ·
  **prime tower OFF, purge to chute**.
- Label (piece # + letter) is debossed on the bed face of each black body.

## Assembly
1. Wood frame: top + bottom rails spanning ~1.65 m, 50–75 mm standoff depth; side verticals;
   thin back skin screwed to rails (shear web). PSU/controller board on one side.
2. Pieces butt left→right (1→6); seams are pre-relieved 0.12 mm/joint. Screw through the
   pre-drilled Ø4.5 holes (6 per piece: 4 corners + 2 mids) with black pan-heads into the rails.
3. Pixels press into collars from behind, chained in path order within each letter, jumper
   slack across seams. 4-inch strings → ~85 mm folds; tuck loose in the plenum
   (Ø3.2 tie-hole pairs along the paths are there if transport demands).
4. Power: **595 px total** (454 word + 141 board) ≈ the 150 W/24 V PSU's full-white
   edge → cap brightness ~80% or add a second PSU. Colors-only scenes draw far less.
5. Board wiring: chain within each color zone per `bolt_pixmap.json` (yellow chain,
   red chain), jumper slack across seams like the word pieces.
