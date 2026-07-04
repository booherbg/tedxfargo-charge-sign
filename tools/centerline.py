#!/usr/bin/env python3
"""Tube-centerline extractor: EPS neon-letter art -> ordered centerline path(s) +
pixel points at a set pitch, as an OpenSCAD data file. Pure stdlib (no numpy):
ghostscript rasterizes the EPS to PGM, a Zhang-Suen pass thins each tube band to a
1px skeleton, then we trace/smooth/resample.

The art's letters are made of OPEN neon-tube segments (e.g. the C = 2 arcs), so
paths are traced end-to-end; closed loops are still handled if a letter has one.

Usage:
  centerline.py LETTER.eps --ref H.eps --cap 270 --pitch 17 --name C --out src/parts/letter_C_data.scad
    --ref    letter whose ink height defines cap height (H = flat-top reference)
    --cap    reference letter height in mm at final scale
    --pitch  pixel spacing along the centerline (mm)
    --dpi    raster resolution (default 1200 ~= 2.3 px/mm at 270mm cap)
Also writes OUT.debug.ppm (ink + skeleton + pixels) next to the .scad for eyeballing.
"""
import re, subprocess, sys, math, os

# ---------- args ----------
def arg(flag, default=None):
    if flag in sys.argv:
        return sys.argv[sys.argv.index(flag) + 1]
    if default is None:
        sys.exit("missing " + flag)
    return default

eps    = sys.argv[1]
ref    = arg("--ref")
cap_mm = float(arg("--cap", "270"))
pitch  = float(arg("--pitch", "17"))
name   = arg("--name")
out    = arg("--out")
dpi    = int(arg("--dpi", "1200"))
THRESH = 245          # ink = anything darker than near-white (art is light cyan ~189)
SPUR_MM = 6.0         # drop dangling skeleton edges shorter than this (spurs, tip clumps)
RUNG_MM = 9.0         # drop short junction-junction edges (sliver bridges where art kisses)
MIN_PATH_MM = 30.0    # ignore debris segments shorter than this
GEO_STEP = 4.0        # emitted path point spacing (mm); sagitta on a 50mm-radius arc ~0.04mm

# ---------- raster: EPS -> ink pixel set ----------
def raster(path, dpi):
    pgm = subprocess.run(
        ["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dEPSCrop",
         "-sDEVICE=pgmraw", "-r%d" % dpi, "-o", "-", path],
        capture_output=True, check=True).stdout
    m = re.match(rb"P5\s+(?:#[^\n]*\n\s*)*(\d+)\s+(?:#[^\n]*\n\s*)*(\d+)\s+(?:#[^\n]*\n\s*)*(\d+)\s", pgm)
    w, h = int(m.group(1)), int(m.group(2))
    px = pgm[m.end():]
    ink = set()
    for y in range(h):
        row = px[y * w:(y + 1) * w]
        for x in range(w):
            if row[x] < THRESH:
                ink.add((x, y))
    return w, h, ink

def bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

# ---------- Zhang-Suen thinning ----------
N8 = [(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]  # P2..P9 clockwise
def thin(S):
    S = set(S)
    while True:
        removed = 0
        for phase in (0, 1):
            kill = []
            for p in S:
                x, y = p
                nb = [(x+dx, y+dy) in S for dx, dy in N8]
                B = sum(nb)
                if not (2 <= B <= 6):
                    continue
                A = sum(1 for i in range(8) if not nb[i] and nb[(i+1) % 8])
                if A != 1:
                    continue
                # nb indices: 0=P2(N) 1=P3 2=P4(E) 3=P5 4=P6(S) 5=P7 6=P8(W) 7=P9
                if phase == 0:
                    if (nb[0] and nb[2] and nb[4]) or (nb[2] and nb[4] and nb[6]):
                        continue
                else:
                    if (nb[0] and nb[2] and nb[6]) or (nb[0] and nb[4] and nb[6]):
                        continue
                kill.append(p)
            S.difference_update(kill)
            removed += len(kill)
        if not removed:
            return S

# ---------- skeleton graph cleanup ----------
def neighbors(p, S):
    x, y = p
    return [(x+dx, y+dy) for dx, dy in N8 if (x+dx, y+dy) in S]

def components(S):
    S, comps = set(S), []
    while S:
        seed = next(iter(S))
        comp, stack = {seed}, [seed]
        while stack:
            for n in neighbors(stack.pop(), S):
                if n not in comp:
                    comp.add(n); stack.append(n)
        comps.append(comp)
        S -= comp
    return comps

def _plen(pts):
    return sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))

