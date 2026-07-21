# Bolt Backer Frame Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and render every part of the printed torsion-box frame for the
bolt board (spec `docs/superpowers/specs/2026-07-21-bolt-backer-frame-design.md`),
with layout-level asserts, QA checks, build lines, and a committed web preview.

**Architecture:** A new generator `tools/boltframe.py` reads the existing
`board_layout.scad` / `bracket_layout.scad` (source of truth for plates, pixels,
screws, straps) and emits `src/parts/frame_layout.scad` + runs clearance
asserts. Three OpenSCAD part files consume it: `frame.scad` (4 corner-L rail
segments, `-D SEG=`), `frame_panel.scad` (4 vented quadrant panels,
`-D PANEL=`), `frame_parts.scad` (handle/foot/leg/key/gland-plate/trim/coupon,
`-D PART=`). The strap part `bracket.scad` gains two `-D`-able params
(`bk_rail_h`, `bk_nut_pocket`) so the S3/S4 reprint builds tall flat-seat
variants from the SAME source. QA and preview follow the house pattern.

**Tech Stack:** Python 3 (no deps), OpenSCAD CLI, existing qa_board.py probe
helpers (`read_stl`, `vset`, `ring_r`).

## Global Constraints

- Board 410 × 550; plate back = z 0, cavity grows +z; plate front at z −2.
- CLR 0.5, WALL 3.0, CAVITY 36.0, PANEL_T 2.4, WALL top 38.4 (= 36 + 2.4).
- FLANGE 16 wide × 4 thick (z 0..4); LEDGE 8 wide × 4 thick (z 32..36).
- Frame outer rect −3.5..413.5 × −3.5..553.5; segment joints at x=205, y=275.
- **Print orientation decision (amends spec):** rails print FLANGE-DOWN
  (flange + tray floors on the bed, wall rising 38.4, 45° chamfer under the
  ledge). The 2 mm reveal lip therefore CANNOT be part of the rail — it is a
  separate snap-on **trim strip** (PART=6); `reveal=0` = don't print trim.
- Straps S3/S4 rebuild with `-D bk_rail_h=32 -D bk_nut_pocket=0` (web 4 +
  32 = 36); S1/S2 untouched.
- Chirality insurance: every mirrored-part lesson applies — tray hole
  patterns get a 1.2 mm printable COUPON (PART=7) and `ctl_diag` / PSU
  patterns stay parametric until the coupon is verified against the units.
- Bed cap 316 × 295. All M3 pilots Ø2.8, boss OD 7. White PETG.
- Commit after every task; `openscad` binary from PATH (as build_board.sh).

---

### Task 1: `tools/boltframe.py` — layout generator with clearance asserts

**Files:**
- Create: `tools/boltframe.py`
- Output (generated): `src/parts/frame_layout.scad`

**Interfaces:**
- Consumes: `src/parts/board_layout.scad` (`bb_scr`, `bb_px`, `bb_bite`),
  `src/parts/bracket_layout.scad` (`bk_span`, `bk_socket`).
- Produces `frame_layout.scad` variables (all consumed by Tasks 3–5, 6, 8):
  `fr_face, fr_clr, fr_wall, fr_cavity, fr_panel_t, fr_flange_w, fr_flange_t,
  fr_ledge_w, fr_ledge_t, fr_reveal, fr_boss` (14 pts), `fr_joint` (=[205,275]),
  `fr_panels` (4 rects), `fr_panel_scr` (per-panel [x,y] lists),
  `fr_ledge_boss, fr_rail_boss` (S3/S4 rail-top pts), `fr_leg` (3 pts),
  `fr_tray_psu, fr_psu_holes` (6 pts), `fr_tray_ctl, fr_ctl_holes` (2 pts),
  `fr_gland` (=[cy, cz]), `fr_handle` (2 spans + bolt xs), `fr_feet` (2 xs),
  `fr_vent_rows`, `fr_mic` (=[367,470]).

- [ ] **Step 1: Write the generator** — full content:

