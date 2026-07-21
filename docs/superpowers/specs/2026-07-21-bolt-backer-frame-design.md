# Bolt backer frame — printed torsion box, vented, PSU-ready

**Goal:** give the bolt board (410×550, 4 plates + 4 seam straps, no frame today)
a fully printed enclosure: stiff, clean, fully closed back with vent slits,
wall-hung or free-standing, controller and (future) PSU fully enclosed — one
power lead through a gland and that's it. Experiment to replace the heavy
carpenter-built wood frame style used on the word sign.

User decisions (2026-07-21, revised same day: everything inside): **picture-
frame torsion box** over sparse ladder and monocoque tub; cavity **34 mm** —
clears the deepest flat-mounted device (LRS-50 stands 30, Elite 23; wall-FACE
mounting like the word sign's exterior would need a 50+ mm wall and was
rejected as too chunky); fully closed back **with vent slits**; snap-in
**feet** in bottom-rail slots; controller = **Gledopto Elite 2D-EXMU
(GL-C-616WL, 129×50×23 mm)** mounted INSIDE — its shell screws down by the
two end tabs (per the word-sign install photo), fuses/relays onboard; PSU
(LRS-50, later) also inside; the only penetrations are **two gland knockouts**
bottom-left (power in + spare for a word-sign link cable). M3 self-tap into
printed bosses now, boss bores sized so M3 heat-set inserts are a later
drop-in (user: heat-set not needed yet).

## Frame rails (4 corner-L segments, white PETG)

- C-channel: **flange** 16 × 4 mm behind the plate perimeter with 14 pilot
  bosses at the existing `bb_scr` kind-0 positions (the wood-rail band —
  keepout already validated); plates screw down from the front, screws they
  already have. **Outer wall** 3 mm, rising to a 2 mm front **reveal lip**
  wrapping the plate edge (hides plate edges/seams; `reveal=2` param, zero to
  disable). The lip NEVER covers a screw: perimeter holes sit 6 mm from the
  plate edge, so the Ø4.5 hole rim starts at 3.75 — the 2 mm lip leaves
  1.75 mm clear (generator asserts lip + head clearance). The lip + flange
  form the channel the plate edges seat in: the frame assembles AROUND the
  intact sign (hook each corner-L's lip over the plate front, rotate down
  onto the flange, join the dovetails), then the 14 screws lock it.
  **Ledge** 8 × 4 mm at cavity depth 34 with M3 panel bosses.
- Segments are corner-Ls (legs ≈ 275 + 205, bbox fits 316×295) meeting at the
  4 edge midpoints, clear of all screw holes. Joint = printed dovetail key
  slid in from the back + one M3 cross-screw per joint.
- Top rail: 2 chain/zip-tie loops at the corners + 2 keyhole slots in the flat.
  Bottom rail: 2 through T-slots in the underside for **snap-in feet** (spring
  tab + click ridge, blade ≈ 90 mm fore-aft); sign is wall-hung with feet out.

## Strap interface (folds in the chirality reprint)

- **S3/S4 reprint** (already required — chirality fix 6edb95e): rails raised
  8 → 30 mm (web 4 + 30 = 34 = cavity depth) with M3 bosses on top; they become
  the panels' mid-span supports. Pass-hole chamfers already cut through rails.
- **Captive hex pockets dropped on the reprint** (user 2026-07-21: nut depth/
  alignment in a pocket is fiddly — prefers flat + washer): screw bores become
  plain Ø4.5 through-holes with a FLAT back face; washer + M4 nut tightened
  from the open back (panels aren't on yet at strap-install time; the 38 mm
  gap between the raised rails leaves driver room). Screw length changes:
  plate 2 + web 4 + washer + nut ≈ 10 — the existing M4×8 are too short,
  **use M4×10 (flush) or M4×12**. `nut_pocket` param restores the old pocket
  if wanted. S1/S2 keep their pockets (installed, working).
- **S1/S2 stay installed** (correct as printed): three Ø10 printed legs drop
  into the existing leg sockets, M3 boss on top at panel height.
- Plates, pixels, wiring untouched.

## Back panels (4 quadrants, vented, removable)

- ≈ 209 × 279 each (bed-fit), 2.4 mm skin + ribs, half-lap rebates at
  panel-to-panel edges so they register flush. M3 screws into ledge bosses,
  raised S3/S4 rail bosses, and S1/S2 leg tops — back comes off without
  touching the plates.
