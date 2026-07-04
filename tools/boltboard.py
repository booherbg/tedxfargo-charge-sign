#!/usr/bin/env python3
"""Production data for the element-6 bolt board (410x550, 4 plates).
Reads src/parts/bolt_el6.json (yellow fused bolt+X outline + red inner zigzag,
pre-split at the seams by tools/bolt_compose6.py). Seams: y=255 full width,
plus per-row vertical seams (piecewise: top row splits at seam_x_top, bottom
row at seam_x_bot). Plates:
  B1 = bottom-left   [0..seam_x_bot] x [0..seam_y]
  B2 = bottom-right  [seam_x_bot..FW] x [0..seam_y]
  B3 = top-left      [0..seam_x_top] x [seam_y..FH]
  B4 = top-right     [seam_x_top..FW] x [seam_y..FH]
Places pixels at --pitch (relaxation de-conflict, same rules as the letters),
lays out per-plate screws + zip-tie holes, and emits:
  src/parts/board_layout.scad   (for src/parts/bolt_piece.scad)
  src/parts/bolt_pixmap.json    (pixel -> color zone map for the controller)
  src/parts/fuzz_board_{1..4}.dat
Usage: boltboard.py [--pitch 20]
"""
import json, math, subprocess, sys

def arg(f, d):
    return sys.argv[sys.argv.index(f)+1] if f in sys.argv else d

PITCH  = float(arg("--pitch", "20"))
PX_MIN = 14.5

D = json.load(open("src/parts/bolt_el6.json"))
FW, FH = D["face"]
SY, SXT, SXB = D["seam_y"], D["seam_x_top"], D["seam_x_bot"]
C = D["c1"]
paths = [[tuple(q) for q in p] for p in C["yellow"]] + \
        [[tuple(q) for q in p] for p in C["red"]]
n_yellow = len(C["yellow"])
PLATES = [(0.0, SXB, 0.0, SY), (SXB, FW, 0.0, SY),
          (0.0, SXT, SY, FH), (SXT, FW, SY, FH)]
for i, (x0, x1, y0, y1) in enumerate(PLATES):
    w, h = x1 - x0, y1 - y0
    ok = (w <= 316 and h <= 295)
    print("plate B%d: %.0fx%.0f %s" % (i+1, w, h, "ok" if ok else "TOO BIG"))
    if not ok:
        sys.exit(1)

# content must already sit inside the face with band margin
lo_x = min(q[0] for p in paths for q in p) - 11
hi_x = max(q[0] for p in paths for q in p) + 11
lo_y = min(q[1] for p in paths for q in p) - 11
hi_y = max(q[1] for p in paths for q in p) + 11
assert lo_x > 14 and lo_y > 14 and hi_x < FW - 14 and hi_y < FH - 14, \
    "content too close to face edge"

def _plen(p): return sum(math.dist(p[i], p[i+1]) for i in range(len(p)-1))
def point_at(p, t):
    acc = 0.0
    for i in range(len(p)-1):
        d = math.dist(p[i], p[i+1])
        if acc + d >= t:
            f = (t-acc)/d if d else 0
            return (p[i][0]+(p[i+1][0]-p[i][0])*f, p[i][1]+(p[i+1][1]-p[i][1])*f)
        acc += d
    return p[-1]

# pixel placement: even + chord floor, then relaxation (same physics as letters)
seg_len = [_plen(p) for p in paths]
pmeta = []
for si, p in enumerate(paths):
    L = seg_len[si]
    pts, t = [(point_at(p, 0), 0.0)], 0.0
    while True:
        t2 = t + PITCH
        while t2 < L and math.dist(point_at(p, t2), pts[-1][0]) < PX_MIN + 0.3:
            t2 += 1.0
        if t2 >= L - PITCH*0.45:
            R = L - t
            k = max(1, round(R/PITCH))
            while k > 1 and R/k < PX_MIN + 0.3:
                k -= 1
            for j in range(1, k):
                pts.append((point_at(p, t + j*R/k), t + j*R/k))
            pts.append((point_at(p, L), L))
            break
        pts.append((point_at(p, t2), t2))
        t = t2
    for i, (xy, tt) in enumerate(pts):
        pmeta.append([xy[0], xy[1], si, tt, 0.0])

def live_pairs():
    live = [k for k in range(len(pmeta)) if pmeta[k] is not None]
    return [(a, b) for i, a in enumerate(live) for b in live[i+1:]
            if math.dist(pmeta[a][:2], pmeta[b][:2]) < PX_MIN]
for _ in range(60):
    prs = live_pairs()
    if not prs:
        break
    for a, b in prs:
        for idx, oth in ((a, b), (b, a)):
            x, y, si, t, mv = pmeta[idx]
            if abs(mv) >= 9.0:
                continue
            L = seg_len[si]
            bt, bd = t, math.dist(pmeta[idx][:2], pmeta[oth][:2])
            for dt in (-0.8, 0.8):
                t2 = min(max(t+dt, 0.0), L)
                d2 = math.dist(point_at(paths[si], t2), pmeta[oth][:2])
                if d2 > bd:
                    bt, bd = t2, d2
            if bt != t:
                nx, ny = point_at(paths[si], bt)
                pmeta[idx] = [nx, ny, si, bt, mv + (bt-t)]
