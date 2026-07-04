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
            pool[a].append(list(pool[a][0]))       # close the loop
            closed.add(a)
            print("  close  seg %d loop  (gap %.1f mm)" % (a, dd))
        else:
            A, B = pool[a], pool[b]
            if ea == 0:
                A = A[::-1]                        # bridge from A's end
            if eb == 1:
                B = B[::-1]                        # into B's start
            pool[a] = A + B
            del pool[b]
            print("  bridge seg %d + seg %d      (gap %.1f mm)" % (a, b, dd))
        n_bridges += 1

    new_paths = [[[round(v, 2) for v in q] for q in p] for p in pool.values()]
    print("%d bridges/closures; %d paths -> %d" % (n_bridges, len(paths), len(new_paths)))
    if dry:
        json.dump(new_paths, open("bridged_paths_dry.json", "w"))
        print("dry run: wrote bridged_paths_dry.json only")
        return
    d["paths"] = new_paths
    json.dump(d, open(src, "w"))
    print("rewrote", src)

if __name__ == "__main__":
    main()
