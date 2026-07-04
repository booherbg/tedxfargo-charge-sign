#!/usr/bin/env python3
"""Compose bolt options A (in-band 7th element) and B (tall 2-plate board).
A: writes a merged data scad (bolt + CHARGE) ready for panelize.
B: computes board dims, seam crossings (-> introduced neon breaks), and stats.
Outputs a JSON for the preview page builder."""
import json, math, re

REPO = "/Users/blaine/workspace/2026-charge-tedxfargo"

def grab(txt, name, key):
    m = re.search(re.escape(name + "_" + key) + r"\s*=\s*(.*?);", txt, re.S)
    return json.loads(m.group(1))

wtxt = open(REPO + "/src/parts/word_data.scad").read()
btxt = open(REPO + "/src/parts/bolt5_data.scad").read()
wp = grab(wtxt, "WORD", "paths")
wpx = grab(wtxt, "WORD", "pixels")
bp = grab(btxt, "BOLT", "paths")
bbx = grab(btxt, "BOLT", "bbox")          # [132.1, 552.5] centerline bbox

def plen(p): return sum(math.dist(p[i], p[i+1]) for i in range(len(p)-1))

# ---------- OPTION A: in-band, scaled to letter height ----------
word_h = max(q[1] for p in wp for q in p)          # 251.2 (letters' centerline height)
s = word_h / bbx[1]
GAP = 40.0                                          # band-edge gap bolt -> C
bw = bbx[0] * s
shift = bw + 22 + GAP                               # bolt occupies x in [0, bw], word shifts right
a_bolt = [[[round(q[0]*s, 2), round(q[1]*s, 2)] for q in p] for p in bp]
a_word = [[[round(q[0]+shift, 2), round(q[1], 2)] for q in p] for p in wp]
a_paths = a_bolt + a_word
a_closed = [0]*len(a_paths)
with open(REPO + "/src/parts/aword_data.scad", "w") as f:
    f.write("// AUTO-GENERATED: option A = bolt (in-band) + CHARGE\n")
    f.write("AW_paths = %s;\n" % json.dumps(a_paths))
    f.write("AW_closed = %s;\n" % a_closed)
    f.write("AW_pixels = %s;\n" % json.dumps([[round(q[0]+shift,2), round(q[1],2)] for q in wpx]))
    f.write("AW_bbox = [%.2f, %.2f];\n" % (max(q[0] for p in a_paths for q in p), word_h))
a_len = sum(plen(p) for p in a_bolt)
print("A: bolt scaled x%.3f -> %.0fx%.0fmm centerline, %.0fmm tube, word shifted +%.1f"
      % (s, bw, word_h, a_len, shift))

# ---------- OPTION B: tall board, 2 plates, seam breaks ----------
BH = 570.0                                          # bolt art height (as extracted)
FACE_W = round(bbx[0] + 22 + 2*14, 0)               # board face width (band + margins)
FACE_H = round(BH + 2*11.5, 0)                      # + top/bottom screw bands
seam_y = bbx[1] / 2                                 # mid-height seam (centerline coords)
# find tube crossings of the seam: consecutive path points straddling seam_y
crossings = []
for si, p in enumerate(bp):
    for i in range(len(p)-1):
        y0, y1 = p[i][1], p[i+1][1]
        if (y0 - seam_y) * (y1 - seam_y) < 0:
            f_ = (seam_y - y0) / (y1 - y0)
            crossings.append([round(p[i][0] + f_*(p[i+1][0]-p[i][0]), 1), round(seam_y, 1), si])
print("B: board %dx%dmm, 2 plates of ~%dx%d; seam at y=%.0f crosses the tube %d time(s) -> %d neon breaks"
      % (FACE_W, FACE_H, FACE_W, FACE_H/2, seam_y, len(crossings), len(crossings)))
b_len = sum(plen(p) for p in bp)
grams_b = FACE_W * FACE_H * 0.00254 + b_len * 0.132
print("B: tube %.0fmm, ~%d px @17, ~%dg total across 2 plates" % (b_len, round(b_len/17)+len(bp), grams_b))

json.dump({"A": {"bolt": a_bolt, "shift": shift, "scale": s, "bolt_len": a_len},
           "B": {"bolt": bp, "face_w": FACE_W, "face_h": FACE_H, "seam_y": seam_y,
                 "crossings": crossings, "tube_len": b_len, "grams": round(grams_b)}},
          open(REPO + "/src/parts/bolt_options.json", "w"))
print("wrote src/parts/aword_data.scad + src/parts/bolt_options.json")