```python
#!/usr/bin/env python3
"""Backer-frame layout for the bolt board (spec 2026-07-21).
Reads board_layout/bracket_layout (truth), emits frame_layout.scad.
Every placement is asserted against the pixel map — the lower-left PSU
lesson: never place cavity equipment without sweeping bb_px."""
import math, re

def grab(txt, name):
    return eval(re.search(name + r"\s*=\s*(\[.*?\]);", txt, re.S).group(1))

bl = open("src/parts/board_layout.scad").read()
bk = open("src/parts/bracket_layout.scad").read()
SCR, PX, BITE = grab(bl, "bb_scr"), grab(bl, "bb_px"), grab(bl, "bb_bite")
SOCK = grab(bk, "bk_socket")
FW, FH = 410.0, 550.0
CLR, WALL, CAV, PT = 0.5, 3.0, 36.0, 2.4
FLW, FLT, LGW, LGT, REV = 16.0, 4.0, 8.0, 4.0, 2.0
JX, JY = 205.0, 275.0
PXPTS = [(p[0], p[1]) for p in PX] + [tuple(b) for b in BITE]

def rect_px_clear(r, need, what):
    x0, y0, x1, y1 = r
    d = min(math.hypot(max(x0-x, 0, x-x1), max(y0-y, 0, y-y1))
            for x, y in PXPTS)
    assert d >= need, f"{what}: {d:.1f} < {need} to a pixel"
    return d

# 14 frame bosses = the wood-screw band (validated keepout)
boss = [(s[0], s[1]) for s in SCR if s[2] == 0]
assert len(boss) == 14, "expected 14 perimeter wood-screw points"
for x, y in boss:   # reveal lip (trim) never covers a hole rim
    e = min(x, y, FW - x, FH - y)
    assert e - 2.25 >= REV + 0.5, f"lip too close to screw at {(x,y)}"

# trays (verified zones; see spec)
TRAY_PSU = (1.0, 415.0, 98.0, 544.0)
TRAY_CTL = (342.0, 405.0, 392.0, 534.0)
rect_px_clear(TRAY_PSU, 11.0, "PSU tray")
rect_px_clear(TRAY_CTL, 10.5, "controller tray")
S3L = 126 - 24          # S3 raised-rail outer edge
assert TRAY_PSU[2] <= S3L - 3.5, "PSU tray must clear S3's raised rail"
assert 4 + 30 + 2 <= CAV, "PSU (30) + floor (4) + 2 clear must fit cavity"

# PSU bottom-hole patterns (Mean Well datasheets; L=3.0 max depth).
# Portrait, terminal end DOWN, case corner at tray corner (x0, y0):
# (w_off across x, l_off along y) per model.
x0, y0 = TRAY_PSU[0], TRAY_PSU[1]
psu = {"LRS-50":  [(40.5, 20.5), (40.5, 75.5)],
       "LRS-75":  [(45.5, 20.5), (45.5, 75.5)],
       "LRS-100": [(34.0, 78.0), (67.0, 78.0)]}
psu_holes = [(round(x0+w, 2), round(y0+l, 2)) for m in psu.values() for w, l in m]
for i in range(len(psu_holes)):     # union pattern must not merge bores
    for j in range(i+1, len(psu_holes)):
        assert math.dist(psu_holes[i], psu_holes[j]) >= 5.5, "PSU holes collide"

# Elite shell screws: ±61 along length, ±13 across width (probed from
# docs/elite2d_mount.stl). ctl_diag flips the diagonal after coupon check.
ctl_diag = 1
cx, cy = (TRAY_CTL[0]+TRAY_CTL[2])/2, (TRAY_CTL[1]+TRAY_CTL[3])/2
ctl_holes = [(round(cx - 13*ctl_diag, 2), round(cy - 61, 2)),
             (round(cx + 13*ctl_diag, 2), round(cy + 61, 2))]

# panel quadrants + fixing points
panels = [(0, 0, JX, JY), (JX, 0, FW, JY), (0, JY, JX, FH), (JX, JY, FW, FH)]
ledge_c = 3.5           # ledge boss centerline, inboard of plate edge
ledge_boss = ([(x, ledge_c) for x in (60, 150, 260, 350)]          # bottom
            + [(x, FH - ledge_c) for x in (60, 150, 260, 350)]     # top
            + [(ledge_c, y) for y in (120, 210, 340, 395)]         # left
            + [(FW - ledge_c, y) for y in (120, 210, 340, 470)])   # right
for p in ledge_boss:    # bosses must not sit inside a tray footprint
    for r, nm in ((TRAY_PSU, "PSU"), (TRAY_CTL, "ctl")):
        assert not (r[0]-4 < p[0] < r[2]+4 and r[1]-4 < p[1] < r[3]+4), \
            f"ledge boss {p} inside {nm} tray"
rail_boss = ([(126 - 21.5, y) for y in (330, 470)]     # S3 raised rails
           + [(126 + 21.5, y) for y in (330, 470)]
           + [(153 - 21.5, y) for y in (60, 190)]      # S4
           + [(153 + 21.5, y) for y in (60, 190)])
legs = [(q[0], 255.0) for s in SOCK for q in s]
assert len(legs) == 3, "expected 3 S1/S2 leg sockets"
supports = ledge_boss + rail_boss + legs
pscr = [[p for p in supports
         if r[0] - 1 <= p[0] <= r[2] + 1 and r[1] - 1 <= p[1] <= r[3] + 1]
        for r in panels]
for i, ps in enumerate(pscr):
    assert len(ps) >= 6, f"panel {i+1} has only {len(ps)} fixings"

# gland (left wall, low), handles (top rail), feet (bottom rail)
GLAND = (70.0, 19.0)            # (y along wall, z up the wall) hole center
assert not (TRAY_PSU[1] - 30 < GLAND[0] < TRAY_PSU[3]), "gland under PSU tray"
HANDLE = [(60, 150, 65, 145), (260, 350, 265, 345)]   # span x0,x1, bolt xs
for h in HANDLE:
    assert not h[0] < JX < h[1], "handle crosses the top joint"
FEET = [105.0, 305.0]
vent_rows = {"intake": [14, 23, 32, 41, 50], "exhaust": [500, 509, 518, 527, 536]}
MIC = (367.0, 470.0)

def fmt(pts):
    return "[%s]" % ",".join("[%.2f,%.2f]" % (p[0], p[1]) for p in pts)

with open("src/parts/frame_layout.scad", "w") as f:
    f.write("// AUTO-GENERATED by tools/boltframe.py — backer frame layout\n")
    f.write("// Board coords, z=0 at plate BACK, +z into the cavity.\n")
    f.write("fr_face=[%.1f,%.1f]; fr_clr=%.1f; fr_wall=%.1f; fr_cavity=%.1f;\n"
            % (FW, FH, CLR, WALL, CAV))
    f.write("fr_panel_t=%.1f; fr_flange_w=%.1f; fr_flange_t=%.1f;\n"
            % (PT, FLW, FLT))
    f.write("fr_ledge_w=%.1f; fr_ledge_t=%.1f; fr_reveal=%.1f;\n"
            % (LGW, LGT, REV))
    f.write("fr_joint=[%.1f,%.1f];\n" % (JX, JY))
    f.write("fr_boss=%s;\n" % fmt(boss))
    f.write("fr_panels=[%s];\n" % ",".join(
        "[%.1f,%.1f,%.1f,%.1f]" % p for p in panels))
    f.write("fr_panel_scr=[%s];\n" % ",".join(fmt(ps) for ps in pscr))
    f.write("fr_ledge_boss=%s;\n" % fmt(ledge_boss))
    f.write("fr_rail_boss=%s;\n" % fmt(rail_boss))
    f.write("fr_leg=%s;\n" % fmt(legs))
    f.write("fr_tray_psu=[%.1f,%.1f,%.1f,%.1f];\n" % TRAY_PSU)
    f.write("fr_psu_holes=%s;\n" % fmt(psu_holes))
    f.write("fr_tray_ctl=[%.1f,%.1f,%.1f,%.1f];\n" % TRAY_CTL)
    f.write("fr_ctl_holes=%s;\n" % fmt(ctl_holes))
    f.write("fr_gland=[%.1f,%.1f];\n" % GLAND)
    f.write("fr_handle=[%s];\n" % ",".join(
        "[%.1f,%.1f,%.1f,%.1f]" % h for h in HANDLE))
    f.write("fr_feet=[%.1f,%.1f];\n" % tuple(FEET))
    f.write("fr_vent_intake=%s;\n" % vent_rows["intake"])
    f.write("fr_vent_exhaust=%s;\n" % vent_rows["exhaust"])
    f.write("fr_mic=[%.1f,%.1f];\n" % MIC)
print("frame_layout: 14 bosses, %d PSU holes, %d panel fixing sets — asserts OK"
      % (len(psu_holes), len(pscr)))
```