dropped = 0
while True:
    prs = live_pairs()
    if not prs:
        break
    a, b = min(prs, key=lambda pr: math.dist(pmeta[pr[0]][:2], pmeta[pr[1]][:2]))
    d = math.dist(pmeta[a][:2], pmeta[b][:2])
    if d >= 13.0:
        break                                   # snug pairs: seat firmly, keep the light
    end_a = pmeta[a][3] < 1 or pmeta[a][3] > seg_len[pmeta[a][2]] - 1
    pmeta[a if not end_a else b] = None
    dropped += 1
pixels = [[round(m[0], 2), round(m[1], 2), m[2]] for m in pmeta if m is not None]
snug = len(live_pairs())
ny_px = sum(1 for p in pixels if p[2] < n_yellow)
print("pixels: %d (%d yellow, %d red), %d dropped at crossings, %d snug pairs"
      % (len(pixels), ny_px, len(pixels)-ny_px, dropped, snug))

# screws: per plate, corners + long-edge midpoints (inset 12 in x, 6 in y from
# plate edges -- interior edges get the inset on each side of the seam)
scr = []
for (x0, x1, y0, y1) in PLATES:
    xs = [x0 + 12, (x0 + x1) / 2, x1 - 12]
    for sy in (y0 + 6, y1 - 6):
        for f in xs:
            scr.append([round(f, 1), round(sy, 1)])
scr = [list(s) for s in dict(((round(s[0]), round(s[1])), s) for s in scr).values()]

def plate_of(x, y):
    for i, (x0, x1, y0, y1) in enumerate(PLATES):
        if x0 <= x < x1 and y0 <= y < y1:
            return i + 1
    return 0

# zip ties along paths, clear of tubes/screws/edges/all seams
SEAMS = [(1, SY, 0, FW), (0, SXT, SY, FH), (0, SXB, 0, SY)]
def near_seam(x, y, d=12.0):
    for axis, coord, b0, b1 in SEAMS:
        v = (x, y)
        if b0 - 2 <= v[1-axis] <= b1 + 2 and abs(v[axis] - coord) < d:
            return True
    return False
ties = []
for si, p in enumerate(paths):
    t = 30.0
    while t < seg_len[si] - 20:
        (x, y) = point_at(p, t)
        (x2, y2) = point_at(p, min(t+2, seg_len[si]))
        tx, ty = x2-x, y2-y
        L = math.hypot(tx, ty) or 1
        for sgn in (1, -1):
            hx, hy = x - ty/L*15.5*sgn, y + tx/L*15.5*sgn
            if not (8 < hx < FW-8 and 8 < hy < FH-8) or near_seam(hx, hy):
                continue
            if min(math.dist((hx, hy), q) for pp in paths for q in pp[::2]) < 14:
                continue
            if any(math.dist((hx, hy), sxy) < 10 for sxy in scr):
                continue
            ties.append([round(hx, 1), round(hy, 1)])
        t += 60.0

fmt = lambda pts: "[" + ",".join("[%.2f,%.2f]" % (q[0], q[1]) for q in pts) + "]"
with open("src/parts/board_layout.scad", "w") as f:
    f.write("// AUTO-GENERATED by tools/boltboard.py — element-6 bolt board\n")
    f.write("bb_face = [%.1f, %.1f];\n" % (FW, FH))
    f.write("bb_plates = [%s];\n" % ",".join(
        "[%.1f,%.1f,%.1f,%.1f]" % r for r in PLATES))
    f.write("bb_paths = [\n  %s\n];\n" % ",\n  ".join(fmt(p) for p in paths))
    f.write("bb_px = %s;\n" % fmt(pixels))
    f.write("bb_scr = %s;\n" % fmt(scr))
    f.write("bb_tie = %s;\n" % fmt(ties))
json.dump({"pitch": PITCH, "pixels": [{"x": p[0], "y": p[1],
           "color": "yellow" if p[2] < n_yellow else "red",
           "plate": plate_of(p[0], p[1])} for p in pixels]},
          open("src/parts/bolt_pixmap.json", "w"), indent=1)
for pl, (x0, x1, y0, y1) in enumerate(PLATES, 1):
    ax, ay = (x1 - x0) + 4, (y1 - y0) + 4
    dat = "src/parts/fuzz_board_%d.dat" % pl
    # plate 4's grid at seed 7 rolls a non-manifold fuzz sliver (grid-luck class
    # from the word postmortem); seed 8 audits clean
    seed = "8" if pl == 4 else "7"
    subprocess.run(["python3", "tools/make_fuzz.py", dat,
                    "1.5", "0.8", seed, "0", "0", "%.0f" % ax, "%.0f" % ay], check=True)
    rows = []                                   # same +-50um dead-band as the letters
    for line in open(dat):
        vals = []
        for v in line.split():
            fv = float(v)
            if 0.100 < fv < 0.201:
                fv = 0.100 if fv < 0.1504 else 0.201
            vals.append("%.3f" % fv)
        rows.append(" ".join(vals))
    open(dat, "w").write("\n".join(rows) + "\n")
counts = [sum(1 for p in pixels if plate_of(p[0], p[1]) == pl) for pl in (1,2,3,4)]
print("plate px: B1 %d / B2 %d / B3 %d / B4 %d; %d screws, %d ties"
      % (*counts, len(scr), len(ties)))
print("wrote board_layout.scad + bolt_pixmap.json + fuzz_board_{1..4}.dat")