def decompose(S, mm_px, spur_mm=6.0, rung_mm=9.0, min_mm=30.0):
    """Skeleton px -> ordered centerline segments [(pts, closed)].

    Degree!=2 px are clustered into graph nodes; degree-2 chains between clusters
    are edges. Short dangling edges (spurs, ZS tip clumps) and short node-to-node
    edges (sliver rungs where art shapes kiss) are dropped. At each node the
    surviving edge-ends are PAIRED BY STRAIGHTEST CONTINUATION, so tubes that
    merely touch (the A's top piece on its counter apex) pass through the crossing
    independently. Very sharp V-apexes may refuse to pair (dot >= .3) and yield an
    open segment with kissing ends — geometrically identical once stroked with
    round caps, so that's fine."""
    segments = []
    for comp in components(S):
        nodepx = {p for p in comp if len(neighbors(p, comp)) != 2}
        if not nodepx:                                  # pure cycle
            start = next(iter(comp)); prev, cur, pts = None, start, [start]
            while True:
                nxt = [n for n in neighbors(cur, comp) if n != prev][0]
                if nxt == start:
                    break
                pts.append(nxt); prev, cur = cur, nxt
            segments.append((pts, True))
            continue
        clusters = components(nodepx)
        cid = {p: i for i, c in enumerate(clusters) for p in c}
        edges, seen = [], set()
        for c in clusters:
            for p in c:
                for n in neighbors(p, comp):
                    if n in cid or (p, n) in seen:
                        continue
                    pts, prev, cur = [p, n], p, n
                    while cur not in cid:
                        nxt = [q for q in neighbors(cur, comp) if q != prev][0]
                        pts.append(nxt); prev, cur = cur, nxt
                    seen.add((pts[0], pts[1])); seen.add((pts[-1], pts[-2]))
                    edges.append(pts)
        # drop spurs (short + a dead end) and rungs (short between junctions), iteratively
        while True:
            nedges = {}
            for e in edges:
                for cl in (cid[e[0]], cid[e[-1]]):
                    nedges[cl] = nedges.get(cl, 0) + 1
            drop = []
            for e in edges:
                L = _plen(e) * mm_px
                da = nedges[cid[e[0]]] == 1
                db = nedges[cid[e[-1]]] == 1
                if (da or db) and L < spur_mm:
                    drop.append(e)                     # dangling spur / tip clump
                elif (nedges[cid[e[0]]] >= 3 and nedges[cid[e[-1]]] >= 3
                      and L < rung_mm):
                    drop.append(e)                     # sliver rung between REAL junctions
                    # (2-end pass-through clusters are staircase artifacts mid-line —
                    #  short edges between those are healthy path, never dropped)
            if not drop:
                break
            edges = [e for e in edges if e not in drop]
        if not edges:
            continue
        # pair edge-ends at each cluster by straightest continuation
        def outdir(e, side):
            a = e[0] if side == 0 else e[-1]
            b = e[min(6, len(e)-1)] if side == 0 else e[max(-7, -len(e))]
            d = math.dist(a, b) or 1.0
            return ((b[0]-a[0])/d, (b[1]-a[1])/d)
        at = {}
        for ei, e in enumerate(edges):
            at.setdefault(cid[e[0]], []).append((ei, 0))
            at.setdefault(cid[e[-1]], []).append((ei, 1))
        link = {}
        for cl, ends in at.items():
            free = list(ends)
            while len(free) >= 2:
                best, bi, bj = 2.0, None, None
                for i in range(len(free)):
                    for j in range(i+1, len(free)):
                        di, dj = outdir(edges[free[i][0]], free[i][1]), outdir(edges[free[j][0]], free[j][1])
                        dot = di[0]*dj[0] + di[1]*dj[1]
                        if dot < best:
                            best, bi, bj = dot, i, j
                if best >= 0.3:                        # nothing continues straight enough
                    break
                a, b = free[bj], free[bi]              # pop higher index first
                link[free[bi]] = free[bj]; link[free[bj]] = free[bi]
                free.pop(bj); free.pop(bi)
        # assemble chains through the links
        visited = set()
        def run(ei, entry):
            pts = []
            while True:
                visited.add(ei)
                e = edges[ei] if entry == 0 else edges[ei][::-1]
                pts.extend(e)
                exit_end = (ei, 1 - entry)
                if exit_end not in link:
                    return pts, False
                nei, nside = link[exit_end]
                if nei in visited:
                    return pts, True                   # closed the loop
                ei, entry = nei, nside
        for ei in range(len(edges)):
            if ei in visited:
                continue
            side = 0 if (ei, 0) not in link else (1 if (ei, 1) not in link else None)
            if side is not None:                       # open chain: start at a free end
                pts, closed = run(ei, side)
                segments.append((pts, closed))
        for ei in range(len(edges)):                   # remaining = pure cycles via links
            if ei not in visited:
                pts, _ = run(ei, 0)
                segments.append((pts, True))
    return [(pts, cl) for pts, cl in segments if _plen(pts) * mm_px >= min_mm]

# ---------- polyline ops ----------
def smooth(pts, win, closed):
    n, half = len(pts), win // 2
    outp = []
    for i in range(n):
        if closed:
            w = [pts[(i+j) % n] for j in range(-half, half+1)]
        else:
            w = pts[max(0, i-half):min(n, i+half+1)]
        outp.append((sum(p[0] for p in w)/len(w), sum(p[1] for p in w)/len(w)))
    return outp

