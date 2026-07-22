# Bolt backer frame — printed torsion box, vented, internal PSU

**Goal:** give the bolt board (410×550, 4 plates + 4 seam straps, no frame today)
a fully printed enclosure: stiff, clean, fully closed back with vent slits,
wall-hung or free-standing, controller AND PSU fully enclosed — ONE mains cable
through a side-wall gland and that's it. Experiment to replace the heavy
carpenter-built wood frame style used on the word sign.

User decisions (2026-07-21, three revision rounds same day): **picture-frame
torsion box** over sparse ladder and monocoque tub; **internal PSU from day
one** — plan for the whole 30-mm-tall LRS family (**LRS-50 / 75 / 100**, one
tray profile); cavity **36 mm** (tray floor 4 over the flange + PSU 30 + 2
clear; wall-FACE mounting like the word sign's exterior would need 50+ mm
walls, rejected); fully closed back **with vent slits**; snap-in **feet** in
bottom-rail slots; **two thick top handles** for carrying + wall-hanging
(replace the loops/keyhole idea); controller = **Gledopto Elite 2D-EXMU
(GL-C-616WL, 129×50×23)** inside, shell end-tab screws; **one PG9 gland,
printed open** — no knockouts to punch or drill, alternates are swap plates.
M3 self-tap into printed bosses now, bores sized so M3 heat-set inserts are a
later drop-in.

Total sign body ≈ 40 mm behind the plate front (plate 2 + cavity 36 + panel
2.4), plus the front shell as built.

**V1 AS-BUILT CONFIGURATION (2026-07-22, user simplification):** controller
mounts OUTSIDE on the left-wall pads (`fr_ctl_ext`, screws at the probed
122 × 26 diagonal, body spans y ≈ 96..225), fed by a plug-in PSU — nothing
electrical inside. One **PG7 gland threaded directly into the 3.0 mm wall**
(Ø12.5 hole at y = 275, z = 19; 3.0 ≤ the 3.5 clamp limit, so no plate)
passes the single jacketed 3 × 18 AWG V+/V−/D line into the cavity, 50 mm
(2 in) above the controller's top/output end for working room — the position
is capped by the y = 300 segment joint (asserted). Everything below —
internal trays, PSU patterns, gland plate — is BUILT and KEPT as the
enclosed-future path; `GLAND_PLATE = 1` in tools/boltframe.py restores the
plate opening for the internal-PSU pivot (rails reprint required then).

## Frame rails (4 corner-L segments, white PETG)

- C-channel: **flange** 16 × 4 mm behind the plate perimeter with 14 pilot
  bosses at the existing `bb_scr` kind-0 positions (the wood-rail band —
  keepout already validated); plates screw down from the front, screws they
  already have. **Outer wall** 3 mm. **AS-BUILT AMENDMENT:** the 2 mm front
  reveal is a separate **snap-on trim strip** (frame_parts PART=6, groove in
  the wall outer face) — one-piece lip + rail can't print support-free, and
  the split lets rails print FLANGE-DOWN cleanly; `reveal=0` = don't print
  trim. The trim never covers a screw: holes sit 6 mm from the plate edge,
  hole rim at 3.75, trim covers 2 (generator asserts). Assembly: sign
  face-down, segments laid flange-down onto the plate backs, dovetails
  joined, flip once, drive the 14 screws, snap trim on last.
  **Ledge** 8 × 4 mm at cavity depth 36 with M3 panel bosses.
- Segments are corner-Ls meeting at **x=205 / y=300** (AS-BUILT: y moved
  275→300 — the probe caught the joint splitting the (6,275)/(404,275)
  bosses, and 300 also clears the S1/S2 strap band; asserted now). Joint =
  printed dovetail key in an inner-face pocket + M3 cross-screws from
  outside through wall+pad into the key.
- **Handles ×2** on the top rail near the corners: thick printed bars
  (grip opening ≈ 100 × 28, body ≥ 14 thick), each bolted with 2 × M4 +
  washer/nut into top-rail bosses. Back faces sit FLUSH with the back-panel
  plane so the sign hangs flat on a wall — the grip opening doubles as the
  hang point (screw head, cleat, chain, or zip tie through it) and as the
  carry handle. Printed lying flat so layer lines run along the load path.
- Bottom rail: 2 snap sockets in the underside for **snap-in feet**
  (AS-BUILT: split-prong arrowhead tab + barb pocket — a true T-slot can't
  insert from below; squeeze the prongs from inside to release; blade
  ≈ 90 mm fore-aft); sign is wall-hung with feet out.

## Strap interface (folds in the chirality reprint)

- **S3/S4 reprint** (already required — chirality fix 6edb95e): rails raised
  8 → 32 mm (web 4 + 32 = 36 = cavity depth) with M3 bosses on top; they become
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
  into the existing leg sockets, M3 boss on top at panel height (36).
- Plates, pixels, wiring untouched.

## Back panels (4 quadrants, vented, removable)

- ≈ 209 × 279 each (bed-fit), 2.4 mm skin + ribs, half-lap rebates at
  panel-to-panel edges so they register flush. M3 screws into ledge bosses,
  raised S3/S4 rail bosses, and S1/S2 leg tops — back comes off without
  touching the plates.
