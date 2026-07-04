#!/usr/bin/env python3
"""Panelize the CHARGE billboard: compute corridor cuts between letters (top-to-
bottom paths through black field, never near a channel), piece bboxes, a bed-fit
report, screw-hole positions, and a JSON + SVG for the cut-preview page.

Usage: panelize.py src/parts/word_data.scad --name WORD --out src/parts/word_cuts.json
Key params (mm): --band-out 22  --clear 5  --face-h 295  --bed-long 316 --bed-short 296
"""
import json, math, re, sys, heapq

def arg(flag, default=None):
    if flag in sys.argv:
        return sys.argv[sys.argv.index(flag) + 1]
    return default

src      = sys.argv[1]
name     = arg("--name", "WORD")
out      = arg("--out", "src/parts/word_cuts.json")
BAND_OUT = float(arg("--band-out", "22"))    # printed tube outer width
CLEAR    = float(arg("--clear", "5"))        # cut clearance beyond band edge
FACE_H   = float(arg("--face-h", "295"))     # uniform piece height
BED_LONG = float(arg("--bed-long", "316"))   # piece long-axis limit (H2D 320 - margin)
BED_SHORT= float(arg("--bed-short", "296"))  # piece short-axis limit (H2D 300 - margin)
G        = 2.0                               # planning grid cell (mm)
KEEPOUT  = BAND_OUT / 2 + CLEAR              # min distance cut <-> tube centerline (16)
SIDE_PAD = 6.0                               # black margin past the outer band at word ends
TUBE_G_MM  = 0.132                           # g per mm of channel (walls+liner+lens+collars, measured)
PLATE_G_MM2 = 0.00254                        # g per mm^2 of 2mm black plate

# ---------- load extractor data (the .scad data file is JSON-compatible) ----------
txt = open(src).read()
def grab(key):
    m = re.search(re.escape(name + "_" + key) + r"\s*=\s*(.*?);", txt, re.S)
    return json.loads(m.group(1))
paths, closed, pixels, bb = grab("paths"), grab("closed"), grab("pixels"), grab("bbox")
W, H = bb
PITCH    = float(arg("--pitch", "17"))       # pixel spacing along tube centerlines
PX_MIN   = float(arg("--px-min", "14.5"))    # min pixel-center spacing (flange O13.6 + margin)

def _plen(p):
    return sum(math.dist(p[i], p[i+1]) for i in range(len(p)-1))
def cut_at(c, y):
    lo = min(range(len(c)), key=lambda i: abs(c[i][1] - y))
    return c[lo][0]

# ---------- letter grouping (x-overlap clustering of segment band extents) ----------
def seg_ext(p):
    xs = [q[0] for q in p]
    return min(xs) - BAND_OUT/2, max(xs) + BAND_OUT/2
groups = []
for i, p in enumerate(sorted(range(len(paths)), key=lambda i: seg_ext(paths[i])[0])):
    x0, x1 = seg_ext(paths[p])
    for g in groups:
        ov = min(x1, g["x1"]) - max(x0, g["x0"])
        if ov > 0.35 * min(x1 - x0, g["x1"] - g["x0"]):
            g["segs"].append(p); g["x0"] = min(g["x0"], x0); g["x1"] = max(g["x1"], x1)
            break
    else:
        groups.append({"segs": [p], "x0": x0, "x1": x1})
groups.sort(key=lambda g: g["x0"])
letters = list("CHARGE")
assert len(groups) == len(letters), "expected %d letter groups, got %d" % (len(letters), len(groups))

# ---------- clearance field on a coarse grid (rebuilt after each kerning nudge) ----------
MARG = 14.0                                   # grid margin past the face on all sides
ox = oy = 0.0
gw = gh = 0
dist = {}
def build_field():
    global ox, oy, gw, gh, dist, W
    W = max(q[0] for p in paths for q in p)   # layout width follows the nudges
    ox, oy = -BAND_OUT/2 - SIDE_PAD - MARG, -(FACE_H - H)/2 - MARG
    gw = int((W + 2*(BAND_OUT/2 + SIDE_PAD + MARG)) / G) + 2
    gh = int((H + (FACE_H - H) + 2*MARG) / G) + 2
    seed = set()
    for p in paths:
        for i in range(len(p) - 1):
            d = math.dist(p[i], p[i+1])
            for t in range(int(d / G) + 1):
                f = t * G / d if d else 0
                seed.add((int((p[i][0] + (p[i+1][0]-p[i][0])*f - ox) / G),
                          int((p[i][1] + (p[i+1][1]-p[i][1])*f - oy) / G)))
    dist = {c: 0.0 for c in seed}             # chamfer (1 / 1.414) ~ euclidean +-4%
    pq = [(0.0, c) for c in seed]
    heapq.heapify(pq)
    while pq:
        d, (cx, cy) = heapq.heappop(pq)
        if d > dist.get((cx, cy), 1e18):
            continue
        for dx, dy, w in ((1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.414),(1,-1,1.414),(-1,1,1.414),(-1,-1,1.414)):
            n = (cx + dx, cy + dy)
            if 0 <= n[0] < gw and 0 <= n[1] < gh and d + w < dist.get(n, 1e18):
                dist[n] = d + w
                heapq.heappush(pq, (d + w, n))
