#!/usr/bin/env python3
"""Random height grid for the lens baked 'fuzzy skin' (OpenSCAD surface()).
Heights are ABSOLUTE mm; 1 grid unit = 1mm, and the .scad scales XY by CELL so the
same CELL sets the bump size. Rows = Y, cols = X.
Usage: make_fuzz.py OUT CELL HMAX [SEED]"""
import random, sys
out  = sys.argv[1]
cell = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0   # bump size (mm) -> also the .scad scale
hmax = float(sys.argv[3]) if len(sys.argv) > 3 else 0.55  # peak bump height (mm)
seed = int(sys.argv[4])   if len(sys.argv) > 4 else 7
AREA_X, AREA_Y = 102, 30                                   # mm to cover (lens ~90x22 + margin)
NX = int(AREA_X / cell) + 2
NY = int(AREA_Y / cell) + 2
random.seed(seed)
with open(out, "w") as f:
    for _ in range(NY):
        f.write(" ".join("%.3f" % random.uniform(0.0, hmax) for _ in range(NX)) + "\n")
print("wrote %s  (%dx%d grid, cell %.2fmm, heights 0..%.2fmm, seed %d)" % (out, NX, NY, cell, hmax, seed))
