#!/usr/bin/env python3
"""Build word_cuts_repairs.json: extraction defects repaired to match the font.

The published logo art is LIVE TEXT in "NeonSans" (decoded from the PSD text
engine); the AI lockup is that text outlined, so the VECTOR IS THE FONT — it
is the authority for what tubes exist. Vs it, production had two amputations
(both from the 2026-07-03 extractor junction surgery):
  1. The hat's LEFT ARM — in CHARGE.svg ink (edges (97.73,2.31)->(94.08,8.16)
     / (92.83,7.38)->(96.70,1.19) pt) but dropped as a spur: tube5's walk
     starts at (661.96,245.38), exactly the amputation. Restored by PREPENDING
     the arm to tube5 (the chevron corner is continuous — one bent tube).
  2. The TRIANGLE'S LEFT SIDE — tube4 was extracted as an open arc (right side
     + bottom + stub). Its endpoints already sit on the left-side line, so the
     closing chord end->start IS the missing side (78mm). Loop closed + 3 px.

(A third "floating mid dash" was added on 2026-07-06 and REMOVED the same day:
it was a glow-core highlight in the PSD renders misread as a tube. It is not
in the vector, therefore not in the font. Lesson: the vector outruns any
reading of the raster mockups.)

pt->mm similarity (calibrated on roof/bottom/hat/leg lines, <0.3mm residual):
  X = 6.9127*x_pt - 13.22 ; Y = 256.51 - 6.9127*y_pt

Pixels: hat-bar chain re-spaced over arm+bar (3 removed, 5 added), triangle
left side +3 @19.4mm. Net +5. All spacings audited (>=17 arc, >=14.8 chord).

Round 2 (2026-07-06, user-approved; C deferred — its piece is already printing):
  3. G (tube 1): BOTH ends truncated — top-arc end 29.1mm short of the vector
     cut center (1128.9,212.5), inner-bar end 10.8mm short of (1118.8,151.1).
     Extended to the cut centers; end chains locally re-spaced by uniform
     chord (+1 px at the top end, net 0 at the bar end).
  4. R (tube 8, the leg): the extracted polyline runs 183mm of arc over 142mm
     of chord (real curve + raster-skeleton zigzag), so arc-spaced pixels
     landed at 14.2mm true chords — the three flange_trims "snug pairs".
     Re-spaced by UNIFORM CHORD (12 -> 11 px, ~16.8mm chords, arcs still
     >=17); flange_trims cleared, no snipping needed.

Usage: make_repairs.py [in=src/parts/word_cuts.json] [out=src/parts/word_cuts_repairs.json]
"""
import json, math, sys

IN  = sys.argv[1] if len(sys.argv) > 1 else "src/parts/word_cuts.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "src/parts/word_cuts_repairs.json"

d = json.load(open(IN))
paths, pixels = d["paths"], d["pixels"]

# ---- geometry (word mm, from the calibrated pt->mm map) -------------------
ARM_END    = (632.80, 202.80)   # arm cut end (pt (93.455,7.77))
ARM_CORNER = (659.50, 245.62)   # chevron corner (arm meets hat bar, pt (97.32,1.575))

# ---- 1. prepend arm to tube5 (the A body walk starts at the hat bar) ------
# t5[0] = (658.09,244.42): the extractor's rounded stub of the amputated corner.
# Replace it with the true chevron corner and hang the arm off it.
t5 = paths[5]
assert math.dist(t5[0], (658.09, 244.42)) < 1.0, "tube5 no longer starts at the hat bar"
paths[5] = [list(ARM_END), list(ARM_CORNER)] + t5[1:]

def lerp(a, b, t):
    return (a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t)

# ---- 1b. close the triangle (defect fix, not an alt-A styling choice) -----
# tube4 was extracted as an OPEN arc: right side + bottom + a stub; the left
# side fell to the same junction surgery that ate the hat arm. Its endpoints
# already sit ON the left-side line a few mm past the corners, so the closing
# chord end->start IS the missing left side (77.6mm).
t4 = paths[4]
assert math.dist(t4[0], (646.65, 171.57)) < 1.0 and math.dist(t4[-1], (602.40, 107.84)) < 1.0, \
    "tube4 is no longer the expected open triangle arc"