- Vents: angled louver slits (light-tight, dust-shedding), intake rows along
  the bottom panels, exhaust rows in the top third; one consistent pattern,
  plus a small cluster over the controller (mic aperture for audioreactive +
  convection over the equipment corners — PSU and controller both live up
  top, so the exhaust rows do double duty).

## Internal equipment (top corners — the verified pixel-free zones)

Placement is pinned by a clearance sweep against the real pixel map (the
originally-sketched lower-left PSU spot FAILED it — a pixel sat inside the
rect; the bolt's bottom and diagonal channels fill the lower half). The two
clean zones are the TOP corners. Devices lie FLAT on 4-mm tray floors that
span the flange band, integrated into the top corner-L segments; devices stay
with the sign when panels come off.

- **PSU tray (upper-LEFT)**: zone x ≈ 1..98, y ≈ 407..536 (AS-BUILT: slid
  down 8 so the top ledge bosses clear the tray) — 28.6 mm to the nearest
  pixel, 4 mm to S3's raised rail. Fits the whole family in portrait
  (all 30 tall, L=3.0 bottom taps, M3×7 through the 4 mm floor = 3 mm in):
  - LRS-50 (case 239A, 99×82) + LRS-75 (240A, 99×97): shared **slots** at
    length 20.5/75.5 spanning width 40.5→45.5 (AS-BUILT: the two patterns
    are 5 mm apart — one slot serves both)
  - LRS-100 (case 238A, 129×97): round holes (78, 34) + (78, 67)
  Terminals point DOWN toward the cavity. Before buying: match the voltage
  to the pixel string — LRS is 5/12/24 V.
- **Controller tray (upper-RIGHT)**: Elite vertical, zone x ≈ 342..392,
  y ≈ 405..534 (10.7 mm to the nearest pixel — generator asserts ≥ 8.5 + 2).
  Two bosses at the shell's end screws — **122.0 × 26.0 diagonal, Ø4.6**
  (probed from docs/elite2d_mount.stl; no adapter plate needed). Terminals
  face the cavity; WiFi works through PETG. USB-C/Ethernet/button need the
  panel off — accepted, WLED is OTA.
- **Wiring run**: mains in low on the left wall → up the flange shelf to the
  PSU AC end (cord FG lands on the LRS FG terminal); DC across the top rail
  channel to the controller INPUT; OUTPUT drops to the chain entry at
  (194, 180). All runs < 500 mm.
- **Gland plate** low on the LEFT side wall (side entry keeps free-standing
  on the feet stable; low = hidden, cord drops to the floor): a 2.5-mm-thick
  screwed-on plate (2 × M3 into wall bosses) over a rectangular opening.
  V1 plate ships with ONE **PG9** hole printed OPEN (Ø15.2, clamps 4–8 —
  takes a 3-wire SVT mains cord; no drilling, no punch-outs). Variant plates
  (PG7 Ø12.5, PG11 Ø18.6, or two-hole for a word-sign link) are 5-minute
  prints — swap the plate, not the rail. **Seats stay ≤ 3.5 mm** — PG thread
  is ~8 mm and the locknut needs ~5 (user has over-thickened walls before;
  generator asserts). Fusing and relays live on the controller.

## Fasteners / material / mass

White PETG throughout (matches straps). M3 self-tap bosses (Ø2.8 pilot),
boss OD 7 so a Ø4.0 counterbore upgrade takes M3 heat-set inserts later.
Plate-to-flange reuses the 14 existing wood screws. Estimate ≈ 1.3–1.7 kg
total: 4 rails (2 with equipment trays) + 4 panels + 2 handles + 2 feet +
3 legs + gland plate (+ S3/S4 reprint ~140 g at the taller rails).

## Build & verify

- New generator emits `frame_layout.scad` (rail segments, boss positions from
  `bb_scr`, panel outlines, tray anchors + PSU hole patterns, gland position,
  handle bosses) + part scads in the existing `-D PART=` style; build lines
  added to build_board.sh. Generator asserts: both tray rects ≥ 11 mm from
  every `bb_px`/`bb_bite`; PSU top clearance ≥ 2; tray clear of S3 rails.
- qa_board.py grows frame checks: flange bosses == `bb_scr` kind-0 positions
  (axis-aware — see the chirality lesson), every segment/panel fits 316×295,
  panel screw bosses land on ledge/strap/leg supports, joint keys clear
  screw holes, reveal lip clears every `bb_scr` hole rim, gland-plate seat
  thickness ≤ 3.5 (PG clamp limit), handle back faces coplanar with the
  panel plane.
- Print order: S3/S4 straps first (unblocks the strap swap), then rails,
  panels, handles, feet, gland plate.

## Config params (all have working defaults)

`psu` (LRS-50/75/100 hole pattern, default all), `gland` (PG9 default /
PG7 / PG11 / two-hole link variant), `reveal` (2, 0 disables), `nut_pocket`
(off), supply-cord diameter only if it falls outside PG9's 4–8 mm clamp.
