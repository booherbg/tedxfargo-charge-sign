#!/usr/bin/env python3
"""Bridge the word's art-break openings: within each letter, greedily join
path-end pairs (< MAX_GAP mm) with straight tube runs until none remain.
Letters become continuous/closed neon outlines ("smooth all around" request,
2026-07-05). Rewrites word_cuts.json paths in place; cuts/pieces/pixels/screws
untouched (bridges only ADD channel; nothing moves).

Usage: bridge_word.py [--dry] [src/parts/word_cuts.json]
"""
import json, math, sys

MAX_GAP = 115.0

def cut_at(c, y):
    return c[min(range(len(c)), key=lambda i: abs(c[i][1] - y))][0]

def main():
    dry = "--dry" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src = args[0] if args else "src/parts/word_cuts.json"
    d = json.load(open(src))
    paths, cuts, pieces = d["paths"], d["cuts"], d["pieces"]

    def side(pt, i):
        return ((i == 0 or pt[0] > cut_at(cuts[i - 1], pt[1])) and
                (i == len(pieces) - 1 or pt[0] <= cut_at(cuts[i], pt[1])))

    def centroid(p):
        return (sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p))

    letter_of = [next(i for i in range(len(pieces)) if side(centroid(p), i))
                 for p in paths]
    pool = {si: list(map(list, p)) for si, p in enumerate(paths)}
    closed = set()
    n_bridges = 0
    bridges = []          # bridges >= ~30mm get pixels AFTER all bridging,
                          # placed against the full pixel set (existing pixels
                          # are NOT reliably at stroke ends, and some bridges
                          # run beside strokes that already carry pixels)
    def bridge_pixels(a, b):
        if math.dist(a, b) >= 30:
            bridges.append((list(a), list(b)))
    while True:
        best = None
        for a in pool:
            for b in pool:
                if b < a or a in closed or b in closed:
                    continue
                if letter_of[a] != letter_of[b]:
                    continue
                for ea in (0, 1):
                    for eb in (0, 1):
                        if a == b and ea == eb:
                            continue
                        pa = pool[a][0 if ea == 0 else -1]
                        pb = pool[b][0 if eb == 0 else -1]
                        dd = math.dist(pa, pb)
                        if dd < MAX_GAP and (best is None or dd < best[0]):
                            best = (dd, a, b, ea, eb)
        if best is None:
            break
        dd, a, b, ea, eb = best
        if a == b:
            bridge_pixels(pool[a][-1], pool[a][0])
            pool[a].append(list(pool[a][0]))       # close the loop
            closed.add(a)
            print("  close  seg %d loop  (gap %.1f mm)" % (a, dd))
        else:
            A, B = pool[a], pool[b]
            if ea == 0:
                A = A[::-1]                        # bridge from A's end
            if eb == 1:
                B = B[::-1]                        # into B's start
            bridge_pixels(A[-1], B[0])
            pool[a] = A + B
            del pool[b]
            print("  bridge seg %d + seg %d      (gap %.1f mm)" % (a, b, dd))
        n_bridges += 1

    new_paths = [[[round(v, 2) for v in q] for q in p] for p in pool.values()]

    # place bridge pixels: candidates every ~17mm, keep only those that can sit
    # >=14.5 from every other pixel (try sliding along the bridge first)
    new_px = []
    all_px = [q[:2] for q in d["pixels"]]
    for a, b in bridges:
        L = math.dist(a, b)
        n = max(1, round(L / 17.0) - 1)
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        for k in range(1, n + 1):
            t0 = L * k / (n + 1)
            placed = None
            for dt in (0, 3, -3, 6, -6, 9, -9):
                t = t0 + dt
                if not (12 <= t <= L - 12):
                    continue
                cand = [a[0] + ux * t, a[1] + uy * t]
                if all(math.dist(cand, q) >= 14.5 for q in all_px):
                    placed = cand
                    break
            if placed:
                placed = [round(v, 2) for v in placed]
                new_px.append(placed)
                all_px.append(placed)
    print("%d bridges/closures; %d paths -> %d; +%d bridge pixels"
          % (n_bridges, len(paths), len(new_paths), len(new_px)))
    if dry:
        json.dump(new_paths, open("bridged_paths_dry.json", "w"))
        print("dry run: wrote bridged_paths_dry.json only")
        return
    d["paths"] = new_paths
    d["pixels"] = d["pixels"] + new_px
    for i, pc in enumerate(pieces):
        added = sum(1 for px in new_px if side(px, i))
        if added:
            pc["pixels"] += added
            print("  piece %d (%s): +%d px -> %d" % (i + 1, pc["letter"],
                                                     added, pc["pixels"]))
    json.dump(d, open(src, "w"))
    print("rewrote", src)

if __name__ == "__main__":
    main()
