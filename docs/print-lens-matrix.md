# Print card — lit-lens diffusion matrix

Goal: print 8 diffuser test cells in one dual-material job, light them, and pick the
recipe that glows most evenly. Full rationale: `superpowers/specs/2026-06-29-integrated-lens-design.md`.

## File to load
- **`stl/lens_matrix_2color.3mf`** — open this one file. It loads as a single object
  with two parts already mapped: **white body → filament 1, clear optic → filament 2.**

Regenerate if it gets overwritten:
```
./build.sh        # rebuilds stl/matrix_white.stl + matrix_clear.stl (source)
python3 tools/make_3mf.py stl/matrix_white.stl stl/matrix_clear.stl stl/lens_matrix_2color.3mf
```

## Bambu Studio (H2D)
1. Open the `.3mf`. (You'll get a "saved outside Bambu" banner — normal; the part→
   filament assignment still loads.)
2. Set **filament slot 1 = white, slot 2 = clear**. Use the **same polymer family for
   both** (both PLA *or* both PETG) — a PLA+PETG mix bonds poorly at the seam.
3. **Orientation:** leave as-is — already plate-down (collar tray on the bed, optics
   up). Do **not** flip.

## Slicer recipe — Adafruit neon settings (verified), go all-in
Source: https://learn.adafruit.com/led-neon-signs-with-neopixels/3d-printing

| Setting | Value |
|---|---|
| Layer height | **0.16mm** (0.20 = faster / Adafruit's implied default; avoid ≥0.24 — visible striping) |
| Line width | default **0.42mm** is fine (Adafruit says 0.4 nominal; 0.02 doesn't matter) |
| Wall loops | **2** |
| Infill | **10% gyroid** |
| Top/bottom layers | **6** |
| Supports | **off** (sealed cavities — can't remove internal supports anyway) |
| Brim | 3–5mm (adhesion for the thin walls) |
| Cooling | bridge fan **on** (A0–A3/R1 clear faces bridge ~30mm); don't crank the global fan on PETG |

Material/temps: Adafruit uses **PLA @ 220°C / 60°C bed** — match that for a literal
replication, or use **PETG** (Bambu PETG profile temps) for heat tolerance near the LEDs.
Either is fine for this test; just keep both colors the same family.

This one recipe covers all 8 cells. *Optional:* for a "purer" gyroid in the B1 cell
(light straight through the lattice, no solid skin), give it **1 top layer** instead of
6 — but that needs B1 as its own file; ask and I'll split it out.

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
