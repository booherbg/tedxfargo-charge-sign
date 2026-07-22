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
CLR, WALL, CAV, PT = 0.5, 3.0, 48.0, 2.4
FLW, FLT, LGW, LGT, REV = 16.0, 4.0, 8.0, 4.0, 2.0
JX, JY = 205.0, 300.0   # JY=300 keeps the side joints off the (6,275)/(404,275)
                        # screw bosses AND off the S1/S2 strap band (231..279)
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
for x, y in boss:   # trim reveal never covers a hole rim
    e = min(x, y, FW - x, FH - y)
    assert e - 2.25 >= REV + 0.5, f"trim lip too close to screw at {(x, y)}"
    # segment joints must never cut through a boss (the y=275 lesson)
    if y < 20 or y > FH - 20:
        assert abs(x - JX) >= 12, f"top/bottom joint through boss {(x, y)}"
    if x < 20 or x > FW - 20:
        assert abs(y - JY) >= 12, f"side joint through boss {(x, y)}"

# equipment trays (verified pixel-free zones; see spec)
TRAY_PSU = (1.0, 407.0, 98.0, 536.0)
TRAY_CTL = (342.0, 405.0, 392.0, 534.0)
rect_px_clear(TRAY_PSU, 11.0, "PSU tray")
rect_px_clear(TRAY_CTL, 10.5, "controller tray")
S3L = 126 - 24          # S3 raised-rail outer edge
assert TRAY_PSU[2] <= S3L - 3.5, "PSU tray must clear S3's raised rail"
assert 4 + 30 + 2 <= CAV, "PSU (30) + floor (4) + 2 clear must fit cavity"

# PSU bottom-hole patterns (Mean Well datasheets; screw depth MAX 3 mm).
# Portrait, terminal end DOWN, case corner at the tray corner (x0, y0);
# (w_off across x, l_off along y). LRS-50 and LRS-75 share the 20.5/75.5
# length positions and differ only across (40.5 vs 45.5), so each pair
# merges into one SLOT serving both; LRS-100 gets round holes.
x0, y0 = TRAY_PSU[0], TRAY_PSU[1]
psu_slots = [(round(x0+40.5, 2), round(y0+l, 2), round(x0+45.5, 2), round(y0+l, 2))
             for l in (20.5, 75.5)]
psu_holes = [(round(x0+w, 2), round(y0+78.0, 2)) for w in (34.0, 67.0)]
assert math.dist(psu_holes[0], psu_holes[1]) >= 5.5, "PSU holes collide"
for hx, hy in psu_holes:            # rounds must clear the slot envelopes
    for sx0, sy, sx1, _ in psu_slots:
        near = (min(max(hx, sx0), sx1), sy)
        assert math.dist((hx, hy), near) >= 5.5, "PSU hole hits a slot"

# Elite shell screws: ±61 along length, ±13 across width (probed from
# docs/elite2d_mount.stl). ctl_diag flips the diagonal after coupon check.
ctl_diag = 1
cx, cy = (TRAY_CTL[0]+TRAY_CTL[2])/2, (TRAY_CTL[1]+TRAY_CTL[3])/2
ctl_holes = [(round(cx - 13*ctl_diag, 2), round(cy - 61, 2)),
             (round(cx + 13*ctl_diag, 2), round(cy + 61, 2))]

# v1 wiring config (2026-07-22, user): controller OUTSIDE on the left-wall
# pads (same 122 x 26 diagonal), plug-in PSU, and a single PG7 gland passing
# the 3x18AWG V+/V-/D line into the cavity 2 in above the controller's top
# (output) end. PG7 threads the 3.0 wall directly (clamp limit 3.5) — no
# plate. The internal-PSU gland-plate config is kept behind GLAND_PLATE.
GLAND_PLATE = 0
TRIM = 0        # v1.1: trim dropped (user) — no groove, clean outer face
# flush exterior mount: wall = CAV + 2.4 = 50.4 >= the Elite's 50 width;
# body spans z 0.4..50.4 (back face coplanar with the panel plane)
ctl_ext = [(99.0, 12.4), (221.0, 38.4)]
GLAND = (275.0, 19.0)           # (y along wall, z) hole center, left wall
ext_top = (ctl_ext[0][0] + ctl_ext[1][0]) / 2 + 64.5   # controller top end
assert GLAND[0] - ext_top >= 45, "gland must sit ~2 in above the controller"
assert GLAND[0] + (6.25 if not GLAND_PLATE else 22.5) + 2 <= JY - 15, \
    "gland must clear the side joint pad"
assert not (TRAY_PSU[1] - 30 < GLAND[0] < TRAY_PSU[3]), "gland under PSU tray"

# panel quadrants + fixing points
panels = [(0, 0, JX, JY), (JX, 0, FW, JY), (0, JY, JX, FH), (JX, JY, FW, FH)]
ledge_c = 3.5           # ledge boss centerline, inboard of plate edge
ledge_boss = ([(x, ledge_c) for x in (60, 150, 260, 350)]          # bottom
            + [(x, FH - ledge_c) for x in (60, 150, 220, 260, 350)]  # top
            + [(ledge_c, y) for y in (120, 210, 340, 395)]         # left
            + [(FW - ledge_c, y) for y in (120, 210, 340, 470, 530)])  # right
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

# handles (top rail, back-flush), feet T-slots (bottom rail)
HANDLE = [(60, 150, 65, 145), (260, 350, 265, 345)]   # span x0,x1, bolt xs
for h in HANDLE:
    assert not h[0] < JX < h[1], "handle crosses the top joint"
FEET = [105.0, 305.0]
vent_int = [14, 23, 32, 41, 50]
vent_exh = [500, 509, 518, 527, 536]
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
    f.write("fr_psu_slots=[%s];\n" % ",".join(
        "[%.2f,%.2f,%.2f,%.2f]" % s for s in psu_slots))
    f.write("fr_tray_ctl=[%.1f,%.1f,%.1f,%.1f];\n" % TRAY_CTL)
    f.write("fr_ctl_holes=%s;\n" % fmt(ctl_holes))
    f.write("fr_ctl_ext=%s;\n" % fmt(ctl_ext))
    f.write("fr_gland=[%.1f,%.1f];\n" % GLAND)
    f.write("fr_gland_plate=%d;\n" % GLAND_PLATE)
    f.write("fr_trim=%d;\n" % TRIM)
    f.write("fr_handle=[%s];\n" % ",".join(
        "[%.1f,%.1f,%.1f,%.1f]" % h for h in HANDLE))
    f.write("fr_feet=[%.1f,%.1f];\n" % tuple(FEET))
    f.write("fr_vent_intake=%s;\n" % vent_int)
    f.write("fr_vent_exhaust=%s;\n" % vent_exh)
    f.write("fr_mic=[%.1f,%.1f];\n" % MIC)
print("frame_layout: %d bosses, %d PSU holes, %d panel fixing sets — asserts OK"
      % (len(boss), len(psu_holes), len(pscr)))