def path_len(pts, closed):
    L = sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))
    return L + (math.dist(pts[-1], pts[0]) if closed else 0)

def resample(pts, step, closed):
    """Even respacing at ~step. Open: includes BOTH endpoints. Closed: N=round(L/step)."""
    L = path_len(pts, closed)
    if closed:
        n = max(3, round(L / step))
        targets = [i * L / n for i in range(n)]
        src = pts + [pts[0]]
    else:
        n = max(2, round(L / step) + 1)
        targets = [i * L / (n - 1) for i in range(n)]
        src = pts
    outp, acc, i = [], 0.0, 0
    for t in targets:
        while i < len(src) - 2 and acc + math.dist(src[i], src[i+1]) < t:
            acc += math.dist(src[i], src[i+1]); i += 1
        d = math.dist(src[i], src[i+1])
        f = (t - acc) / d if d > 1e-9 else 0
        f = min(max(f, 0.0), 1.0)
        outp.append((src[i][0] + (src[i+1][0]-src[i][0])*f,
                     src[i][1] + (src[i+1][1]-src[i][1])*f))
    return outp

# ---------- main ----------
w, h, ink = raster(eps, dpi)
_, _, rink = raster(ref, dpi)
_, ry0, _, ry1 = bbox(rink)
mm_px = cap_mm / (ry1 - ry0 + 1)               # scale: ref letter ink height == cap height
px_mm = 1.0 / mm_px

skel = thin(ink)
traced = decompose(skel, mm_px, spur_mm=SPUR_MM, rung_mm=RUNG_MM, min_mm=MIN_PATH_MM)

# px -> mm: flip Y (image y-down), then shift so the centerline bbox min is (0,0)
x0, y0, x1, y1 = bbox([p for pts, _ in traced for p in pts])
win = max(3, int(2.0 * px_mm) | 1)             # ~2mm moving-average window, odd
paths, flags, pixels = [], [], []
for pts, closed in traced:
    mm = [((p[0] - x0) * mm_px, (y1 - p[1]) * mm_px) for p in smooth(pts, win, closed)]
    fine = resample(mm, 1.5, closed)           # smooth working polyline
    paths.append(resample(fine, GEO_STEP, closed))
    flags.append(1 if closed else 0)
    pixels += resample(fine, pitch, closed)    # pixel centers at pitch (ends included)

bw, bh = (x1 - x0) * mm_px, (y1 - y0) * mm_px
lens = [path_len(p, f) for p, f in zip(paths, flags)]
total = sum(lens)
band_w = len(ink) * mm_px * mm_px / total      # measured original tube width

fmt_path = lambda c: "[%s]" % ",".join("[%.2f,%.2f]" % (x, y) for x, y in c)
with open(out, "w") as f:
    f.write("// AUTO-GENERATED by tools/centerline.py — do not hand-edit\n")
    f.write("// %s @ cap %.0fmm (ref %s): centerline bbox %.1f x %.1f mm, tube ~%.1fmm wide\n"
            % (os.path.basename(eps), cap_mm, os.path.basename(ref), bw, bh, band_w))
    f.write("// %d tube segment(s), %s mm, %d pixels @ %.1fmm pitch\n"
            % (len(paths), "+".join("%.0f" % L for L in lens), len(pixels), pitch))
    f.write("%s_paths = [\n    %s\n];\n" % (name, ",\n    ".join(fmt_path(p) for p in paths)))
    f.write("%s_closed = %s;\n" % (name, flags))
    f.write("%s_pixels = %s;\n" % (name, fmt_path(pixels)))
    f.write("%s_bbox = [%.2f, %.2f];\n" % (name, bw, bh))

# debug overlay: ink gray, skeleton red, pixels blue squares
dbg = out + ".debug.ppm"
img = bytearray(b"\xff" * (w * h * 3))
def put(x, y, r, g, b):
    if 0 <= x < w and 0 <= y < h:
        i = (y * w + x) * 3
        img[i:i+3] = bytes((r, g, b))
for x, y in ink:  put(x, y, 210, 210, 210)
for x, y in skel: put(x, y, 220, 0, 0)
for px_, py_ in pixels:
    cx, cy = int(px_ * px_mm + x0), int(y1 - py_ * px_mm)
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            put(cx + dx, cy + dy, 0, 0, 220)
with open(dbg, "wb") as f:
    f.write(b"P6\n%d %d\n255\n" % (w, h) + bytes(img))

print("%s: %d segment(s) [%s]mm %s, tube ~%.1fmm, bbox %.1fx%.1fmm, %d pixels @ %.1fmm"
      % (name, len(paths), "+".join("%.0f" % L for L in lens),
         ["open" if not f else "closed" for f in flags], band_w, bw, bh, len(pixels), pitch))
print("wrote %s + %s" % (out, dbg))
