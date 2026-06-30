# Locked specs (validated)

Finalized, print-validated parameters. Change only with a new test.

## Bullet pixel — the hardware everything keys off
- dome **Ø8**, barrel **Ø12**, flange **Ø13.6 × 2mm**, dome-tip → flange **5.5mm**
- dome protrusion above plate front (`dome_clear`) = **4.0mm**
- plate bore (`pixel_through`) = **12.3mm**; calibrated press-fit collar `assets/bullet-collar.stl` (bore ~Ø12.19)

## Bolt lens fit ✅ printed & snapped
- `bolt_lip_clear = -0.2` → lip **Ø18.2** into the **18.0** channel (0.2mm interference)
- Perfect snap-in, **material-robust**: validated in **clear PETG** (on a white-PLA base) *and* **clear PLA**.
- Dialed via `lens_fit_*` slices (0.4 → -0.2); 0.6 and even 0.1 clearance were too loose / fell out.

## Diffuser matrix — pixel clearance ✅ collision-verified
- `led_void = 14.0` — pixel keep-out Ø (barrel 12 + clearance + hole-shrink)
- `led_clear = 2.5` — vertical headroom above the dome tip before any solid optic
- masks ride **flared floor legs** (self-supporting, feet splay clear of the barrel) → **no internal support**
- Verified by `src/parts/lens_pixel_collision.scad`: pixel envelope intersects nothing in all 8 cells

## Diffuser print recipe — Adafruit neon, verified (see `print-lens-matrix.md`)
- **0.16mm** layer · **0.42mm** line (slicer default ok) · **2 walls** · **10% gyroid** · **6 top/bottom**
- supports **off** · small brim · bridge fan on (A/R faces bridge ~30mm)
- **same polymer family for both colors** (both PLA *or* both PETG — not mixed; PLA↔PETG bonds poorly)
- PETG preferred near LEDs for heat; PLA fine for prototyping / this test

## Two-color file
- `stl/lens_matrix_2color.3mf` — Bambu-native, white → filament 1 / clear → filament 2
- regenerate: `./build.sh` then
  `python3 tools/make_3mf.py stl/matrix_white.stl stl/matrix_clear.stl stl/lens_matrix_2color.3mf`

## Still open
- Diffuser **winner** — pick the best-glowing cell once the printed matrix is lit.
- That winning cross-section then transfers to the **TEDxFargo letter strokes**.