paths[4] = t4 + [list(t4[0])]
tri_px = [lerp(t4[-1], t4[0], f) for f in (0.25, 0.5, 0.75)]   # 19.4mm pitch on the left side
d["alt"] = "repairs v3: A arm + closed triangle; G ends extended; R leg chord-respaced"

# ---- shared pixel machinery -------------------------------------------------
def densify(poly, step=0.25):
    out = [tuple(poly[0])]
    for a, b in zip(poly, poly[1:]):
        L = math.dist(a, b)
        for i in range(1, max(1, int(L/step)) + 1):
            out.append((a[0] + (b[0]-a[0])*i/max(1, int(L/step)),
                        a[1] + (b[1]-a[1])*i/max(1, int(L/step))))
    return out

def chord_chain(poly, n):
    """n+1 points along poly, equal consecutive straight-line chords, ends pinned."""
    P = densify(poly)
    end = P[-1]
    def walk(t):
        placed, last = [P[0]], P[0]
        for q in P[1:]:
            if math.dist(q, last) >= t:
                placed.append(q); last = q
        return placed
    lo, hi = 5.0, 200.0
    for _ in range(80):
        t = (lo + hi) / 2
        pl = walk(t)
        g = (len(pl) - 1) + math.dist(pl[-1], end) / t
        if g > n: lo = t
        else: hi = t
    return walk(lo)[:n] + [end]

def d_poly(p, poly):
    best = 9e9
    for i in range(len(poly)-1):
        a, b = poly[i], poly[i+1]
        L2 = (b[0]-a[0])**2 + (b[1]-a[1])**2
        t = max(0, min(1, ((p[0]-a[0])*(b[0]-a[0]) + (p[1]-a[1])*(b[1]-a[1])) / L2)) if L2 else 0
        best = min(best, math.hypot(p[0]-a[0]-t*(b[0]-a[0]), p[1]-a[1]-t*(b[1]-a[1])))
    return best

def s_along(p, poly):
    best, bs, acc = 9e9, 0.0, 0.0
    for i in range(len(poly)-1):
        a, b = poly[i], poly[i+1]
        L = math.dist(a, b)
        t = max(0, min(1, ((p[0]-a[0])*(b[0]-a[0]) + (p[1]-a[1])*(b[1]-a[1])) / (L*L))) if L else 0
        dd = math.hypot(p[0]-a[0]-t*(b[0]-a[0]), p[1]-a[1]-t*(b[1]-a[1]))
        if dd < best: best, bs = dd, acc + t*L
        acc += L
    return bs

def sub_to(dense, target):
    """prefix of a densified polyline up to the sample nearest target"""
    i = min(range(len(dense)), key=lambda k: math.dist(dense[k], target))
    return dense[:i+1]

# ---- 2. G (tube 1): extend both truncated ends to the vector cut centers ---
G_TOP_CUT = (1128.9, 212.5)     # vector end-cut centers (kern +7.1 applied)
G_BAR_CUT = (1118.8, 151.1)
t1 = paths[1]
assert math.dist(t1[0], (1151.7, 230.7)) < 1.0 and math.dist(t1[-1], (1114.1, 141.3)) < 1.0, \
    "tube1 (G) ends are not where expected"
on1 = sorted((p for p in pixels if d_poly(p, t1) < 0.6), key=lambda p: s_along(p, t1))
assert math.dist(on1[0], t1[0]) < 1.5 and math.dist(on1[-1], t1[-1]) < 1.5, \
    "G end pixels not found at tube ends"
paths[1] = [list(G_TOP_CUT)] + t1 + [list(G_BAR_CUT)]
dense1 = densify(paths[1])
# top end: [new cut ... old end(px removed) ... pxA2]: 2 intervals ~23mm (+1 px)
g_top = chord_chain(sub_to(dense1, on1[1]), 2)[:-1]          # cut + mid (pxA2 kept)
# bar end: [pxB3 ... (2 px removed) ... new cut]: 2 intervals ~22.4mm (net 0)
g_bar = chord_chain(sub_to(dense1[::-1], on1[-3]), 2)[:-1]   # cut + mid (pxB3 kept)
g_remove = [on1[0], on1[-1], on1[-2]]
g_add = g_top + g_bar