- [ ] **Step 2: Run it** — `python3 tools/boltframe.py`
Expected: `frame_layout: 14 bosses, 6 PSU holes, 4 panel fixing sets — asserts OK`
- [ ] **Step 3: Negative test** — temporarily set `TRAY_PSU = (22,55,121,137)`
  (the failed lower-left zone), rerun, expect `AssertionError: PSU tray: 0.0 <
  11` — then restore. This proves the sweep guards.
- [ ] **Step 4: Commit** — `git add tools/boltframe.py src/parts/frame_layout.scad
  && git commit -m "feat: backer-frame layout generator with pixel-sweep asserts"`

### Task 2: tall flat-seat S3/S4 straps

**Files:**
- Modify: `src/parts/bracket.scad` (params + conditional nut pocket)
- Rebuild: `stl/strap_s3.stl`, `stl/strap_s4.stl`
- Modify: `tools/qa_board.py` (strap C-section knows tall/flat variants)

**Interfaces:**
- Produces: `bk_rail_h` / `bk_nut_pocket` as `-D`-able params; S3/S4 STLs
  become web 4 + rail 32 with plain Ø4.5 bores (flat z=4 seat, no hex).

- [ ] **Step 1: Parameterize bracket.scad** — change the two constants:

```scad
bk_rail_h    = 8.0;   // stiffening rails above the web (-D 32 for frame)
bk_nut_pocket = 1;    // 1 = captive hex (as-built S1/S2); 0 = flat seat
```