def clear_mm(c):
    return dist.get(c, 99) * G

# ---------- corridor cuts ----------
# Pass 1 (widest path): what's the best achievable bottleneck clearance in this gap?
# Pass 2 (routed): shortest mid-corridor path at min(KEEPOUT, bottleneck - 1).
HARD_MIN = BAND_OUT / 2 + 0.6                # absolute floor: past the band edge + a hair
                                             # (kissing letters like A|R leave ~1mm black at
                                             #  the pinch — backed by the channel wall foot)

def widest(gx, c_lo, c_hi):
    best, pq = {}, []
    for cx in range(c_lo, c_hi + 1):
        c = (cx, 0)
        best[c] = clear_mm(c)
        heapq.heappush(pq, (-best[c], c))
    while pq:
        nb, c = heapq.heappop(pq)
        nb = -nb
        if nb < best.get(c, -1):
            continue
        if c[1] == gh - 1:
            return nb
        for dx, dy in ((-1,0),(1,0),(0,1),(-1,1),(1,1)):
            n = (c[0]+dx, c[1]+dy)
            if not (c_lo <= n[0] <= c_hi and 0 <= n[1] < gh):
                continue
            w = min(nb, clear_mm(n))
            if w > best.get(n, -1):
                best[n] = w
                heapq.heappush(pq, (-w, n))
    return 0.0

def corridor(gx):
    c_lo, c_hi = int((gx - 90 - ox)/G), int((gx + 90 - ox)/G)
    bottleneck = widest(gx, c_lo, c_hi)
    if bottleneck < HARD_MIN:
        sys.exit("gap at x=%.0f: best corridor clearance %.1fmm < hard floor %.1fmm" %
                 (gx, bottleneck, HARD_MIN))
    keep = min(max(HARD_MIN, min(KEEPOUT, bottleneck - 0.7)), bottleneck)
    def ok(c):
        return c_lo <= c[0] <= c_hi and 0 <= c[1] < gh and clear_mm(c) >= keep
    pq, best, prev = [], {}, {}
    for cx in range(c_lo, c_hi + 1):
        c = (cx, 0)
        if ok(c):
            best[c] = abs((ox + cx*G) - gx) * 0.02   # slight pull toward gap center
            heapq.heappush(pq, (best[c], c))
    goal = None
    while pq:
        d, c = heapq.heappop(pq)
        if d > best.get(c, 1e18):
            continue
        if c[1] == gh - 1:
            goal = c
            break
        for dx, dy, w in ((-1,0,1),(1,0,1),(0,1,1),(-1,1,1.4),(1,1,1.4)):
            n = (c[0]+dx, c[1]+dy)
            if not ok(n):
                continue
            nd = d + w * (1 + 2 / max(clear_mm(n) - keep + 2, 2)) \
                   + 0.08 * abs((ox + n[0]*G) - gx)          # stay straight: x-wiggle widens pieces
            if nd < best.get(n, 1e18):
                best[n], prev[n] = nd, c
                heapq.heappush(pq, (nd, n))
    if goal is None:
        sys.exit("no corridor found near x=%.0f at clearance %.1f" % (gx, keep))
    pts, c = [], goal
    while c in prev:
        pts.append(c); c = prev[c]
    pts.append(c); pts.reverse()
    mm = [(ox + (cx+0.5)*G, oy + (cy+0.5)*G) for cx, cy in pts]
    win = 3                                    # light smoothing, clamped ends
    sm = [(sum(q[0] for q in mm[max(0,i-win):i+win+1]) / len(mm[max(0,i-win):i+win+1]),
           sum(q[1] for q in mm[max(0,i-win):i+win+1]) / len(mm[max(0,i-win):i+win+1]))
          for i in range(len(mm))]
    return sm, round(bottleneck, 1)

