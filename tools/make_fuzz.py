#!/usr/bin/env python3
"""Random height grid for the lens baked 'fuzzy skin' (OpenSCAD surface()).
Heights are ABSOLUTE mm; 1 grid unit = 1mm, and the .scad scales XY by CELL so the
same CELL sets the bump size. Rows = Y, cols = X.
Usage: make_fuzz.py OUT CELL HMAX [SEED [CELL2 HMAX2 [AREA_X AREA_Y]]] [--mode=M]
Optional second octave: smooth coarse waves (CELL2, HMAX2) bilinearly added under
the fine bumps -> two-scale texture (frost over orange peel).
Optional AREA_X/AREA_Y (mm): grid coverage — default 102x30 (testbox lens); pass
the part's bbox + margin for bigger parts (bolt, letters).
--mode=random (default) | pyramid | pyramid-jitter
  pyramid: UNIFORM square-pyramid facet grid (deterministic prismatic texture),
  sampled at CELL/4 so the .scad scale must be CELL/4 for these dats.
  pyramid-jitter: same lattice, per-cell random peak height (0.6-1.0x) and peak
  offset (+-0.25 cell) — uniform facet density, scattered orientations."""
import random, sys

MODE = "random"
for a in list(sys.argv[1:]):
    if a.startswith("--mode="):
        MODE = a.split("=", 1)[1]
        sys.argv.remove(a)
out  = sys.argv[1]
cell = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0   # bump size (mm) -> also the .scad scale
hmax = float(sys.argv[3]) if len(sys.argv) > 3 else 0.55  # peak bump height (mm)
seed = int(sys.argv[4])   if len(sys.argv) > 4 else 7
cell2 = float(sys.argv[5]) if len(sys.argv) > 5 else 0    # coarse-octave wave size (mm), 0 = off
hmax2 = float(sys.argv[6]) if len(sys.argv) > 6 else 0    # coarse-octave peak height (mm)
AREA_X = float(sys.argv[7]) if len(sys.argv) > 7 else 102  # mm to cover (default: testbox lens ~90x22 + margin)
AREA_Y = float(sys.argv[8]) if len(sys.argv) > 8 else 30
NX = int(AREA_X / cell) + 2
NY = int(AREA_Y / cell) + 2
random.seed(seed)
# floor at 0.02: cells that hit exactly 0.000 make the heightfield touch its own
# base plane -> non-manifold pinch edges in the CGAL union (Bambu flags them)
if MODE in ("pyramid", "pyramid-jitter"):
    S = 3                                     # samples per cell edge (0.67mm at cell
                                              # 2.0 -- the 0.4 nozzle is the real
                                              # resolution limit; S=4 was 2x the mesh
                                              # for no printable difference)
    NX, NY = int(AREA_X / cell * S) + 2, int(AREA_Y / cell * S) + 2
    ncx, ncy = NX // S + 2, NY // S + 2
    peaks = [[(hmax, 0.0, 0.0) for _ in range(ncx)] for _ in range(ncy)]
    if MODE == "pyramid-jitter":
        peaks = [[(hmax * random.uniform(0.6, 1.0),
                   random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25))
                  for _ in range(ncx)] for _ in range(ncy)]
    # Float the whole faceted field 0.02mm PROUD of the lens plane: the .scad
    # places the surface base at top-0.1504, so values below 0.1504 dip under
    # the lens top and every ramp crossing that plane leaves a tangency line ->
    # non-manifold edges (dead-band snaps samples, not the interpolated ramps).
    # Min value 0.1704 keeps every triangle strictly above the plane; peaks
    # still reach ~hmax above the lens top.
    F0 = 0.1704
    grid = []
    for j in range(NY):
        row = []
        for i in range(NX):
            cx, cy = i // S, j // S
            h0, ox, oy = peaks[cy][cx]
            fx = (i % S) / S - 0.5 - ox       # position within cell, peak-relative
            fy = (j % S) / S - 0.5 - oy
            t = max(abs(fx), abs(fy)) * 2.0   # 0 at peak -> 1 at cell edge
            frac = (h0 / hmax) * max(0.0, 1.0 - t)
            row.append(F0 + frac * (hmax - 0.02))
        grid.append(row)
else:
    grid = [[max(0.02, random.uniform(0.0, hmax)) for _ in range(NX)] for _ in range(NY)]
if cell2 and hmax2:
    NX2 = int(AREA_X / cell2) + 2
    NY2 = int(AREA_Y / cell2) + 2
    coarse = [[random.uniform(0.0, hmax2) for _ in range(NX2)] for _ in range(NY2)]
    for j in range(NY):                                    # bilinear-sample coarse at each fine point
        for i in range(NX):
            u = min(i * cell / cell2, NX2 - 1.001)
            v = min(j * cell / cell2, NY2 - 1.001)
            iu, iv, fu, fv = int(u), int(v), u - int(u), v - int(v)
            grid[j][i] += (coarse[iv][iu]   * (1-fu)*(1-fv) + coarse[iv][iu+1]   * fu*(1-fv)
                         + coarse[iv+1][iu] * (1-fu)*fv     + coarse[iv+1][iu+1] * fu*fv)
with open(out, "w") as f:
    for row in grid:
        f.write(" ".join("%.3f" % h for h in row) + "\n")
octave = " + octave cell %.2fmm h %.2fmm" % (cell2, hmax2) if cell2 and hmax2 else ""
print("wrote %s  (%dx%d grid, cell %.2fmm, heights 0..%.2fmm, seed %d%s)" % (out, NX, NY, cell, hmax, seed, octave))