# ---- 3. R (tube 8, the leg): uniform-chord respace between the end pixels --
t8 = paths[8]
on8 = sorted((p for p in pixels if d_poly(p, t8) < 0.6), key=lambda p: s_along(p, t8))
assert len(on8) == 12, f"expected 12 px on the R leg, found {len(on8)}"
dense8 = densify(t8)
i0 = min(range(len(dense8)), key=lambda k: math.dist(dense8[k], on8[0]))
i1 = min(range(len(dense8)), key=lambda k: math.dist(dense8[k], on8[-1]))
seg8 = dense8[min(i0, i1):max(i0, i1)+1]
r_add = None
for n in (11, 10):                                   # most pixels that satisfies both rules
    cand = chord_chain(seg8, n)
    chords = [math.dist(a, b) for a, b in zip(cand, cand[1:])]
    arcs = [abs(s_along(b, t8) - s_along(a, t8)) for a, b in zip(cand, cand[1:])]
    if min(chords) >= 15.2 and min(arcs) >= 17:
        r_add = cand
        break
assert r_add, "no legal R respace found"
r_remove = list(on8)
d["flange_trims"] = []                               # snug pairs eliminated

# ---- 4. pixel merge ---------------------------------------------------------
# A: re-space the arm+bar chain, pinned at arm end and the px at (708.91,245.51)
REMOVE = [(658.09, 244.42), (674.94, 245.51), (691.92, 245.51)] + g_remove + r_remove
kept = [px for px in pixels if not any(math.dist(px, r) < 0.5 for r in REMOVE)]
assert len(pixels) - len(kept) == 18, "expected to remove exactly 3+3+12 pixels"

arm_len = math.dist(ARM_END, ARM_CORNER)                 # 50.4
bar_len = math.dist(ARM_CORNER, (708.91, 245.51))        # 49.4
chain, total = [], arm_len + bar_len
N = 5                                                    # 5 intervals -> 19.96mm
for i in range(N):                                       # skip t=total (existing px)
    t = total * i / N
    if t <= arm_len:
        chain.append(lerp(ARM_END, ARM_CORNER, t/arm_len))
    else:
        chain.append(lerp(ARM_CORNER, (708.91, 245.51), (t-arm_len)/bar_len))
a_add = chain + tri_px
added = a_add + g_add + r_add
d["pixels"] = kept + [[round(x, 2), round(y, 2)] for x, y in added]

# ---- 5. audits --------------------------------------------------------------
# (a) pixel spacing: every added px vs every other px: chord >= 14.8
allpx = d["pixels"]
worst = 99
for a in added:
    for b in allpx:
        dd = math.dist(a, b)
        if 0.01 < dd < worst:
            worst = dd
assert worst >= 14.8, f"pixel chord violation: {worst:.2f}mm"
# (b) arc pitch >= 17 on the A chains (G/R intervals already >= their chords/checked)
arcs = [total/N]*N + [math.dist(t4[-1], t4[0]) / 4]
assert min(arcs) >= 17, "arc pitch violation"
# (c) containment: additions stay well inside their piece
for q, x0, x1 in ([(q, 468, 764) for q in [ARM_END, ARM_CORNER] + a_add] +
                  [(q, 1040, 1340) for q in [G_TOP_CUT, G_BAR_CUT] + g_add] +
                  [(q, 764, 1056) for q in r_add]):
    assert x0 + 15 < q[0] < x1 - 15, f"outside piece interior: {q}"

d["pieces"][2]["pixels"] += len(a_add) - 3
d["pieces"][3]["pixels"] += len(r_add) - 12
d["pieces"][4]["pixels"] += len(g_add) - 3
json.dump(d, open(OUT, "w"))
word_px = len(d["pixels"])
r_ch = [math.dist(a, b) for a, b in zip(r_add, r_add[1:])]
print(f"A: arm+triangle (+{len(a_add)-3} px) | G: ends extended 29.1/10.8mm "
      f"(+{len(g_add)-3} px) | R: leg respaced {len(r_remove)}->{len(r_add)} px, "
      f"chords {min(r_ch):.1f}-{max(r_ch):.1f}mm, snug pairs eliminated")
print(f"wrote {OUT}: {word_px} word px (was {len(pixels)}, net {word_px - len(pixels):+d})")
print(f"sign total: {word_px} + 137 bolt = {word_px + 137} / 600 purchased")