# ---------- auto-kern: nudge letters apart until every seam has clearance ----------
SEAM_MIN = float(arg("--seam-min", "12.6"))   # want >=1.6mm black past the band edge at seams
nudges = [0.0] * (len(groups) - 1)
for _ in range(4):
    build_field()
    worst = 0.0
    for i in range(len(groups) - 1):
        gx = (groups[i]["x1"] + groups[i+1]["x0"]) / 2
        b = widest(gx, int((gx - 90 - ox)/G), int((gx + 90 - ox)/G))
        need = max(0.0, (SEAM_MIN - b) * 2)   # gap widens ~2x the per-side deficit
        if need > 0.2:
            worst = max(worst, need)
            nudges[i] += need
            thresh = gx
            for g in groups[i+1:]:
                for s in g["segs"]:
                    paths[s] = [(x + need, y) for x, y in paths[s]]
                g["x0"] += need; g["x1"] += need
            for k, (px, py) in enumerate(pixels):
                if px > thresh:
                    pixels[k] = [px + need, py]
    if worst == 0.0:
        break
if any(n > 0.2 for n in nudges):
    print("auto-kern: widened gaps by %s mm (sign +%.1fmm — invisible at 1.5m scale)"
          % (["%.1f" % n for n in nudges], sum(nudges)))

cut_results = [corridor((groups[i]["x1"] + groups[i+1]["x0"]) / 2) for i in range(len(groups) - 1)]
cuts = [c for c, _ in cut_results]
bottlenecks = [b for _, b in cut_results]

# ---------- pixels: resample on the kerned layout, then DE-CONFLICT ----------
# Segment ends each carry a pixel, so tube breaks/crossings can put two pixels
# closer than a bullet flange (O13.6) allows. Fix: shift end-pixels inward along
# their own path; where paths truly overlap (shared lit pocket), drop one.
def point_at(p, t):
    acc = 0.0
    for i in range(len(p) - 1):
        d = math.dist(p[i], p[i+1])
        if acc + d >= t:
            f = (t - acc) / d if d else 0
            return (p[i][0] + (p[i+1][0]-p[i][0])*f, p[i][1] + (p[i+1][1]-p[i][1])*f)
        acc += d
    return tuple(p[-1])

insets = [[0.0, 0.0] for _ in paths]          # per segment: [start inset, end inset]
def build_pmeta():
    """Chord-aware pixel placement: next pixel at >=PITCH along the arc AND
    >=PX_MIN+0.3 by straight-line chord — corners stretch a little instead of
    crowding flanges (a 90 elbow turns 17mm of arc into ~13.5mm of chord)."""
    pm = []
    for si, p in enumerate(paths):
        L = _plen(p)
        a, b = insets[si]
        lo, hi = a, max(L - b, a + 1.0)
        pts = [(point_at(p, lo), lo)]
        t = lo
        while True:
            t2 = t + PITCH
            while t2 < hi and math.dist(point_at(p, t2), pts[-1][0]) < PX_MIN + 0.3:
                t2 += 1.0
            if t2 >= hi - PITCH * 0.45:
                if math.dist(point_at(p, hi), pts[-1][0]) < PX_MIN + 0.3 and len(pts) > 1:
                    pts.pop()                 # end pixel wins over a crowding predecessor
                pts.append((point_at(p, hi), hi))
                break
            pts.append((point_at(p, t2), t2))
            t = t2
        for i, ((x, y), _) in enumerate(pts):
            pm.append([x, y, si, i, len(pts)])
    return pm
def conflict_pairs(pm, adjacent=False):
    """Pairs closer than PX_MIN. Along-path neighbors (same segment, |di|==1) are
    excluded unless adjacent=True: they can only get too close at hairpin corners,
    where the band folds onto itself (a merged pocket) — handled by dropping, never
    by insets (an inset would shrink the segment and make its own spacing worse)."""
    live = [k for k in range(len(pm)) if pm[k] is not None]
    return [(k, j, math.dist(pm[k][:2], pm[j][:2]))
            for ai, k in enumerate(live) for j in live[ai+1:]
            if (adjacent or pm[k][2] != pm[j][2] or abs(pm[k][3] - pm[j][3]) >= 2)
            and math.dist(pm[k][:2], pm[j][:2]) < PX_MIN]

for _ in range(4):                            # end conflicts: inset + re-spread the segment
    pmeta = build_pmeta()
    changed = False
    for k, j, d in conflict_pairs(pmeta):
        for idx in (k, j):
            x, y, si, i, n = pmeta[idx]
            end = 0 if i == 0 else (1 if i == n - 1 else None)
            if end is not None and insets[si][end] < 8.0:
                insets[si][end] = min(8.0, insets[si][end] + (PX_MIN - d) / 2 + 0.4)
                changed = True
    if not changed:
        break
