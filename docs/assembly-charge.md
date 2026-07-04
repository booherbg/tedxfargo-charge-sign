# CHARGE billboard — print & assembly card

Six 3-color pieces (`stl/piece<N>_3color.3mf`), cut preview / seam map:
`docs/sign-preview/cut-preview.html`. Specs: `docs/locked-specs.md`,
`docs/superpowers/specs/2026-07-03-billboard-panelize-design.md`.

## Pieces (rendered weights, PETG @1.27)

| # | letter | footprint (mm) | black | white | clear | total | pixels |
|---|--------|----------------|-------|-------|-------|-------|--------|
| 1 | C | 295 × 295 | 226 g | 60 g | 47 g | 333 g | 61 |
| 2 | H | 316 × 295 | 236 g | 78 g | 61 g | 374 g | 78 |
| 3 | A | 296 × 295 | 224 g | 63 g | 50 g | 337 g | 63 |
| 4 | R | 292 × 295 | 253 g | 80 g | 62 g | 395 g | 80 |
| 5 | G | 300 × 295 | 235 g | 79 g | 62 g | 377 g | 81 |
| 6 | E | 290 × 295 | 240 g | 77 g | 61 g | 378 g | 79 |
| | **total** | face 1597 × 295 | 1414 g | 437 g | 343 g | **2194 g** | **442** |

## Slicing (per validated specs)
- Filaments: **1 = black PETG, 2 = white PETG (the two nozzles), 3 = clear PETG sharing the
  WHITE nozzle** — black never swaps; the print's ONLY filament change is white→clear at the
  lens (~z21), whose residue hides in the white weld zone. **Prime tower OFF, purge to chute**
  (no plate room for a tower, and one benign swap doesn't need it).
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
4. Power: ~442 px ≈ 130 W full-white ≈ the 150 W/24 V PSU's edge → cap brightness ~80%
   or add a second PSU.
