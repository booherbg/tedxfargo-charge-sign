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

SEAM BRACKETS (2026-07-10, spec docs/superpowers/specs/2026-07-10-seam-bracket-design.md):
printed white splice straps behind each seam replace the y-seam wood rail.
Pixels are ANCHORED at seam crossings (straddle at +-KEEPOUT/sin(theta); the
two shallow crossings get a pixel ON the seam whose collar lives in the strap)
so LED spacing stays uniform across the joints. Plates fasten to the straps
with M4 machine screws into captive hex nuts.

Emits:
  src/parts/board_layout.scad    (plates: pixels, screws, bites -> bolt_piece.scad)
  src/parts/bracket_layout.scad  (straps, local printed coords -> bracket.scad)
  src/parts/bolt_pixmap.json     (pixel -> color zone / plate / chain / mount)
  src/parts/fuzz_board_p{1..4}.dat
Usage: boltboard.py [--pitch-max 23]
"""
import json, math, subprocess, sys

def arg(f, d):
    return sys.argv[sys.argv.index(f)+1] if f in sys.argv else d

PX_BUDGET = 137          # board share of the 600-pixel inventory (user-locked)
PX_MIN    = 14.5
KEEPOUT   = 9.5          # perpendicular collar-center -> seam floor (1.5mm web)
GAP_MAX   = 25.0         # straddle arc beyond this -> pixel ON the seam (strap collar)

D = json.load(open("src/parts/bolt_el6.json"))
FW, FH = D["face"]
SY, SXT, SXB = D["seam_y"], D["seam_x_top"], D["seam_x_bot"]
C = D["c1"]
paths = [[tuple(q) for q in p] for p in C["yellow"]] + \
        [[tuple(q) for q in p] for p in C["red"]]
n_yellow = len(C["yellow"])
PLATES = [(0.0, SXB, 0.0, SY), (SXB, FW, 0.0, SY),
          (0.0, SXT, SY, FH), (SXT, FW, SY, FH)]
# seams: (axis, coord, b0, b1) — axis 1 = horizontal line y=coord
SEAMS = [(1, SY, 0.0, FW), (0, SXT, SY, FH), (0, SXB, 0.0, SY)]
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
def path_dist(q):
    """distance from point q to the nearest channel centerline"""
    best = 1e9
    for p in paths:
        for i in range(len(p)-1):
            a, b = p[i], p[i+1]
            d2 = math.dist(a, b)
            if d2:
                t = max(0, min(1, ((q[0]-a[0])*(b[0]-a[0])+(q[1]-a[1])*(b[1]-a[1]))/d2**2))
                c = (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))
                best = min(best, math.dist(q, c))
            else:
                best = min(best, math.dist(q, a))
    return best

def seam_perp(q):
    """perpendicular distance to the nearest seam segment (inf if off-band)"""
    best = 1e9
    for axis, coord, b0, b1 in SEAMS:
        if b0 - 2 <= q[1-axis] <= b1 + 2:
            best = min(best, abs(q[axis] - coord))
    return best

def crossings(p):
    """[(arc_t, sin_theta, xy)] where the centerline crosses a seam.
    sin_theta = |cos of direction vs seam normal| = crossing steepness."""
    out, acc = [], 0.0
    for i in range(len(p)-1):
        a, b = p[i], p[i+1]
        d = math.dist(a, b)
        if d:
            for axis, coord, b0, b1 in SEAMS:
                if (a[axis]-coord)*(b[axis]-coord) <= 0 and a[axis] != b[axis]:
                    f = (coord - a[axis]) / (b[axis] - a[axis])
                    if 0 <= f <= 1:
                        q = (a[0]+f*(b[0]-a[0]), a[1]+f*(b[1]-a[1]))
                        if b0 - 2 <= q[1-axis] <= b1 + 2:
                            out.append((acc + f*d, abs(b[axis]-a[axis]) / d, q))
        acc += d
    return sorted(out)

# ---- pixel placement: seam-crossing anchors + even fill (spec 2026-07-10) ----
# Straddle anchors sit exactly KEEPOUT perpendicular from the seam (arc offset
# KEEPOUT/sin). Shallow crossings (straddle arc > GAP_MAX) instead pin a pixel
# ON the seam; its collar is carried by the bracket (plate gets a bite).
seg_len = [_plen(p) for p in paths]

def place(pitch):
    pmeta, onseam = [], []
    for si, p in enumerate(paths):
        L = seg_len[si]
        closed = math.dist(p[0], p[-1]) < 0.05
        anchors = []
        def walk_out(c, sgn, start):
            # walk the arc until TRUE perpendicular >= KEEPOUT (the analytic
            # offset under-delivers where the path curves or runs oblique)
            t = c + sgn * start
            while 0 <= t <= L and seam_perp(point_at(p, t)) < KEEPOUT:
                t += sgn * 0.25
            return t
        for c, sin_t, q in crossings(p):
            arc_half = KEEPOUT / max(sin_t, 1e-9)
            if 2 * arc_half > GAP_MAX:
                # pixel ON the seam (strap-carried collar) + pinned neighbors
                # so even-fill can't land inside the keepout on the oblique run
                anchors.extend([walk_out(c, -1, arc_half), c, walk_out(c, 1, arc_half)])
                onseam.append((si, c, q))
            else:
                anchors.extend([walk_out(c, -1, arc_half), walk_out(c, 1, arc_half)])
        merged = []
        for t in sorted(t for t in anchors if 0 <= t <= L):
            if not merged or t - merged[-1] >= PX_MIN:
                merged.append(t)
        if closed and merged:
            spans = [(merged[i], merged[i+1]) for i in range(len(merged)-1)] \
                    + [(merged[-1], merged[0] + L)]
            fixed = list(merged)
        elif closed:
            spans, fixed = [(0.0, L)], []
        else:
            ends = [0.0] + merged + [L]
            spans = list(zip(ends, ends[1:]))
            fixed = [0.0] + merged + [L]
        placed = list(fixed)
        for t1, t2 in spans:
            span = t2 - t1
            n = max(0, round(span / pitch) - 1)
            while n > 0 and span / (n + 1) < PX_MIN + 0.3:
                n -= 1
            placed.extend(t1 + j * span / (n + 1) for j in range(1, n + 1))
        if closed and not merged:
            n = max(1, round(L / pitch))
            placed = [j * L / n for j in range(n)]
        fx = set(round(t, 6) for t in fixed)
        for t in placed:
            tt = t % L if closed else min(t, L)
            xy = point_at(p, tt)
            pmeta.append([xy[0], xy[1], si, tt, 0.0, round(t, 6) in fx])
    return pmeta, onseam

def relax(pmeta):
    """existing crossing de-conflict physics; anchors are immovable/undroppable"""
    def live_pairs():
        live = [k for k in range(len(pmeta)) if pmeta[k] is not None]
        return [(a, b) for i, a in enumerate(live) for b in live[i+1:]
                if math.dist(pmeta[a][:2], pmeta[b][:2]) < PX_MIN]
    for _ in range(60):
        prs = live_pairs()
        if not prs:
            break
        for a, b in prs:
            if pmeta[a] is None or pmeta[b] is None:
                continue
            for idx, oth in ((a, b), (b, a)):
                x, y, si, t, mv, fx = pmeta[idx]
                if fx or abs(mv) >= 9.0:
                    continue
                L = seg_len[si]
                bt, bd = t, math.dist(pmeta[idx][:2], pmeta[oth][:2])
                for dt in (-0.8, 0.8):
                    t2 = min(max(t + dt, 0.0), L)
                    cand = point_at(paths[si], t2)
                    d2 = math.dist(cand, pmeta[oth][:2])
                    if d2 > bd and seam_perp(cand) >= KEEPOUT:
                        bt, bd = t2, d2
                if bt != t:
                    nx, ny = point_at(paths[si], bt)
                    pmeta[idx] = [nx, ny, si, bt, mv + (bt - t), fx]
    dropped = 0
    while True:
        prs = live_pairs()
        if not prs:
            break
        a, b = min(prs, key=lambda pr: math.dist(pmeta[pr[0]][:2], pmeta[pr[1]][:2]))
        if math.dist(pmeta[a][:2], pmeta[b][:2]) >= 13.0:
            break                       # snug pairs: seat firmly, keep the light
        if pmeta[a][5] and pmeta[b][5]:
            break
        pmeta[a if not pmeta[a][5] else b] = None
        dropped += 1
    return dropped

# solve pitch so the board lands exactly on its pixel budget
pick = None
p_lo, p_hi = 19.0, float(arg("--pitch-max", "23"))
pitch = p_lo
while pitch <= p_hi + 1e-9:
    pmeta, onseam = place(pitch)
    dropped = relax(pmeta)
    n = sum(1 for m in pmeta if m is not None)
    if n <= PX_BUDGET and (pick is None or n > pick[0]):
        pick = (n, pitch, pmeta, onseam, dropped)
    if n <= PX_BUDGET - 3:
        break
    pitch = round(pitch + 0.1, 4)
n_px, PITCH, pmeta, onseam, dropped = pick
assert n_px <= PX_BUDGET, "over pixel budget"
pixels = [[round(m[0], 2), round(m[1], 2), m[2], 1 if m[5] else 0]
          for m in pmeta if m is not None]
pix_t = [m[3] for m in pmeta if m is not None]
onseam_xy = [(round(q[0], 2), round(q[1], 2)) for si, c, q in onseam]
ny_px = sum(1 for p in pixels if p[2] < n_yellow)
print("pixels: %d @ pitch %.1f (%d yellow, %d red), %d dropped, %d on-seam (bracket collars)"
      % (len(pixels), PITCH, ny_px, len(pixels) - ny_px, dropped, len(onseam_xy)))

# gap QA: seam-adjacent spacing must stay near pitch (the whole point)
bysi = {}
for m in pmeta:
    if m is not None:
        bysi.setdefault(m[2], []).append(m[3])
max_seam_gap = 0
for si, p in enumerate(paths):
    L = seg_len[si]
    ts = sorted(bysi.get(si, []))
    closed = math.dist(p[0], p[-1]) < 0.05
    pairs = list(zip(ts, ts[1:])) + ([(ts[-1], ts[0] + L)] if closed and len(ts) > 1 else [])
    cr = [c for c, s, q in crossings(p)]
    for t1, t2 in pairs:
        if any(t1 - 0.5 <= c <= t2 + 0.5 or t1 - 0.5 <= c + L <= t2 + 0.5 for c in cr):
            max_seam_gap = max(max_seam_gap, t2 - t1)
print("max seam-adjacent gap: %.1fmm (pitch %.1f)" % (max_seam_gap, PITCH))
assert max_seam_gap < GAP_MAX, "seam gap regression"

def is_onseam(p):
    return (p[0], p[1]) in set(onseam_xy)

# ---- seam straps (brackets) ----
STRAP_W   = 48.0      # across the seam
STRAP_IN  = 20.0      # strap end inset from board edges / y-strap edge
SCR_OFF   = 8.0       # screw offset each side of the seam
SCR_CH    = 14.5      # screw center -> channel centerline floor (11 band + 2.25 + margin)
SCR_PX    = 16.0      # screw center -> pixel center floor (nut pocket vs Ø21 chamfer)
PAIR_STEP = (60, 85)  # target spacing between screw pairs along a seam
Y_SPLIT   = 145.5     # y-strap butt joint: in the quiet interval between the
                      # T-junctions (channel crossings at x=99/190/245/310);
                      # plates splice the joint, junction pairs flank it

def screw_ok(q):
    if path_dist(q) < SCR_CH:
        return False
    return all(math.dist(q, p[:2]) >= SCR_PX for p in pixels)

def pair_ok(axis, coord, u):
    a = (u, coord - SCR_OFF) if axis == 1 else (coord - SCR_OFF, u)
    b = (u, coord + SCR_OFF) if axis == 1 else (coord + SCR_OFF, u)
    return screw_ok(a) and screw_ok(b)

def place_pairs(axis, coord, u0, u1, required):
    """screw positions along a seam: required spots (strap ends, junction
    flanks) plus greedy fill at PAIR_STEP spacing. Pairs preferred; where an
    oblique channel shadows one side (e.g. the 31deg crossing), a required
    spot degrades to a single screw on the clear side — insertion force
    presses the strap against the plates, so ends only need to be held snug."""
    got, singles = [], []
    for ur in required:
        u = next((ur + s * d for d in range(0, 24, 2) for s in (1, -1)
                  if u0 <= ur + s * d <= u1 and pair_ok(axis, coord, ur + s * d)), None)
        if u is not None:
            got.append(u)
            continue
        one = next(((ur + s * d, sgn) for d in range(0, 24, 2) for s in (1, -1)
                    for sgn in (-1, 1)
                    if u0 <= ur + s * d <= u1 and screw_ok(
                        (ur + s * d, coord + sgn * SCR_OFF) if axis == 1
                        else (coord + sgn * SCR_OFF, ur + s * d))), None)
        assert one is not None, "no legal screw near u=%.0f on seam %s=%s" \
            % (ur, "xy"[axis], coord)
        singles.append(one)
    u = u0 + 8
    while u <= u1 - 8:
        if any(abs(u - g) < PAIR_STEP[0] for g in got + [s[0] for s in singles]):
            u += 2
            continue
        if pair_ok(axis, coord, u):
            got.append(u)
            u += PAIR_STEP[0]
        else:
            u += 2
    assert len(got) >= 2, "strap needs >=2 screw pairs"
    return sorted(got), singles

# strap definitions: (name, axis, coord, u0, u1)
straps = [
    ("S1", 1, SY, STRAP_IN, Y_SPLIT - 0.15),
    ("S2", 1, SY, Y_SPLIT + 0.15, FW - STRAP_IN),
    ("S3", 0, SXT, SY + STRAP_W/2 + 2, FH - STRAP_IN),
    ("S4", 0, SXB, STRAP_IN, SY - STRAP_W/2 - 2),
]
# required screw-pair spots: T-junction flanks on the y-straps, butt-joint
# flanks, and each strap's ends
req = {
    # 139.5 = shared flank between the two T-junctions (27mm apart) and the
    # butt joint's near-side pair; 167 = SXB's right flank + joint far side
    "S1": [STRAP_IN + 10, SXT - 14, (SXT + SXB) / 2],
    "S2": [SXB + 14, FW - STRAP_IN - 10],
    "S3": [SY + STRAP_W/2 + 12, FH - STRAP_IN - 10],
    "S4": [STRAP_IN + 10, SY - STRAP_W/2 - 12],
}
scr_screws = {}     # strap -> [(u, side or 0=both)...]
scr = []            # face machine-screw holes (board coords)
for name, axis, coord, u0, u1 in straps:
    us, singles = place_pairs(axis, coord, u0, u1, req[name])
    scr_screws[name] = [(u, -1) for u in us] + [(u, 1) for u in us] + singles
    for u, sgn in scr_screws[name]:
        q = (u, coord + sgn * SCR_OFF) if axis == 1 else (coord + sgn * SCR_OFF, u)
        scr.append([round(q[0], 1), round(q[1], 1), 1])       # 1 = machine screw

# perimeter wood screws (frame attachment): bottom/top rows + side columns
def fill_edge(axis, coord, v0, v1, step):
    got, v = [], v0
    while v <= v1:
        q = (v, coord) if axis == 1 else (coord, v)
        if screw_ok(q):
            got.append(q)
            v += step
        else:
            v += 3
    q = (v1, coord) if axis == 1 else (coord, v1)
    if screw_ok(q) and (not got or math.dist(got[-1], q) > 40):
        got.append(q)
    return got

for q in (fill_edge(1, 6, 12, FW - 12, 130) + fill_edge(1, FH - 6, 12, FW - 12, 130)
          + fill_edge(0, 6, 130, FH - 130, 145) + fill_edge(0, FW - 6, 130, FH - 130, 145)):
    scr.append([round(q[0], 1), round(q[1], 1), 0])           # 0 = wood screw
n_mach = sum(1 for s in scr if s[2])
print("screws: %d machine (M4x8 + captive nut) + %d wood"
      % (n_mach, len(scr) - n_mach))

def plate_of(x, y):
    for i, (x0, x1, y0, y1) in enumerate(PLATES):
        if x0 <= x < x1 and y0 <= y < y1:
            return i + 1
    return 0

# strap features in LOCAL PRINTED coords. Local frame: u along the seam,
# v_m ACROSS; the strap prints front-face-down and is FLIPPED about u to
# install, so v_m = -(board v). Baking the mirror here keeps bracket.scad
# dumb (see the chiral flip-to-use gotcha).
def to_local(name, q):
    axis, coord = {"S1": (1, SY), "S2": (1, SY), "S3": (0, SXT), "S4": (0, SXB)}[name]
    u = q[0] if axis == 1 else q[1]
    v = (q[1] - coord) if axis == 1 else (q[0] - coord)
    return (round(u, 2), round(-v, 2))

def straps_of(q, catch=8.5):
    """ALL straps whose footprint the point's flange/hole zone overlaps — a
    pixel near a T-junction can touch two straps and needs a hole in each."""
    out = []
    for name, axis, coord, u0, u1 in straps:
        v = (q[1] - coord) if axis == 1 else (q[0] - coord)
        u = q[0] if axis == 1 else q[1]
        if abs(v) <= STRAP_W/2 + catch and u0 - catch <= u <= u1 + catch:
            out.append(name)
    return out

def strap_of(q):
    ss = straps_of(q)
    return ss[0] if ss else None

feat = {name: {"pass": [], "collar": [], "nut": [], "socket": []} for name, *_ in straps}
for p in pixels:
    for s in straps_of(p[:2]):
        (feat[s]["collar"] if is_onseam(p) else feat[s]["pass"]).append(to_local(s, p[:2]))
for name in scr_screws:
    axis, coord = {"S1": (1, SY), "S2": (1, SY), "S3": (0, SXT), "S4": (0, SXB)}[name]
    for u, sgn in scr_screws[name]:
        q = (u, coord + sgn * SCR_OFF) if axis == 1 else (coord + sgn * SCR_OFF, u)
        feat[name]["nut"].append(to_local(name, q))
n_collar = sum(len(f["collar"]) for f in feat.values())
assert n_collar == len(onseam_xy), "every on-seam pixel needs a strap collar"

# leg sockets: T-junctions + y-midspan, nudged to clear pixels/features and
# sit fully interior to a strap segment (boss r8 must not overhang an end)
def socket_ok(q):
    s = strap_of(q)
    if s is None:
        return False
    u0, u1 = dict((n, (a, b)) for n, _, _, a, b in straps)[s]
    if not (u0 + 10 <= q[0] <= u1 - 10):
        return False
    return (all(math.dist(q, p[:2]) >= 16.5 for p in pixels)      # boss r8 vs Ø17 hole
            and all(math.dist(q, sc[:2]) >= 11.5 for sc in scr))  # boss r8 vs Ø4.5 hole
cands = [u for u in range(int(STRAP_IN) + 10, int(FW - STRAP_IN) - 10, 2)
         if socket_ok((float(u), SY))]
assert len(cands) >= 3, "not enough leg-socket room on the y-seam"
for u in (cands[0], cands[len(cands)//2], cands[-1]):   # spread: ends + middle
    q = (float(u), SY)
    s = strap_of(q)
    feat[s]["socket"].append(to_local(s, q))
print("straps: " + "; ".join(
    "%s %d pass/%d collar/%d nut/%d socket" %
    (n, len(f["pass"]), len(f["collar"]), len(f["nut"]), len(f["socket"]))
    for n, f in feat.items()))

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

fmt = lambda pts: "[" + ",".join(
    "[" + ",".join("%.2f" % v for v in q) + "]" for q in pts) + "]"
with open("src/parts/board_layout.scad", "w") as f:
    f.write("// AUTO-GENERATED by tools/boltboard.py — element-6 bolt board\n")
    f.write("bb_face = [%.1f, %.1f];\n" % (FW, FH))
    f.write("bb_plates = [%s];\n" % ",".join(
        "[%.1f,%.1f,%.1f,%.1f]" % r for r in PLATES))
    f.write("bb_paths = [\n  %s\n];\n" % ",\n  ".join(fmt(p) for p in paths))
    # bb_px excludes on-seam pixels (no plate collar); bb_bite replaces them
    f.write("bb_px = %s;\n" % fmt([p[:3] for p in pixels if not is_onseam(p)]))
    f.write("bb_bite = %s;\n" % fmt(onseam_xy))
    f.write("bb_scr = %s;\n" % fmt(scr))
    f.write("bb_tie = [];\n")
    f.write("bb_fuzz_ctr = [%s];\n" % ",".join(
        "[%.2f,%.2f]" % c for c in fuzz_ctr))
with open("src/parts/bracket_layout.scad", "w") as f:
    f.write("// AUTO-GENERATED by tools/boltboard.py — seam strap layout\n")
    f.write("// LOCAL PRINTED coords: u along seam, v pre-mirrored for the\n")
    f.write("// front-face-down print + flip-to-install (chirality baked here).\n")
    f.write("bk_strap_w = %.1f;\n" % STRAP_W)
    f.write("bk_names = [%s];\n" % ",".join('"%s"' % n for n, *_ in straps))
    f.write("bk_span = [%s];\n" % ",".join(
        "[%.2f,%.2f]" % (u0, u1) for _, _, _, u0, u1 in straps))
    for key in ("pass", "collar", "nut", "socket"):
        f.write("bk_%s = [%s];\n" % (key, ",".join(
            fmt(feat[n][key]) if feat[n][key] else "[]" for n, *_ in straps)))
json.dump({"pitch": PITCH,
           "chain_note": "chain = physical data order (one chain, addressable "
                         "pixels); links over 101.6mm need an extension jumper",
           "pixels": [{"x": p[0], "y": p[1],
           "color": "yellow" if p[2] < n_yellow else "red",
           "plate": plate_of(p[0], p[1]),
           "mount": "bracket" if is_onseam(p) else "plate",
           "chain": chain_of[i]} for i, p in enumerate(pixels)]},
          open("src/parts/bolt_pixmap.json", "w"), indent=1)
counts = [sum(1 for p in pixels if plate_of(p[0], p[1]) == pl) for pl in (1, 2, 3, 4)]
print("plate px: B1 %d / B2 %d / B3 %d / B4 %d" % tuple(counts))
print("wrote board_layout.scad + bracket_layout.scad + bolt_pixmap.json + fuzz")
