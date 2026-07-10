# Bolt-board seam brackets — continuous LEDs across the plate joints

**Goal:** kill the 34–58 mm dark spots where the bolt board's channels cross the
4-plate seams (pixels were kept ≥12.5 mm off every joint), while replacing the
LED-blocking y-seam wood rail with printed splice brackets the plates screw into.

User decisions (2026-07-10): plates NOT yet printed (regenerate freely); keep the
board at **137 pixels** (re-spread, no inventory impact — hard cap 600); captive
M4 hex nuts in the bracket, M4×8 black button-heads from the front; leg sockets
now, snap-in "pizza saver" legs only if the mounted panel flexes. Approach B
(hybrid) chosen over straddle-only (A) and full collar-carrier (C).

## Placement (approach B, verified by simulation)

- Keepout shrinks 12.5 → **9.5 mm** perpendicular (Ø16 collar hole keeps a
  1.5 mm web to the plate edge).
- At each channel/seam crossing, pixels are **pinned** symmetrically at arc
  offset 9.5/sinθ each side. Where the straddle arc exceeds 25 mm — the two
  shallow crossings, 31° at (153, 51) and 29° at (126, 401) — pin **one pixel ON
  the seam** instead; its collar lives in the bracket.
- Even-fill between pins/path ends; pitch solved to land exactly 137
  (sim: 21.5 mm). Existing relaxation de-conflicts tube crossings; pins are
  immovable and never dropped.
- Verified: every seam-adjacent gap ≤ 23.2 mm vs 21.5 running pitch; min pair
  spacing 14.2 (snug band 13–14.5 OK). Remaining big *arc* gaps are the
  bolt-tail hairpin (14.4 mm chord, both walls lit) and crossing pockets lit by
  the crossing tube — both exist in the approved design.

## Brackets (4 white PETG straps + pusher tool)

S1+S2 y=255 (410 mm, two lap-jointed segments), S3 x=126 (295 mm), S4 x=153
(255 mm). ~48 mm wide, 4 mm web, two 8 mm back rails (shallow U). Printed
**front-face-down** so the plate-mating face is flat and an embedded collar
prints in the same first-2 mm-on-bed orientation as plate collars (calibrated
press-fit transfers).

Generated features:
1. **Ø17 chamfered pass-through holes** at every pixel inside the strap
   footprint (pixel presses into its normal plate collar through the bracket).
2. **2 embedded collars** (standard collar STL) flush in the front face at the
   on-seam pixels; Ø14.5 flange pocket behind (bracket is exactly 4 = 2+2).
   Pixel seats 2 mm deeper: dome tip 17.5 mm from lens — inside the validated
   10–20 window. Plates get a **Ø13 bite** split across the mating edges
   (through black + white liner). No plate collar at these two positions.
3. **M4 nut pockets** (7.2 AF, 3.2 deep, opening back) paired across the seam
   every ~60–80 mm in black-field intervals; generator asserts ≥2 pairs per
   segment + a pair per T-junction quadrant, and that screw holes never pierce
   a channel (new check). ~15 pairs ≈ 30 × M4×8 + nuts.
4. **Leg sockets** Ø10.2 in 16 mm bosses at the two T-junctions + y-midspan;
   legs printed later at measured plenum depth if needed.

No wire slots needed: assembly is brackets-first (plates butted face-down →
brackets screwed on → panel to frame by perimeter screws → pixels press in from
behind through the bracket holes → chain). Wires always route behind the
bracket plane. Pusher = Ø13.5 slotted tube for seating pixels through Ø17 holes.

## Pipeline

`boltboard.py` gains the anchored placement + emits `bracket_layout.scad` and
bite positions in `board_layout.scad`; new `src/parts/bracket.scad` → white
STLs (single color, plain STL). Plates re-render via `build_board.sh` with mesh
audit + 2D-projection visual check. `bolt_pixmap.json`/chain regenerate.
Assembly card: y-seam rail removed from the frame plan; perimeter rails only.
