#!/usr/bin/env python3
"""Generate a random height grid for the lens baked 'fuzzy skin' (OpenSCAD surface()).
Rows = Y, columns = X, values = bump height (mm). 1 grid unit = 1mm.
Usage: make_fuzz.py [out.dat] [seed]"""
import random, sys
out  = sys.argv[1] if len(sys.argv) > 1 else "src/parts/fuzz.dat"
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
NX, NY, HMAX = 93, 25, 0.55        # covers the ~90x22mm lens at 1mm resolution
random.seed(seed)
with open(out, "w") as f:
    for _ in range(NY):
        f.write(" ".join("%.3f" % random.uniform(0.0, HMAX) for _ in range(NX)) + "\n")
print("wrote %s  (%dx%d grid, heights 0..%.2fmm, seed %d)" % (out, NX, NY, HMAX, seed))