- Vents: angled louver slits (light-tight, dust-shedding), intake rows along
  the bottom panels, exhaust rows in the top third; one consistent pattern,
  plus a small cluster over the controller (mic aperture for audioreactive +
  convection over the equipment corners).

## Internal equipment corners (left rail)

The bolt runs diagonally, so both left corners of the board are pixel-free.
Devices lie FLAT against the plate back, snugged to the inner wall, on tray
bosses integrated into the two left corner-L rail segments (devices stay with
the sign when panels come off; wiring never leaves the box).

- **Controller (upper-left)**: Elite vertical along the rail, footprint
  129 × 50 in the empty zone x < 100, y > 400; two bosses at the shell's
  end-screw positions — **diagonal, 122.0 apart lengthwise × 26.0 across, at
  12/38 of the 50 width, Ø4.6 clearance** (probed from docs/elite2d_mount.stl,
  the word-sign adapter plate; no adapter needed here, controller screws
  straight to the tray). Terminals face the cavity; antenna + WiFi work
  through PETG (RF-transparent). USB-C/Ethernet/function button need the
  adjacent panel off — accepted, WLED is OTA.
- **PSU tray (lower-left, later)**: LRS-50 boss footprint (99 × 82, stands 30)
  next to the glands. Bottom mounting per datasheet (case 239A): **2 × M3 on
  the width centerline (40.5 from the edge), 55.0 apart (at 20.5 and 75.5
  along the 99 length); screw penetration into the case MAX 3 mm** (L=3.0 —
  longer screws can reach the board). M3×6 through the 3 mm tray floor lands
  exactly at 3. The case also has 2 × M3 side holes (74 apart, mid-height,
  L=5) as a fallback orientation. Costs nothing until used. Before buying:
  confirm the supply voltage matches the pixel string — LRS-50 is 5/12/24 V.
- **Gland plate** on the bottom-left outer wall: a small screwed-on plate
  (2 × M3 into wall bosses) over a rectangular opening, carrying both cable
  entries — swap the plate, not the rail. Default **PG9** (Ø15.2 bore,
  clamps 4–8 mm — covers 3-wire SVT mains cord AND the DC lead; user has
  stock); `gland` config param generates PG7 (Ø12.5) or PG11 (Ø18.6)
  variants. **Plate is 2.5 mm thick at the gland seats** — PG thread length
  is only ~8 mm and the locknut needs ~5, so anything over ~3.5 mm can't
  clamp (user has been bitten by too-thick walls; generator asserts this).
  Second hole = blanked spare for a word-sign link. Fusing and relays live
  on the controller — no separate fuse holder.

## Fasteners / material / mass

White PETG throughout (matches straps). M3 self-tap bosses (Ø2.8 pilot),
boss OD 7 so a Ø4.0 counterbore upgrade takes M3 heat-set inserts later.
Plate-to-flange reuses the 14 existing wood screws. Estimate ≈ 1.2–1.6 kg
total: 4 rails (2 with equipment trays) + 4 panels + 2 feet + 3 legs
(+ S3/S4 reprint ~130 g at the taller rails).

## Build & verify

- New generator emits `frame_layout.scad` (rail segments, boss positions from
  `bb_scr`, panel outlines, equipment-tray anchors, gland positions) + part
  scads in the existing `-D PART=` style; build lines added to build_board.sh.
  Generator asserts both trays sit fully in pixel-free zones (min distance to
  every `bb_px`/`bb_bite`).
- qa_board.py grows frame checks: flange bosses == `bb_scr` kind-0 positions
  (axis-aware — see the chirality lesson), every segment/panel fits 316×295,
  panel screw bosses land on ledge/strap/leg supports, joint keys clear
  screw holes, reveal lip clears every `bb_scr` hole rim, gland-plate seat
  thickness ≤ 3.5 (PG clamp limit).
- Print order: S3/S4 straps first (unblocks the strap swap), then rails,
  panels, feet.

## Measure-at-build inputs (config params, not blockers)

Existing supply-lead diameter (gland bore); plate-edge reveal preference
(2 mm default, 0 disables). Controller screw geometry is NOT one of these —
it's pinned by docs/elite2d_mount.stl (122.0 × 26.0 diagonal, Ø4.6).
