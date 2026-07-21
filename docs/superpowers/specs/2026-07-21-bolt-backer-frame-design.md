# Bolt backer frame — printed torsion box, vented, PSU-ready

**Goal:** give the bolt board (410×550, 4 plates + 4 seam straps, no frame today)
a fully printed enclosure: stiff, clean, fully closed back with vent slits,
wall-hung or free-standing, controller accessible from outside. Experiment to
replace the heavy carpenter-built wood frame style used on the word sign.

User decisions (2026-07-21): **picture-frame torsion box** over sparse ladder
and monocoque tub; cavity **34 mm** (PSU-ready — Mean Well LRS-50 drops in
later; wiring-only for now, PSU stays external); fully closed back **with vent
slits**; snap-in **feet** in bottom-rail slots; controller = **Gledopto Elite
2D-EXMU (GL-C-616WL, 129×50×23 mm)** in an external side pod — it carries its
own fuses/relays and screw-down feet, so the pod is a tray + cover, no cradle;
pod on the **left rail, lower third** (bolt data chain enters at (194, 180),
nearest the bottom-left). M3 self-tap into printed bosses now, boss bores
sized so M3 heat-set inserts are a later drop-in (user: heat-set not needed yet).

## Frame rails (4 corner-L segments, white PETG)

- C-channel: **flange** 16 × 4 mm behind the plate perimeter with 14 pilot
  bosses at the existing `bb_scr` kind-0 positions (the wood-rail band —
  keepout already validated); plates screw down from the front, screws they
  already have. **Outer wall** 3 mm, rising to a 2 mm front **reveal lip**
  wrapping the plate edge (hides plate edges/seams; `reveal=2` param, zero to
  disable). **Ledge** 8 × 4 mm at cavity depth 34 with M3 panel bosses.
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
- **S1/S2 stay installed** (correct as printed): three Ø10 printed legs drop
  into the existing leg sockets, M3 boss on top at panel height.
- Plates, pixels, wiring untouched.

## Back panels (4 quadrants, vented, removable)

- ≈ 209 × 279 each (bed-fit), 2.4 mm skin + ribs, half-lap rebates at
  panel-to-panel edges so they register flush. M3 screws into ledge bosses,
  raised S3/S4 rail bosses, and S1/S2 leg tops — back comes off without
  touching the plates.
- Vents: angled louver slits (light-tight, dust-shedding), intake rows along
  the bottom panels, exhaust rows in the top third; one consistent pattern.
- **PSU provision** (lower-left panel, beside the pod): LRS-50 boss footprint +
  a mains-inlet knockout. Costs nothing until used. Before buying: confirm the
  supply voltage matches the pixel string — LRS-50 comes in 5/12/24 V.

## Controller pod (left rail, lower third)

- External sidecar on the outer wall: interior ≈ 140 × 60 × 32, flat floor with
  pilot bosses matching the Elite's screw-down feet (**foot spacing measured
  from the physical unit** — config param, gates pod print only), antenna
  clearance port, vented snap-on cover.
- Grommeted pass-through into the cavity for data/power to the board; strain-
  relief gland at the pod's bottom face for the external supply lead. Fusing
  and relays live on the controller itself — no separate fuse holder.

## Fasteners / material / mass

White PETG throughout (matches straps). M3 self-tap bosses (Ø2.8 pilot),
boss OD 7 so a Ø4.0 counterbore upgrade takes M3 heat-set inserts later.
Plate-to-flange reuses the 14 existing wood screws. Estimate ≈ 1.2–1.6 kg
total: 4 rails + 4 panels + pod + 2 feet + 3 legs (+ S3/S4 reprint ~130 g at
the taller rails).

## Build & verify

- New generator emits `frame_layout.scad` (rail segments, boss positions from
  `bb_scr`, panel outlines, pod anchor) + part scads in the existing
  `-D PART=` style; build lines added to build_board.sh.
- qa_board.py grows frame checks: flange bosses == `bb_scr` kind-0 positions
  (axis-aware — see the chirality lesson), every segment/panel fits 316×295,
  panel screw bosses land on ledge/strap/leg supports, joint keys clear
  screw holes.
- Print order: S3/S4 straps first (unblocks the strap swap), then rails,
  panels, pod, feet.

## Measure-at-build inputs (config params, not blockers)

Elite 2D-EXMU foot screw spacing; existing supply-lead diameter (gland bore);
plate-edge reveal preference (2 mm default, 0 disables).