and make the nut cut conditional:

```scad
        for (q = bk_nut[i]) translate([q[0], q[1], 0]) {
            translate([0, 0, -0.1])
                cylinder(h = bk_web_t + bk_rail_h + 0.2, d = bk_scr_d);
            if (bk_nut_pocket)
                translate([0, 0, bk_web_t - bk_nut_t])
                    cylinder(h = bk_nut_t + 0.1, d = bk_nut_af / cos(30), $fn = 6);
        }
```

(bore extended through any rail the screw line crosses — harmless when clear.)
- [ ] **Step 2: Rebuild tall straps**
`for S in 3 4; do openscad -D STRAP=$S -D bk_rail_h=32 -D bk_nut_pocket=0 -o stl/strap_s${S}.stl src/parts/bracket.scad 2>stl/strap${S}.log; done`
- [ ] **Step 3: Probe** — max z == 36.0; screw bores present as Ø4.5 rings at
  z=0; NO hex ring at z 0.7–0.9 (reuse qa ring_r via a one-liner or the
  scratch probe script).
- [ ] **Step 4: Teach QA the variants** — in qa_board.py section C, replace the
  unconditional hex probe with:

```python
TALL = {"S3", "S4"}          # tall flat-seat frame variants
rail_h = 32.0 if name in TALL else 8.0
...
        rh = ring_r(verts, q[0], q[1], 0.7, 0.9, 6, rmin=3.0)
        if name in TALL:
            if rh is not None:          # flat seat: hex must be ABSENT
                bad.append(("hex-should-be-flat", q, rh))
        elif rh is None or not 3.4 <= rh <= 4.3:
            bad.append(("hex", q, rh))
```

and assert strap height: `zmax = max(v[2] for v in verts)` == `bk_web_t + rail_h`
(±0.1) as a new per-strap check.
- [ ] **Step 5: Run** `python3 tools/qa_board.py` — expect all PASS (45 checks:
  43 + 2 height checks fold into existing strap lines is fine either way).
- [ ] **Step 6: Commit.**

### Task 3: `src/parts/frame.scad` — 4 corner-L rail segments

**Files:**
- Create: `src/parts/frame.scad` (`-D SEG=1..4`; 1=BL, 2=BR, 3=TR, 4=TL)

**Interfaces:**
- Consumes: every `fr_*` from frame_layout.scad.
- Produces: `stl/frame_seg1..4.stl`, printable flange-down, bbox ≤ 316×295.

- [ ] **Step 1: Write frame.scad** — model the FULL frame in board coords
(z per Global Constraints), then clip per segment and lay flat. Core:

