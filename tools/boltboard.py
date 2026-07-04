#!/usr/bin/env python3
"""Production data for the C1 bolt board (300x590, 2 plates, straight seam).
Reads src/parts/bolt_final2.json (c1 = yellow outline + double-run red, pre-split
at the seam), places pixels at --pitch (relaxation de-conflict, same rules as the
letters), lays out screws for the 3-rail mount and zip-tie holes, and emits:
  src/parts/board_layout.scad   (for src/parts/bolt_piece.scad)
  src/parts/bolt_pixmap.json    (pixel -> color zone map for the controller)
Usage: boltboard.py [--pitch 20]
"""
import json, math, subprocess, sys

def arg(f, d):
    return sys.argv[sys.argv.index(f)+1] if f in sys.argv else d

PITCH  = float(arg("--pitch", "20"))
PX_MIN = 14.5
FW, FH, SEAM = 300.0, 590.0, 295.0
SHRINK_MARGIN = 16.0          # min distance: band edge -> face edge

D = json.load(open("src/parts/bolt_final2.json"))["c1"]
paths = [[tuple(q) for q in p] for p in D["yellow"]] + [[tuple(q) for q in p] for p in D["red"]]
n_yellow = len(D["yellow"])

# recenter + shrink so channels keep SHRINK_MARGIN off the face edges
ys = [q[1] for p in paths for q in p]; xs = [q[0] for p in paths for q in p]
span_y = max(ys) - min(ys) + 22
s = min(1.0, (FH - 2*SHRINK_MARGIN) / span_y)
cx0, cy0 = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
paths = [[((q[0]-cx0)*s + FW/2, (q[1]-cy0)*s + FH/2) for q in p] for p in paths]
print("content scaled x%.3f; channel y-extent %.0f..%.0f" %
      (s, min(q[1] for p in paths for q in p)-11, max(q[1] for p in paths for q in p)+11))

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
    n = max(2, round(L/PITCH) + 1)
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
snug = sum(1 for a, b in live_pairs() if True)
ny_px = sum(1 for p in pixels if p[2] < n_yellow)
print("pixels: %d (%d yellow, %d red), %d dropped at crossings, %d snug pairs"
      % (len(pixels), ny_px, len(pixels)-ny_px, dropped, snug))

# screws: 3 rails (bottom, seam, top); each plate gets corners+mid on its two rails
scr = []
for sy in (6.0, SEAM-6.0, SEAM+6.0, FH-6.0):
    for f in (12.0, FW/2, FW-12.0):
        scr.append([round(f, 1), round(sy, 1)])
# zip ties along paths, clear of tubes/screws/edges/seam
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
            if not (8 < hx < FW-8 and 8 < hy < FH-8) or abs(hy-SEAM) < 12:
                continue
            if min(math.dist((hx, hy), q) for pp in paths for q in pp[::2]) < 14:
                continue
            if any(math.dist((hx, hy), sxy) < 10 for sxy in scr):
                continue
            ties.append([round(hx, 1), round(hy, 1)])
        t += 60.0

fmt = lambda pts: "[" + ",".join("[%.2f,%.2f]" % (q[0], q[1]) for q in pts) + "]"
with open("src/parts/board_layout.scad", "w") as f:
    f.write("// AUTO-GENERATED by tools/boltboard.py — C1 bolt board\n")
    f.write("bb_face = [%.1f, %.1f];\nbb_seam = %.1f;\n" % (FW, FH, SEAM))
    f.write("bb_paths = [\n  %s\n];\n" % ",\n  ".join(fmt(p) for p in paths))
    f.write("bb_px = %s;\n" % fmt(pixels))
    f.write("bb_scr = %s;\n" % fmt(scr))
    f.write("bb_tie = %s;\n" % fmt(ties))
json.dump({"pitch": PITCH, "pixels": [{"x": p[0], "y": p[1],
           "color": "yellow" if p[2] < n_yellow else "red",
           "plate": 1 if p[1] < SEAM else 2} for p in pixels]},
          open("src/parts/bolt_pixmap.json", "w"), indent=1)
for pl in (1, 2):
    ax, ay = FW + 4, SEAM + 4
    dat = "src/parts/fuzz_board_%d.dat" % pl
    subprocess.run(["python3", "tools/make_fuzz.py", dat,
                    "1.5", "0.8", "7", "0", "0", "%.0f" % ax, "%.0f" % ay], check=True)
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
p1 = sum(1 for p in pixels if p[1] < SEAM)
print("plates: B1 %d px / B2 %d px; %d screws, %d ties" % (p1, len(pixels)-p1, len(scr), len(ties)))
print("wrote board_layout.scad + bolt_pixmap.json + fuzz_board_{1,2}.dat")
