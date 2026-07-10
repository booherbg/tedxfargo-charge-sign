#!/usr/bin/env python3
"""Independent QA audit of the bolt board + seam straps. Checks the EMITTED
data (board_layout / bracket_layout / pixmap) and the BUILT meshes (plates,
3MFs, straps, pusher) against the design rules — not the generator's own
bookkeeping. Writes src/parts/board_qa.json (read by gen_bracketpreview.py)
and exits 1 on any FAIL.
Rules: spec docs/superpowers/specs/2026-07-10-seam-bracket-design.md +
docs/locked-specs.md (26mm nesting, 14.5 pixel floor / 13.0 snug, 316x295 bed).
"""
import json, math, re, struct, sys, zipfile
from collections import Counter

def grab(txt, key):
    return json.loads(re.search(key + r"\s*=\s*(\[.*?\]);", txt, re.S).group(1))

def read_stl(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:300]:
        tris, cur = [], []
        for line in data.decode(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("vertex"):
                cur.extend(float(v) for v in line.split()[1:4])
                if len(cur) == 9:
                    tris.append(tuple(cur)); cur = []
        return tris
    n = struct.unpack("<I", data[80:84])[0]
    return [tuple(struct.unpack("<9f", data[84+i*50+12:84+i*50+48])) for i in range(n)]

def vset(tris):
    return set(tuple(round(c, 3) for c in t[j:j+3]) for t in tris for j in (0, 3, 6))

def ring_r(verts, cx, cy, z0, z1, rmax=12, rmin=0.0):
    rs = [r for v in verts
          if abs(v[0]-cx) < rmax and abs(v[1]-cy) < rmax and z0 <= v[2] <= z1
          and (r := math.hypot(v[0]-cx, v[1]-cy)) >= rmin]
    return min(rs) if rs else None

def bad_edges(tris_idx):
    edges = Counter()
    for a, b, c in tris_idx:
        for e in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted(e))] += 1
    return sum(1 for n in edges.values() if n != 2)

def stl_bad_edges(tris):
    vid, idx = {}, []
    for t in tris:
        tri = [vid.setdefault(tuple(round(c, 5) for c in t[j:j+3]), len(vid))
               for j in (0, 3, 6)]
        idx.append(tuple(tri))
    return bad_edges(idx)

# ---- load everything ----
D = json.load(open("src/parts/bolt_el6.json"))
FW, FH = D["face"]
SY, SXT, SXB = D["seam_y"], D["seam_x_top"], D["seam_x_bot"]
paths = [[tuple(q) for q in p] for p in D["c1"]["yellow"]] + \
        [[tuple(q) for q in p] for p in D["c1"]["red"]]
SEAMS = [(1, SY, 0.0, FW), (0, SXT, SY, FH), (0, SXB, 0.0, SY)]
lay = open("src/parts/board_layout.scad").read()
bb_px, bb_bite, bb_scr = grab(lay, "bb_px"), grab(lay, "bb_bite"), grab(lay, "bb_scr")
plates = grab(lay, "bb_plates")
bk = open("src/parts/bracket_layout.scad").read()
bk_w = float(re.search(r"bk_strap_w = ([\d.]+);", bk).group(1))
bk_span = grab(bk, "bk_span")
bk_pass, bk_collar = grab(bk, "bk_pass"), grab(bk, "bk_collar")
bk_nut, bk_socket = grab(bk, "bk_nut"), grab(bk, "bk_socket")
NAMES = ["S1", "S2", "S3", "S4"]
STRAP_AX = {"S1": (1, SY), "S2": (1, SY), "S3": (0, SXT), "S4": (0, SXB)}
pixmap = json.load(open("src/parts/bolt_pixmap.json"))
PX = pixmap["pixels"]
allpx = [(p["x"], p["y"]) for p in PX]

def path_dist(q):
    best = 1e9
    for p in paths:
        for i in range(len(p)-1):
            a, b = p[i], p[i+1]
            d2 = math.dist(a, b)
            if d2:
                t = max(0, min(1, ((q[0]-a[0])*(b[0]-a[0])+(q[1]-a[1])*(b[1]-a[1]))/d2**2))
                best = min(best, math.dist(q, (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))))
    return best