```scad
include <frame_layout.scad>
SEG = 1;
ox0=-fr_clr-fr_wall; ox1=fr_face[0]+fr_clr+fr_wall;
oy0=-fr_clr-fr_wall;  oy1=fr_face[1]+fr_clr+fr_wall;
wz1 = fr_cavity + fr_panel_t;          // wall top 38.4
in0x=-fr_clr; in1x=fr_face[0]+fr_clr;  // wall inner faces
in0y=-fr_clr; in1y=fr_face[1]+fr_clr;

module ring(w) difference() {          // outer perimeter band, width w inboard
    translate([ox0,oy0]) square([ox1-ox0, oy1-oy0]);
    translate([ox0+w,oy0+w]) square([ox1-ox0-2*w, oy1-oy0-2*w]);
}
module frame_body() {
    linear_extrude(wz1) ring(fr_wall + fr_clr);                  // walls
    linear_extrude(fr_flange_t) ring(fr_wall + fr_clr + fr_flange_w); // flange
    translate([0,0,fr_cavity-fr_ledge_t]) linear_extrude(fr_ledge_t)
        ring(fr_wall + fr_clr + fr_ledge_w);                     // ledge
    hull_ledge_chamfer();
    tray_floors(); boss_pads();
}
```

with these features (each a module, subtracted or unioned as appropriate):
- `hull_ledge_chamfer()` — 45° wedge under the ledge ring (printable shelf).
- `tray_floors()` — PSU rect + controller rect, z 0..4, merged to the walls.
- 14 flange bosses: cylinder Ø7 z 0..4 at `fr_boss` + Ø2.8 pilot z −0.1..4.1
  (bosses live INSIDE the flange band — union then drill).
- ledge bosses at `fr_ledge_boss`: Ø7 columns z 4..fr_cavity, Ø2.8 pilot from
  the top, 8 deep.
- tray drills: `fr_psu_holes` Ø2.8 through floor; `fr_ctl_holes` Ø3.2.
- gland: on the LEFT wall at y `fr_gland[0]`, z `fr_gland[1]`: outer-face
  recess 45×30×1.5, through-opening 36×22, two Ø2.8 pilots at y ±20.
- handle pads: top wall inner face, 20×12 pads z wz1−12..wz1 at `fr_handle`
  bolt xs, Ø3.4 pilot bored 10 down from the top face.
- feet pads: bottom wall inner, 36×12 pads z 0..14 at `fr_feet`, T-slot cut
  from below: stem 10.4×3.2 + cross 16.4×3.2, 9 deep.
- dovetail joints at x=fr_joint[0] (top+bottom) and y=fr_joint[1] (sides):
  bowtie pocket 24×14×5 recessed into the wall inner face spanning the cut,
  Ø2.8 pilot each side for the key screws.
- trim groove: 1.6×2 groove in the wall front edge (z −? n/a — wall starts
  z 0; groove in the wall OUTER face at z 0..3, 1.2 deep) for the snap trim.
- segment clip: `intersection()` with the quadrant box for SEG (split at
  fr_joint), then `translate` so bbox min = origin (print plate placement).
- [ ] **Step 2: Render all 4** — `for G in 1 2 3 4; do openscad -D SEG=$G -o
  stl/frame_seg$G.stl src/parts/frame.scad 2>stl/frameseg$G.log; done`
- [ ] **Step 3: Probe** — per segment: manifold (log "Simple: yes"), bbox ≤
  316×295×38.5, flange-boss rings found at the expected subset of `fr_boss`
  (transformed by the same clip translate — emit the offset in a comment line
  of frame_layout or derive: segment 1 offset = (−ox0, −oy0)).
- [ ] **Step 4: Commit.**

### Task 4: `src/parts/frame_panel.scad` — 4 vented quadrant panels

**Files:**
- Create: `src/parts/frame_panel.scad` (`-D PANEL=1..4`)

**Interfaces:**
- Consumes: `fr_panels`, `fr_panel_scr`, `fr_vent_*`, `fr_mic`, `fr_joint`.
- Produces: `stl/frame_panel1..4.stl`, flat prints, outside face down.

