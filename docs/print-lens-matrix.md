# Print card — lit-lens diffusion matrix (morning run)

Goal: print 8 diffuser test cells in one dual-material job, light them, and pick the
recipe that glows most evenly. Full rationale: `superpowers/specs/2026-06-29-integrated-lens-design.md`.

## Files
- `stl/matrix_white.stl` → **white PETG** (nozzle 1)
- `stl/matrix_clear.stl` → **clear/natural PETG** (nozzle 2)

(Regenerate any time with `./build.sh`.)

## Bambu Studio (H2D)
1. Import **both** STLs.
2. Select both → right-click → **Assemble** (they're co-registered to the same
   origin, so this keeps them perfectly aligned as one 2-part object).
3. Assign filaments per part: white STL → white PETG, clear STL → clear PETG.
4. **Orientation:** leave as-is — it's already plate-down (collar tray on the bed,
   optics up). Do **not** flip.
5. Global settings: 0.16–0.20mm layers, ≥3 walls, **strong part cooling** (the A/R
   clear faces bridge ~30mm — cooling keeps that clean; a little sag is fine, it
   diffuses). 5–6 solid top layers on the clear.
6. **Cell B1 only** (6th cell, 6 dots): give it a per-object setting → sparse infill
   **gyroid, ~15%**, **1 top layer**, so light passes through the lattice. (If you
   skip this it just prints as a solid clear block — still works, just not volumetric.)

## After printing
- Press a 12mm bullet pixel into each collar from the **back**.
- Light all 8 (white-ish, mid brightness). Look straight at the faces in a dim room.
- **Read the dot code** on the tray bottom (1–8) to know which is which.

## Cell legend (dots = cell #)
| Dots | Cell | What it is | Expect |
|---|---|---|---|
| 1 | A0 | cavity, **no mask** | brightest, but a center hotspot |
| 2 | A1 | perforated dot d14 @5mm | **even** (predicted best), ~mild dimming |
| 3 | A2 | perforated dot d16 | even, slightly wider block |
| 4 | A3 | perforated dot d14, deeper (gap18) | even, a touch softer |
| 5 | R1 | white reflector cone | bright, partial hotspot reduction |
| 6 | B1 | clear gyroid fill | even volumetric glow, dimmer ("alien") |
| 7 | C1 | clear + 90° TIR cone | bright, beam spread sideways |
| 8 | C2 | clear + 60° TIR cone | bright, more sideways spread |

## What to look for
- **Even, sourceless** glow (no bright dot over the LED) = winner.
- If a cell shows a **dark center** → its perforations clogged (over-extrusion); tell
  me and I'll open the holes up. (The physics sim shows an *opaque* dot inverts to a
  dark center — that's the tell.)
- Note brightness vs evenness per cell; we lock the winning cross-section and move it
  onto the TEDxFargo letter strokes.
```
tray layout (top view):
  [A0][A1][A2][A3]      <- masked-cavity sweep
  [R1][B1][C1][C2]      <- reflector / gyroid / TIR
```
