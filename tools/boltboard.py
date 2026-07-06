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

# channels now CROSS the plate joints (continuous mode) -> a pixel collar must
# never straddle a seam: keep pixel centers >= PX_SEAM from every seam segment
PX_SEAM = 12.5
SEAMS_PX = [(1, SY, 0.0, FW), (0, SXT, SY, FH), (0, SXB, 0.0, SY)]
def seam_ok(xy):
    for axis, coord, b0, b1 in SEAMS_PX:
        if b0 - 2 <= xy[1-axis] <= b1 + 2 and abs(xy[axis] - coord) < PX_SEAM:
            return False
    return True

# pixel placement: even + chord floor, then relaxation (same physics as letters)
seg_len = [_plen(p) for p in paths]
pmeta = []
for si, p in enumerate(paths):
    L = seg_len[si]
    is_closed = math.dist(p[0], p[-1]) < 0.05
    t0 = 0.0
    if not seam_ok(point_at(p, t0)):            # nudge the anchor off a seam
        while t0 < L and not seam_ok(point_at(p, t0)):
            t0 += 1.0
    pts, t = [(point_at(p, t0), t0)], t0
    while True:
        t2 = t + PITCH
        while t2 < L and (math.dist(point_at(p, t2), pts[-1][0]) < PX_MIN + 0.3
                          or not seam_ok(point_at(p, t2))):
            t2 += 1.0
        if t2 >= L - PITCH*0.45:
            R = L - t
            k = max(1, round(R/PITCH))
            while k > 1 and R/k < PX_MIN + 0.3:
                k -= 1
            for j in range(1, k):
                cand = (point_at(p, t + j*R/k), t + j*R/k)
                if seam_ok(cand[0]):
                    pts.append(cand)
            if not is_closed and seam_ok(point_at(p, L)):
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
                cand = point_at(paths[si], t2)
                d2 = math.dist(cand, pmeta[oth][:2])
                if d2 > bd and seam_ok(cand):
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
pix_t = [m[3] for m in pmeta if m is not None]
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
# zip-tie pairs REMOVED at user direction (2026-07-06): lit-plenum light leaks.
ties = []

# wiring chain: pixels are addressable (color zones are software), so one
# physical chain serves the whole board. Keep arc order within each path run,
# then greedily append the nearest path end (either direction). 4-inch strings
# cap a link at ~101.6mm; longer jumps are flagged (need an extension jumper).
runs = {}
for idx, p in enumerate(pixels):
    runs.setdefault(p[2], []).append(idx)
for si in runs:
    runs[si].sort(key=lambda i: pix_t[i])
order, used = [], set()
cur = min(runs, key=lambda si: min(pixels[i][1] for i in runs[si]))
forward = True
while True:
    seq = runs[cur] if forward else runs[cur][::-1]
    order.extend(seq)
    used.add(cur)
    if len(used) == len(runs):
        break
    tail = pixels[order[-1]]
    best = None
    for si in runs:
        if si in used:
            continue
        for fw in (True, False):
            head = pixels[runs[si][0 if fw else -1]]
            d = math.dist(tail[:2], head[:2])
            if best is None or d < best[0]:
                best = (d, si, fw)
    cur, forward = best[1], best[2]
chain_of = {pix_i: c for c, pix_i in enumerate(order)}
links = [math.dist(pixels[order[k]][:2], pixels[order[k+1]][:2])
         for k in range(len(order) - 1)]
long_links = [(k, round(links[k], 1)) for k in range(len(links)) if links[k] > 101.6]
print("chain: %d links, max %.0f mm, %d over the 101.6 mm string length%s"
      % (len(links), max(links), len(long_links),
         " -> extension jumpers at chain idx " + str([k for k, _ in long_links])
         if long_links else ""))

# ONE global fuzz field (texture continuous across the joints the channels now
# cross), CROPPED per plate: surface() otherwise loads the full field for every
# plate render (~1M tris). Crops carry their own center so each plate samples
# the identical global values -> joints stay seamless.
# V8 texture (PETG bake-off winner 2026-07-05): jittered pyramid facets,
# 2.0mm cells / 0.6mm peaks, sampled at cell/3 (bolt_piece.scad scale 0.6667).
dat = "src/parts/fuzz_board_global.dat"
SAMP = 2.0 / 3.0
subprocess.run(["python3", "tools/make_fuzz.py", dat, "2.0", "0.6", "8",
                "0", "0", "%.0f" % (FW + 4), "%.0f" % (FH + 4),
                "--mode=pyramid-jitter"], check=True)   # seed 8: seed-7 field drew
                                                        # a sliver on board4
grid = [[float(v) for v in ln.split()] for ln in open(dat) if ln.strip()]
NYg, NXg = len(grid), len(grid[0])
fuzz_ctr = []
for pl, (px0, px1, py0, py1) in enumerate(PLATES, 1):
    # field is board-centered: mm = (idx - (N-1)/2)*SAMP + face_center
    ix0 = max(0, int((px0 - 6 - FW/2) / SAMP + (NXg - 1) / 2))
    ix1 = min(NXg - 1, int((px1 + 6 - FW/2) / SAMP + (NXg - 1) / 2) + 1)
    iy0 = max(0, int((py0 - 6 - FH/2) / SAMP + (NYg - 1) / 2))
    iy1 = min(NYg - 1, int((py1 + 6 - FH/2) / SAMP + (NYg - 1) / 2) + 1)
    sub = [row[ix0:ix1 + 1] for row in grid[iy0:iy1 + 1]]
    cx = ((ix0 + ix1) / 2 - (NXg - 1) / 2) * SAMP + FW / 2
    cy = ((iy0 + iy1) / 2 - (NYg - 1) / 2) * SAMP + FH / 2
    fuzz_ctr.append((cx, cy))
    open("src/parts/fuzz_board_p%d.dat" % pl, "w").write(
        "\n".join(" ".join("%.3f" % v for v in row) for row in sub) + "\n")
    print("fuzz crop B%d: %dx%d samples, center (%.1f, %.1f)"
          % (pl, len(sub[0]), len(sub), cx, cy))

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
    f.write("bb_fuzz_ctr = [%s];\n" % ",".join(
        "[%.2f,%.2f]" % c for c in fuzz_ctr))
json.dump({"pitch": PITCH,
           "chain_note": "chain = physical data order (one chain, addressable "
                         "pixels); links over 101.6mm need an extension jumper",
           "pixels": [{"x": p[0], "y": p[1],
           "color": "yellow" if p[2] < n_yellow else "red",
           "plate": plate_of(p[0], p[1]),
           "chain": chain_of[i]} for i, p in enumerate(pixels)]},
          open("src/parts/bolt_pixmap.json", "w"), indent=1)
counts = [sum(1 for p in pixels if plate_of(p[0], p[1]) == pl) for pl in (1,2,3,4)]
min_seam = min((abs((p[0], p[1])[axis] - coord)
                for p in pixels for axis, coord, b0, b1 in SEAMS_PX
                if b0 - 2 <= (p[0], p[1])[1-axis] <= b1 + 2), default=99)
print("plate px: B1 %d / B2 %d / B3 %d / B4 %d; %d screws, %d ties; "
      "min pixel-to-seam %.1f mm" % (*counts, len(scr), len(ties), min_seam))
print("wrote board_layout.scad + bolt_pixmap.json + fuzz_board_global.dat")