def seam_perp(q):
    best = 1e9
    for axis, coord, b0, b1 in SEAMS:
        if b0 - 2 <= q[1-axis] <= b1 + 2:
            best = min(best, abs(q[axis] - coord))
    return best

def unlocal(name, q):
    axis, coord = STRAP_AX[name]
    u, v = q[0], -q[1]
    return (u, coord + v) if axis == 1 else (coord + v, u)

results = []
def check(name, ok, detail):
    results.append({"name": name, "ok": bool(ok), "detail": detail})
    print("%s %-52s %s" % ("PASS" if ok else "FAIL", name, detail))

# ---- A. placement physics ----
check("pixel count == 137 (budget)", len(PX) == 137, "%d px" % len(PX))
ny = sum(1 for p in PX if p["color"] == "yellow")
check("color zones 116 yellow / 21 red", ny == 116 and len(PX)-ny == 21,
      "%d/%d" % (ny, len(PX)-ny))
dmin, snug = 1e9, 0
for i in range(len(allpx)):
    for j in range(i+1, len(allpx)):
        d = math.dist(allpx[i], allpx[j])
        if d < dmin:
            dmin = d
        if d < 14.5:
            snug += 1
check("min pixel spacing >= 13.0 (snug band ok)", dmin >= 13.0,
      "min %.1f mm, %d snug pair(s) <14.5" % (dmin, snug))
kmin = min((seam_perp(q) for q in ((p[0], p[1]) for p in bb_px)
            if seam_perp(q) < 1e8), default=99)
check("plate-collar pixels >= 9.4 mm off seams", kmin >= 9.4, "min %.2f mm" % kmin)
onseam = [(p["x"], p["y"]) for p in PX if p.get("mount") == "bracket"]
bite_match = sorted(onseam) == sorted((b[0], b[1]) for b in bb_bite)
check("2 on-seam pixels == 2 plate bites (coords match)",
      len(onseam) == 2 and bite_match, str(onseam))
sc_local = sorted(unlocal(NAMES[i], q) for i in range(4) for q in bk_collar[i])
check("strap collars sit exactly at the bites",
      all(math.dist(a, b) < 0.02 for a, b in zip(sc_local, sorted(onseam))),
      str(sc_local))
# seam-adjacent gaps (arc, via nearest-path assignment)
def t_of(path, q):
    best, acc = (1e9, 0), 0.0
    for i in range(len(path)-1):
        a, b = path[i], path[i+1]
        d = math.dist(a, b)
        if d:
            t = max(0, min(1, ((q[0]-a[0])*(b[0]-a[0])+(q[1]-a[1])*(b[1]-a[1]))/d**2))
            c = (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))
            if math.dist(q, c) < best[0]:
                best = (math.dist(q, c), acc + t*d)
        acc += d
    return best
assign = {}
for q in allpx:
    b = min(((t_of(p, q)[0], si, t_of(p, q)[1]) for si, p in enumerate(paths)))
    assign.setdefault(b[1], []).append(b[2])
worst = 0
for si, p in enumerate(paths):
    acc = 0.0
    for i in range(len(p)-1):
        a, b = p[i], p[i+1]
        d = math.dist(a, b)
        if d:
            for axis, coord, b0, b1 in SEAMS:
                if (a[axis]-coord)*(b[axis]-coord) <= 0 and a[axis] != b[axis]:
                    f = (coord - a[axis]) / (b[axis] - a[axis])
                    if 0 <= f <= 1:
                        q = (a[0]+f*(b[0]-a[0]), a[1]+f*(b[1]-a[1]))
                        if not (b0 - 2 <= q[1-axis] <= b1 + 2):
                            continue        # crossed the LINE, not the seam segment
                        c = acc + f*d
                        ts = sorted(assign[si])
                        lo = max((t for t in ts if t <= c), default=None)
                        hi = min((t for t in ts if t >= c), default=None)
                        if lo is not None and hi is not None:
                            worst = max(worst, hi - lo)
        acc += d