- [ ] **Step 1: Write it** — per panel: 2.4 skin sized to its quadrant minus
  0.3 edge clearance, +half-lap rebates (6 wide, 1.2 deep — panels 1,3 carry
  the lap on top of the x=205 edge, panels 2,4 the underside; same for
  y=275 between 1↔3, 2↔4), rib grid 4×8 on 60 pitch on the inside face,
  Ø3.4 screw holes countersunk at its `fr_panel_scr` points, louver rows
  (`louver()` = 22×2.6 slit + 45° interior hood, open DOWNWARD in sign
  orientation): intake rows on panels 1–2 at `fr_vent_intake` y's, exhaust
  on 3–4 at `fr_vent_exhaust`; mic cluster on panel 4 (contains `fr_mic`):
  5×5 grid of Ø2.5 at 6 mm pitch centered on `fr_mic`... panel 4 is
  x>205 — `fr_mic=(367,470)` lives in panel 4 ✓.
- [ ] **Step 2: Render 4 panels; probe** bbox ≤316×295, screw holes present at
  transformed `fr_panel_scr` points, manifold.
- [ ] **Step 3: Commit.**

### Task 5: `src/parts/frame_parts.scad` — small parts + chirality coupon

**Files:**
- Create: `src/parts/frame_parts.scad` (`-D PART=1..7 [-D GLAND=7|9|11]`)

**Interfaces:**
- Produces: `stl/frame_handle.stl` (×2 print), `frame_foot.stl` (×2),
  `frame_leg.stl` (×3), `frame_key.stl` (×4), `frame_gland_pg9.stl`
  (`GLAND` variants), `frame_trim.stl` (edge trim strips, ×4 corner-L),
  `frame_coupon.stl`.

- [ ] **Step 1: Write the parts:**
  1 handle: outer 120×44×15 rounded bar, 96×24 grip opening, 2 tabs with
    Ø4.5 counterbored bolt holes at 80 spacing; prints on its side.
  2 foot: T-tab (16.0×3.0 cross, 10.0×3.0 stem, 8.6 tall, split spring slot
    + 0.8 click ridge) on a 90×24×6 blade.
  3 leg: Ø10.0×13 pin + Ø14×2 shoulder + Ø10 column to z 36 from plate
    back = total 13+2+20... column such that top face lands at cavity 36
    over the S1/S2 strap boss (boss top at 14): 22 above shoulder; Ø2.8
    pilot 8 deep in top.
  4 gland plate: 45×30×2.5, PG bore per `GLAND` (7→12.5, 9→15.2, 11→18.6),
    2 Ø3.4 holes at ±20.
  5 key: bowtie 23.6×13.6×4.8 with 2 Ø3.4 holes.
  6 trim: corner-L strips matching each segment's outer profile: L-angle
    4.5 (covers plate edge + clr + wall front) × (fr_reveal+... ) — profile:
    leg A covers the wall front edge (3 wide), leg B the reveal face 2 over
    the plate front; snap tongue 1.4×1.8 engaging the wall groove. Rendered
    per SEG via `-D SEG=` like frame.scad, flat.
  7 coupon: 60×150×1.2 plate with BOTH candidate Elite diagonals (holes +
    embossed "A"/"B") and all 6 PSU holes + case-corner engraving — verify
    against the physical units, then set `ctl_diag`/`psu` and reprint straps
    of truth (rails) only after it passes.
- [ ] **Step 2: Render each; probe** hole positions on gland plate + coupon
  (ring probe), manifold all.
- [ ] **Step 3: Commit.**

### Task 6: QA — frame section in `tools/qa_board.py`

**Files:**
- Modify: `tools/qa_board.py` (new section F after plates)

**Interfaces:**
- Consumes: `frame_layout.scad` + the STLs from Tasks 2–5.

- [ ] **Step 1: Add checks** (house `check()` style):
  - frame bosses == bb_scr kind-0 point set (exact coordinate compare).
  - every tray rect ≥ its clearance to every pixel (recompute the sweep —
    independent reimplementation, not an import from boltframe).
  - PSU stack: floor 4 + 30 + 2 ≤ cavity.
  - lip/trim never covers a screw rim (edge distance ≥ reveal + 0.5 + 2.25).
  - gland seat 2.5 ≤ 3.5.
  - every panel fixing lands on a ledge boss / rail boss / leg (±0.5).
  - per-STL: frame_seg1..4 + panels bbox ≤ 316×295; all new STLs manifold
    (reuse the existing manifold check list — extend `MANIFEST`).
  - strap tall-variant checks from Task 2 (if not already merged there).