pmeta = build_pmeta()
inset_n = sum(1 for s in insets if s[0] > 0 or s[1] > 0)
dropped = 0
while True:                                    # residual = crossings/hairpins: pocket is shared, drop
    pairs = conflict_pairs(pmeta, adjacent=True)
    if not pairs:
        break
    k, j, _ = min(pairs, key=lambda t: t[2])
    pmeta[j if pmeta[j][3] not in (0, pmeta[j][4]-1) else k] = None
    dropped += 1
pixels = [[m[0], m[1]] for m in pmeta if m is not None]
print("pixels: %d after de-conflict (%d segment ends re-spread, %d dropped at crossings)"
      % (len(pixels), inset_n, dropped))

# ---------- pieces, bed fit, screws ----------
face_x0, face_x1 = -BAND_OUT/2 - SIDE_PAD, W + BAND_OUT/2 + SIDE_PAD
face_y0, face_y1 = -(FACE_H - H)/2 + 0.0, H + (FACE_H - H)/2   # centered bands

# hardware: ALWAYS a screw in each piece corner (anti-lift), inset enough not to
# crack, then mid-span fill so no run exceeds MAX_SPAN
CORNER_INSET = float(arg("--corner-inset", "12"))   # from the piece's edge at that height
MAX_SPAN     = float(arg("--screw-span", "160"))    # add mid screws beyond this
scr_ys = (face_y0 + 6.0, face_y1 - 6.0)             # in the rail bands, clear of face edge + tubes
def cut_x_range(c):
    xs = [q[0] for q in c]
    return min(xs), max(xs)
pieces = []
for i in range(len(groups)):
    lx = face_x0 if i == 0 else cut_x_range(cuts[i-1])[0]
    rx = face_x1 if i == len(groups)-1 else cut_x_range(cuts[i])[1]
    wpc = rx - lx
    long_ax, short_ax = max(wpc, FACE_H), min(wpc, FACE_H)
    npx = sum(1 for px in pixels
              if (i == 0 or px[0] > cut_at(cuts[i-1], px[1])) and
                 (i == len(groups)-1 or px[0] <= cut_at(cuts[i], px[1])))
    tube_mm = sum(_plen(paths[s]) for s in groups[i]["segs"])
    grams = wpc * FACE_H * PLATE_G_MM2 + tube_mm * TUBE_G_MM
    screws = []
    for sy in scr_ys:                          # corners at THIS height (cuts wiggle) + fill
        ax = (face_x0 if i == 0 else cut_at(cuts[i-1], sy)) + CORNER_INSET
        bx = (face_x1 if i == len(groups)-1 else cut_at(cuts[i], sy)) - CORNER_INSET
        nmid = max(0, math.ceil((bx - ax) / MAX_SPAN) - 1)
        screws += [[round(ax + k * (bx - ax) / (nmid + 1), 1), round(sy, 1)]
                   for k in range(nmid + 2)]
    pieces.append({"letter": letters[i], "x0": round(lx,1), "x1": round(rx,1),
                   "w": round(wpc,1), "h": FACE_H, "fits": long_ax <= BED_LONG and short_ax <= BED_SHORT,
                   "pixels": npx, "grams": round(grams), "screws": screws})

json.dump({"face": [face_x0, face_y0, face_x1, face_y1], "face_h": FACE_H,
           "cuts": [[[round(x,2), round(y,2)] for x, y in c] for c in cuts],
           "bottlenecks_mm": bottlenecks, "kern_nudges_mm": [round(n,1) for n in nudges],
           "pieces": pieces, "band_out": BAND_OUT, "clear": CLEAR,
           # auto-kerned layout — AUTHORITATIVE for the geometry step
           "paths": [[[round(x,2), round(y,2)] for x, y in p] for p in paths],
           "closed": closed,
           "pixels": [[round(x,2), round(y,2)] for x, y in pixels]},
          open(out, "w"), indent=1)

print("face %.0f x %.0f mm, %d pieces; seam clearances (centerline->cut): %s mm"
      % (face_x1-face_x0, FACE_H, len(pieces), bottlenecks))
for p in pieces:
    print("  %s: %6.1f x %.0f mm  %s  %3d px  ~%dg" %
          (p["letter"], p["w"], p["h"], "FITS " if p["fits"] else "OVER!", p["pixels"], p["grams"]))
print("wrote", out)
