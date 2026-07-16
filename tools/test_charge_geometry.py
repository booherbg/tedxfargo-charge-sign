#!/usr/bin/env python3
"""Host checks for the baked CHARGE geometry: internal consistency + agreement
with the flashed 12mm word ledmap. Run: python3 tools/test_charge_geometry.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charge_geometry as cg

def _load_word():
    cuts = ("src/parts/word_cuts_repairs.json"
            if os.path.exists("src/parts/word_cuts_repairs.json")
            else "src/parts/word_cuts.json")
    W = json.load(open(cuts))
    wx0, wy0, wx1, wy1 = W["face"]
    px = json.load(open("src/parts/word_pixmap.json"))["pixels"]
    return px, (wx1 - wx0), W["face_h"], wx0, wy0

def main():
    px, w_mm, h_mm, ox, oy = _load_word()
    geo = cg.compute(px, w_mm, h_mm, ox, oy, 12.0)
    ok = True
    def chk(cond, label):
        nonlocal ok; ok &= bool(cond)
        print(("PASS " if cond else "FAIL ") + label)

    chk(geo["num_pixels"] == 459, "459 pixels")
    chk(geo["letter_start"] == [0, 62, 143, 215, 296, 379], "letter starts C,H,A,R,G,E")
    chk(sum(geo["letter_count"]) == 459, "letter counts sum to 459")
    # contiguous coverage of 0..458
    covered = []
    for L in range(6):
        s = geo["letter_start"][L]; c = geo["letter_count"][L]
        covered += list(range(s, s + c))
    chk(sorted(covered) == list(range(459)), "letters cover 0..458 contiguously")
    chk(all(0 <= v < geo["grid_w"] for v in geo["col"]), "col within grid width")
    chk(all(0 <= v < geo["grid_h"] for v in geo["row"]), "row within grid height")
    chk(all(0 <= v <= 255 for v in geo["height"] + geo["xnorm"]), "height/xnorm in 0..255")

    # agreement with the flashed ledmap: ledmap.map[row*W + col] must equal the physical index
    lm = json.load(open("wled/word-controller/ledmap.json"))
    chk((geo["grid_w"], geo["grid_h"]) == (lm["width"], lm["height"]), "grid matches ledmap dims")
    W = lm["width"]; bad = 0
    for i in range(geo["num_pixels"]):
        if lm["map"][geo["row"][i] * W + geo["col"][i]] != i:
            bad += 1
    chk(bad == 0, "every pixel's (col,row) round-trips through the ledmap (%d mismatches)" % bad)

    print("\n" + ("ALL PASS" if ok else "FAILURES"))
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
