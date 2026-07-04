# CHARGE billboard — print & assembly card

Six 3-color word pieces (`stl/piece<N>_3color.3mf`) + four bolt-board plates
(`stl/board<N>_3color.3mf`). Cut preview / seam map:
`docs/sign-preview/cut-preview.html`; full composition `docs/sign-preview/full-sign.html`.
Specs: `docs/locked-specs.md`,
`docs/superpowers/specs/2026-07-03-billboard-panelize-design.md`.

## Pieces (rendered weights, PETG @1.27)

Letters are CONTINUOUS closed neon loops (2026-07-05: stroke-end openings bridged
per user feedback; `tools/bridge_word.py`). Cuts, kerning, and pixel layout unchanged.

| # | letter | footprint (mm) | black | white | clear | total | pixels |
|---|--------|----------------|-------|-------|-------|-------|--------|
| 1 | C | 295 × 295 | 227 g | 62 g | 48 g | 337 g | 62 |
| 2 | H | 316 × 295 | 232 g | 78 g | 61 g | 370 g | 81 |
| 3 | A | 296 × 295 | 222 g | 64 g | 50 g | 336 g | 67 |
| 4 | R | 292 × 295 | 249 g | 79 g | 62 g | 391 g | 82 |
| 5 | G | 300 × 295 | 236 g | 81 g | 63 g | 380 g | 82 |
| 6 | E | 290 × 295 | 239 g | 78 g | 60 g | 377 g | 80 |
| | **total** | face 1597 × 295 | 1406 g | 442 g | 344 g | **2190 g** | **454** |

Pixel layout is relaxation-solved: min spacing 14.2 mm (flange is 13.6). Three snug pairs
sit in the R's lower leg (~x 957–989) — press those firmly; no trimming needed. One pixel
deliberately omitted at the A's tube crossing (shared light pocket).

## Bolt board (element 6: fused bolt+X, yellow + red inner)

Board face 410 × 550 mm, four plates, piecewise seams (y=255 full width; top row
splits at x=126, bottom row at x=153). CONTINUOUS MODE: channels cross the plate
joints (7 hairline lens joints; butt the plates snug — one global fuzz field keeps
the lens texture continuous). 137 pixels @ 20 mm (116 yellow / 21 red), kept
≥12.5 mm off every seam so no collar straddles a joint. `src/parts/bolt_pixmap.json`
maps every pixel's color zone + plate + chain position (136 links; two links exceed
the 4-inch string — extension jumpers at chain 87 and 108).

| plate | position | footprint (mm) | black | white | clear | total | pixels |
|-------|----------|----------------|-------|-------|-------|-------|--------|
| B1 | bottom-left | 153 × 255 | TBD | TBD | TBD | TBD | 19 |
| B2 | bottom-right | 257 × 255 | TBD | TBD | TBD | TBD | 39 |
| B3 | top-left | 126 × 295 | TBD | TBD | TBD | TBD | 11 |
| B4 | top-right | 284 × 295 | TBD | TBD | TBD | TBD | 68 |
| | **total** | board 410 × 550 | TBD | TBD | TBD | **TBD** | **137** |

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
1. Wood frame (full sign ≈ 2.07 m wide: board 410 + 60 gap + word 1597; 50–75 mm standoff
   depth; thin back skin as shear web; PSU/controller on one side):
   - **Word zone**: top + bottom rails spanning the 1.6 m word run, catching each piece's
     corner/mid screws (as before).
   - **Board zone**: three horizontal rail lines — bottom edge (screws at y≈6), the y-seam
     line (one rail catches both rows' near-seam screws at y=249 and y=261), and top edge
     (y≈544). Board is 550 tall vs the word's 295, so the board zone's verticals are taller;
     with the word band centered on board height, the word rails land inside the board zone's
     vertical span — share stiles at the 60 mm gap between board and word.
2. Pieces butt left→right (1→6); seams are pre-relieved 0.12 mm/joint. Screw through the
   pre-drilled Ø4.5 holes (6 per piece: 4 corners + 2 mids) with black pan-heads into the rails.
3. Pixels press into collars from behind, chained in path order within each letter, jumper
   slack across seams. 4-inch strings → ~85 mm folds; tuck loose in the plenum
   (Ø3.2 tie-hole pairs along the paths are there if transport demands).
4. Power: **591 px total** (454 word + 137 board) ≈ the 150 W/24 V PSU's full-white
   edge → cap brightness ~80% or add a second PSU. Colors-only scenes draw far less.
5. Board wiring: ONE 137-px data chain (pixels are addressable; color zones are
   software) — follow the `chain` index in `bolt_pixmap.json`; extension jumpers
   at chain 87 and 108; jumper slack across seams like the word pieces.