check("max seam-adjacent gap <= 25 mm", worst <= 25.0, "worst %.1f mm" % worst)
chain = sorted(p["chain"] for p in PX)
check("chain is a permutation 0..136", chain == list(range(137)), "")
order = sorted(PX, key=lambda p: p["chain"])
longs = [k for k in range(len(order)-1)
         if math.dist((order[k]["x"], order[k]["y"]),
                      (order[k+1]["x"], order[k+1]["y"])) > 101.6]
check("extension jumpers at chain 86, 107", longs == [86, 107], str(longs))

# ---- B. screws ----
mach = [s for s in bb_scr if s[2] == 1]
wood = [s for s in bb_scr if s[2] == 0]
mch = min(path_dist((s[0], s[1])) for s in bb_scr)
check("all screws >= 14.5 mm from channel centerlines", mch >= 14.5,
      "min %.1f mm (%d machine + %d wood)" % (mch, len(mach), len(wood)))
mpx = min(math.dist((s[0], s[1]), q) for s in mach for q in allpx)
check("machine screws >= 16 mm from pixels", mpx >= 16.0, "min %.1f mm" % mpx)
paired = 0
for s in mach:
    for axis, coord, b0, b1 in SEAMS:
        if abs(abs(s[axis] - coord) - 8.0) < 0.6 and b0 <= s[1-axis] <= b1:
            mirror = [s[1-axis], 2*coord - s[axis]] if axis == 1 else \
                     [2*coord - s[axis], s[1-axis]]
            mb = (mirror[0], mirror[1]) if axis == 0 else (s[0], 2*coord - s[1])
            if any(abs(t[0]-mb[0]) < 0.6 and abs(t[1]-mb[1]) < 0.6 for t in mach):
                paired += 1
check("machine screws paired across seams (1 known single)",
      len(mach) - paired == 1, "%d of %d paired" % (paired, len(mach)))

# ---- C. straps (STL truth) ----
for i, name in enumerate(NAMES):
    tris = read_stl("stl/strap_s%d.stl" % (i+1))
    verts = vset(tris)
    bad = []
    for q in bk_pass[i]:
        r = ring_r(verts, q[0], q[1], -0.05, 2.05)
        if r is None or abs(r - 8.5) > 0.2:
            bad.append(("pass", q, r))
    for q in bk_nut[i]:
        r = ring_r(verts, q[0], q[1], -0.05, 0.85, 6)
        if r is None or abs(r - 2.25) > 0.2:
            bad.append(("bore", q, r))
        # hex pocket: wall vertices live only at the rims (floor z=0.8, top z=4);
        # probe the floor rim in the annulus between the Ø4.5 bore and the boss
        rh = ring_r(verts, q[0], q[1], 0.7, 0.9, 6, rmin=3.0)
        if rh is None or not 3.4 <= rh <= 4.3:      # hex flat 3.6 .. corner 4.16
            bad.append(("hex", q, rh))
    for q in bk_collar[i]:
        r = ring_r(verts, q[0], q[1], 0.9, 1.1, 8)  # lip at mid-height
        if r is None or abs(r - 5.72) > 0.15:
            bad.append(("collar-lip", q, r))
        # flange pocket walls have vertices only at the z=2/z=4 rims; probe the
        # bottom rim in the annulus outside the collar bore (~6.1)
        rp = ring_r(verts, q[0], q[1], 1.95, 2.05, 9, rmin=6.6)
        if rp is None or abs(rp - 7.25) > 0.2:
            bad.append(("flange-pocket", q, rp))
    for q in bk_socket[i]:
        r = ring_r(verts, q[0], q[1], 0.95, 2.0, 7)
        if r is None or abs(r - 5.1) > 0.2:
            bad.append(("socket", q, r))
    n = len(bk_pass[i]) + 2*len(bk_nut[i]) + 2*len(bk_collar[i]) + len(bk_socket[i])
    check("strap %s: %d features at printed positions" % (name, n),
          not bad, "; ".join("%s@%s r=%s" % b for b in bad) or "all verified")
