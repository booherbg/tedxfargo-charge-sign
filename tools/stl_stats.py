#!/usr/bin/env python3
"""Volume/weight report for ASCII STLs (signed tetrahedron sum).
Usage: stl_stats.py file.stl [file2.stl ...] [--density 1.27]
PETG ~1.27 g/cm3, PLA ~1.24 g/cm3. Prints per-file cm3 / grams / bbox."""
import sys

density = 1.27
args = []
it = iter(sys.argv[1:])
for a in it:
    if a == "--density":
        density = float(next(it))
    else:
        args.append(a)

for path in args:
    vol6 = 0.0
    lo = [1e18] * 3
    hi = [-1e18] * 3
    tri = []
    with open(path) as f:
        for line in f:
            s = line.split()
            if len(s) == 4 and s[0] == "vertex":
                v = (float(s[1]), float(s[2]), float(s[3]))
                for i in range(3):
                    lo[i] = min(lo[i], v[i]); hi[i] = max(hi[i], v[i])
                tri.append(v)
                if len(tri) == 3:
                    a, b, c = tri
                    vol6 += (a[0]*(b[1]*c[2]-b[2]*c[1])
                           - a[1]*(b[0]*c[2]-b[2]*c[0])
                           + a[2]*(b[0]*c[1]-b[1]*c[0]))
                    tri = []
    cm3 = abs(vol6) / 6.0 / 1000.0
    print("%-28s %8.1f cm3  %7.1f g  bbox %.0fx%.0fx%.0f mm"
          % (path.split("/")[-1], cm3, cm3 * density,
             hi[0]-lo[0], hi[1]-lo[1], hi[2]-lo[2]))
