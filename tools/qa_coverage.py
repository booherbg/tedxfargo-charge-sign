#!/usr/bin/env python3
"""Coverage QA: does the production tube layout actually cover the vector art?

Rasterizes CHARGE.svg ink (per-letter kern-corrected to match the panelized
layout) and the cuts-json tube bands at INK width (11.8mm), then reports every
ink region the bands miss. This is the check that would have caught the A's
open triangle and amputated hat arm (extractor junction surgery, 2026-07-03)
before anything rendered: the extractor validates its own graph, not the art.

Usage: qa_coverage.py [src/parts/word_cuts.json] [--max-mm2 100]
Exit 1 if any uncovered cluster exceeds --max-mm2 (default 100 mm²).
Known accepted findings should be fixed or the threshold consciously raised —
don't let a red row become wallpaper.

Calibration: pt->mm X = 6.9127x - 13.22, Y = 256.51 - 6.9127y (fit on the A's
roof/bottom/hat lines, <0.3mm residual). Kern shifts from word_cuts.json.
Sub-60mm² clusters are mostly raster/end-cap artifacts; real defects to date
have been full-tube-width (>250 mm²).
"""
import json, math, re, sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
SRC = args[0] if args else "src/parts/word_cuts.json"
MAX = 100.0
for a in sys.argv[1:]:
    if a.startswith("--max-mm2"):
        MAX = float(a.split("=", 1)[1] if "=" in a else sys.argv[sys.argv.index(a) + 1])

wc = json.load(open(SRC))
kerns = wc.get("kern_nudges_mm", [])

def flatten(d):
    toks = re.findall(r"([MLCZ])\s*((?:-?[\d.]+[\s,]*)*)", d)
    subs, cur, pos, start = [], [], None, None
    for c, nums in toks:
        p = [float(x) for x in re.findall(r"-?[\d.]+", nums)]
        if c == "M":
            if cur: subs.append(cur)
            pos = (p[0], p[1]); start = pos; cur = [pos]
        elif c == "L":
            pos = (p[-2], p[-1]); cur.append(pos)
        elif c == "C":
            for i in range(0, len(p), 6):
                c1 = (p[i], p[i+1]); c2 = (p[i+2], p[i+3]); e = (p[i+4], p[i+5])
                for t in (0.2, 0.4, 0.6, 0.8, 1.0):
                    mt = 1 - t
                    cur.append((mt**3*pos[0] + 3*mt*mt*t*c1[0] + 3*mt*t*t*c2[0] + t**3*e[0],
                                mt**3*pos[1] + 3*mt*mt*t*c1[1] + 3*mt*t*t*c2[1] + t**3*e[1]))
                pos = e
        elif c == "Z" and start:
            cur.append(start)
    if cur: subs.append(cur)
    return subs

# letter x-split in pt (C|H|A|R|G|E) and cumulative kern shift per letter
PT_SPLIT = [34.0, 71.0, 112.5, 151.0, 191.5]
def kshift(ptx):
    li = sum(1 for s in PT_SPLIT if ptx >= s)          # 0..5
    seam = {3: [2], 4: [2, 3], 5: [2, 3]}              # R:+A|R  G,E:+A|R+R|G
    return sum(kerns[i] for i in seam.get(li, [])) if kerns else 0.0
def to_mm(q, dx):
    return (6.9127*q[0] - 13.22 + dx, 256.51 - 6.9127*q[1])

X0, Y0, X1, Y1 = -20, -25, 1590, 280
W, H = X1 - X0, Y1 - Y0
ink, band = bytearray(W*H), bytearray(W*H)

body = open("assets/svg/CHARGE.svg").read().split("</defs>")[1]
for d in re.findall(r' d="(M[^"]+)"', body):
    subs = flatten(d)
    if max(len(s) for s in subs) < 3:
        continue
    mid = sum(q[0] for s in subs for q in s) / sum(len(s) for s in subs)
    subs_mm = [[to_mm(q, kshift(mid)) for q in s] for s in subs]
    ys = [q[1] for s in subs_mm for q in s]
    for py in range(int(min(ys)-1), int(max(ys)+2)):
        y = py + 0.5; xs = []
        for s in subs_mm:
            for a, b in zip(s, s[1:]):
                if (a[1] <= y < b[1]) or (b[1] <= y < a[1]):
                    xs.append(a[0] + (y-a[1])/(b[1]-a[1])*(b[0]-a[0]))
        xs.sort()
        for i in range(0, len(xs)-1, 2):
            for px in range(int(xs[i]+0.5), int(xs[i+1]+0.5)):
                gx, gy = px - X0, py - Y0
                if 0 <= gx < W and 0 <= gy < H: ink[gy*W+gx] = 1

R2 = 5.9**2
for p in wc["paths"]:
    for a, b in zip(p, p[1:]):
        n = max(2, int(math.dist(a, b)))
        for t in range(n+1):
            x = a[0] + (b[0]-a[0])*t/n; y = a[1] + (b[1]-a[1])*t/n
            for dy in range(-6, 7):
                for dx in range(-6, 7):
                    if dx*dx + dy*dy <= R2:
                        gx, gy = int(x)+dx-X0, int(y)+dy-Y0
                        if 0 <= gx < W and 0 <= gy < H: band[gy*W+gx] = 1

missset = {i for i in range(W*H) if ink[i] and not band[i]}
clusters = []
while missset:
    stack = [missset.pop()]; cl = [stack[0]]
    while stack:
        i = stack.pop()
        for j in (i-1, i+1, i-W, i+W):
            if j in missset:
                missset.remove(j); stack.append(j); cl.append(j)
    clusters.append(cl)
clusters.sort(key=len, reverse=True)

LETTERS = [("C", -20, 224), ("H", 224, 468), ("A", 468, 764),
           ("R", 764, 1056), ("G", 1056, 1315), ("E", 1315, 1590)]
bad = 0
for cl in clusters:
    if len(cl) < 60:
        continue
    xs = [i % W + X0 for i in cl]; ys = [i // W + Y0 for i in cl]
    cx = sum(xs) / len(xs)
    L = next(nm for nm, a, b in LETTERS if a <= cx < b)
    flag = "FAIL" if len(cl) > MAX else "note"
    bad += flag == "FAIL"
    print("%s  %5d mm²  %s  x[%d,%d] y[%d,%d]" % (flag, len(cl), L, min(xs), max(xs), min(ys), max(ys)))
print("coverage QA (%s): %d cluster(s) over %.0f mm²" % (SRC, bad, MAX))
sys.exit(1 if bad else 0)