# coverage: every pixel whose flange could touch a strap has a hole there
missing = []
for p in PX:
    q = (p["x"], p["y"])
    for i, name in enumerate(NAMES):
        axis, coord = STRAP_AX[name]
        u = q[0] if axis == 1 else q[1]
        v = (q[1] - coord) if axis == 1 else (q[0] - coord)
        u0, u1 = bk_span[i]
        if abs(v) <= bk_w/2 + 7.3 and u0 - 7.3 <= u <= u1 + 7.3:
            feats = [f for f in (bk_pass[i] + bk_collar[i])]
            if not any(abs(f[0]-u) < 0.5 and abs(f[1]+v) < 0.5 for f in feats):
                missing.append((name, q))
check("every strap-overlapped pixel has a pass-hole/collar", not missing,
      str(missing) or "coverage complete")
for i, name in enumerate(NAMES):
    L = bk_span[i][1] - bk_span[i][0]
    check("strap %s fits the bed" % name, L <= 316 and bk_w <= 295,
          "%.0f x %.0f" % (L, bk_w))

# ---- D. plates (STL truth) ----
BITEP = {tuple(b): [] for b in bb_bite}
for pi, (x0, x1, y0, y1) in enumerate(plates):
    for b in bb_bite:
        if x0 - 10 <= b[0] < x1 + 10 and y0 - 10 <= b[1] < y1 + 10:
            BITEP[tuple(b)].append(pi + 1)
for b, ps in BITEP.items():
    for pl in ps:
        for col in ("black", "white"):
            verts = vset(read_stl("stl/board%d_%s.stl" % (pl, col)))
            r = ring_r(verts, b[0], b[1], -0.05, 2.5, 8)
            check("B%d %s bite at (%.0f,%.0f) r=6.5" % (pl, col, b[0], b[1]),
                  r is not None and abs(r - 6.5) < 0.1,
                  "r=%s" % (("%.2f" % r) if r else None))
scr_missing = 0
for s in bb_scr:
    pl = next((k+1 for k, (x0, x1, y0, y1) in enumerate(plates)
               if x0 <= s[0] < x1 and y0 <= s[1] < y1), None)
    verts = vset(read_stl("stl/board%d_black.stl" % pl))
    r = ring_r(verts, s[0], s[1], -0.05, 2.05, 5)
    if r is None or abs(r - 2.25) > 0.15:
        scr_missing += 1
check("all %d face screw holes present in the plates" % len(bb_scr),
      scr_missing == 0, "%d missing" % scr_missing)
for k, (x0, x1, y0, y1) in enumerate(plates):
    check("plate B%d fits 316x295" % (k+1), x1-x0 <= 316 and y1-y0 <= 295,
          "%.0fx%.0f" % (x1-x0, y1-y0))

# ---- E. meshes ----
for p in ["stl/board%d_3color.3mf" % k for k in (1, 2, 3, 4)]:
    xml = zipfile.ZipFile(p).read("3D/3dmodel.model").decode()
    tb = 0
    for mesh in re.findall(r"<mesh>.*?</mesh>", xml, re.S):
        tris = [(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                for m in re.finditer(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', mesh)]
        tb += bad_edges(tris)
    check("%s manifold" % p, tb == 0, "%d bad edges" % tb)
for p in ["stl/strap_s%d.stl" % k for k in (1, 2, 3, 4)] + ["stl/pusher.stl"]:
    tb = stl_bad_edges(read_stl(p))
    check("%s manifold" % p, tb == 0, "%d bad edges" % tb)

n_fail = sum(1 for r in results if not r["ok"])
json.dump({"checks": results, "fail": n_fail},
          open("src/parts/board_qa.json", "w"), indent=1)
print("---\n%d checks, %d FAIL -> src/parts/board_qa.json" % (len(results), n_fail))
sys.exit(1 if n_fail else 0)