- [ ] **Step 2: Run** `python3 tools/qa_board.py` — expect ~55+ checks, 0 FAIL.
- [ ] **Step 3: Commit.**

### Task 7: build_board.sh frame section + full rebuild

**Files:**
- Modify: `build_board.sh`

- [ ] **Step 1: Append:**

```bash
# backer frame (spec 2026-07-21): layout -> segments, panels, parts
python3 tools/boltframe.py
for G in 1 2 3 4; do
  "$OSCAD" -D SEG=$G -o "stl/frame_seg${G}.stl" src/parts/frame.scad \
    2>"stl/frameseg${G}.log" && echo "  ok frame_seg${G}"
  "$OSCAD" -D SEG=$G -D PART=6 -o "stl/frame_trim${G}.stl" src/parts/frame_parts.scad \
    2>"stl/frametrim${G}.log" && echo "  ok frame_trim${G}"
done
for P in 1 2 3 4; do
  "$OSCAD" -D PANEL=$P -o "stl/frame_panel${P}.stl" src/parts/frame_panel.scad \
    2>"stl/framepanel${P}.log" && echo "  ok frame_panel${P}"
done
for N in 1:handle 2:foot 3:leg 4:gland_pg9 5:key 7:coupon; do
  "$OSCAD" -D PART=${N%%:*} -o "stl/frame_${N##*:}.stl" src/parts/frame_parts.scad \
    2>/dev/null && echo "  ok frame_${N##*:}"
done
# tall flat-seat straps for the frame round (chirality-fixed source)
for S in 3 4; do
  "$OSCAD" -D STRAP=$S -D bk_rail_h=32 -D bk_nut_pocket=0 \
    -o "stl/strap_s${S}.stl" src/parts/bracket.scad 2>"stl/strap${S}.log" \
    && echo "  ok strap_s${S} (tall)"
done
```

- [ ] **Step 2: Run the frame portion end-to-end; QA again; commit.**

### Task 8: committed web preview + spec sync

**Files:**
- Create: `tools/gen_framepreview.py` (QA-grade, reads generated layouts —
  port of the session's spec-stage generator, now data-driven end to end:
  frame_layout for every overlay coordinate instead of hardcoded numbers)
- Output: `docs/sign-preview/frame-preview.html`
- Modify: spec (assembly paragraph → trim-strip amendment)

- [ ] **Step 1: Write the tool** — same card layout as the artifact version
  (front x-ray + rail cross-section + tray detail + foot/handle detail +
  params list), house dark style + light tokens, all geometry read from
  `frame_layout.scad`/`board_layout.scad`/`bracket_layout.scad`.
- [ ] **Step 2: Generate; visually sanity-probe the HTML (no leftover
  placeholders, counts match layout).**
- [ ] **Step 3: Amend the spec** — replace the "hook the lip, rotate onto the
  flange" sentence with the trim-strip design (rails flange-down printable,
  trim = PART=6 snap strips, `reveal=0` = skip trim); note coupon gate.
- [ ] **Step 4: Publish the artifact from the generated file (same URL) and
  commit everything.**

## Self-Review

- Spec coverage: rails/flange/lip(→trim)/ledge ✓ T3+T5; joints+keys ✓ T3/T5;
  handles ✓ T3 pads + T5 part; feet ✓; straps 8→32 + flat seats ✓ T2; legs ✓
  T5; panels+louvers+mic+rebates ✓ T4; trays+hole patterns+asserts ✓ T1/T3;
  gland plate PG7/9/11 + thin seat ✓ T1/T3/T5; QA list ✓ T6; build ✓ T7;
  preview ✓ T8; print order = task order ✓. Voltage note is a buy-time item,
  no task.
- Placeholders: none — geometry values all concrete; Task 3–5 module bullets
  each carry exact dimensions.
- Type consistency: `fr_*` names match between T1 emitter and T3–T6/T8
  consumers; `bk_rail_h`/`bk_nut_pocket` names match T2/T7.
- Deviation from spec recorded: reveal lip → snap trim (Global Constraints +
  T8 spec sync). Coupon gate added (chirality history).
