#!/usr/bin/env python3
"""Channel-clearance audit for 22mm neon bands (usable as library or CLI).
Rule (locked spec §9): two channels need >=26mm centerline gap UNLESS they meet
at a crisp crossing/approach (local tangents > CRISP_DEG apart). Long parallel
sub-26 runs are the rejected "mush"; crisp point features (letter-A pockets,
weave crossings, wedge tips) are accepted.

audit(paths_a, paths_b=None, min_gap=26, crisp_deg=35, run_mm=14) ->
list of violations [{'d','ax','ay','angle','run','a','b'}] where each is a
sub-min_gap CONTACT RUN with tangent angle < crisp_deg persisting > run_mm.
Also returns near-misses via report=True for eyeballing.
Self-audit (paths_b=None) skips pairs closer than 40mm along the same path.
"""
import math

def _resample(p, step=2.0):
    out = [(p[0][0], p[0][1], 0.0)]
    acc = 0.0
    for i in range(len(p) - 1):
        ax, ay = p[i]; bx, by = p[i + 1]
        d = math.dist((ax, ay), (bx, by))
        if d == 0:
            continue
        n = max(1, int(d / step))
        for k in range(1, n + 1):
            t = k / n
            out.append((ax + (bx - ax) * t, ay + (by - ay) * t, acc + d * t))
        acc += d
    return out

def _tangent(samples, i):
    j0, j1 = max(0, i - 2), min(len(samples) - 1, i + 2)
    dx = samples[j1][0] - samples[j0][0]
    dy = samples[j1][1] - samples[j0][1]
    n = math.hypot(dx, dy) or 1.0
    return (dx / n, dy / n)

def audit(paths_a, paths_b=None, min_gap=26.0, crisp_deg=35.0, run_mm=14.0,
          step=2.0, self_skip_mm=40.0):
    sa = [_resample(p, step) for p in paths_a]
    sb = sa if paths_b is None else [_resample(p, step) for p in paths_b]
    self_mode = paths_b is None
    # closed loops (first==last): same-path arc distance wraps around, else the
    # closure point pairs its own start/end and self-flags a phantom violation
    closed_len = [s[-1][2] if math.dist(s[0][:2], s[-1][:2]) < 0.1 else None
                  for s in sa]
    events = []          # (a_idx, i, b_idx, j, d, angle)
    for ai, A in enumerate(sa):
        for bi, B in enumerate(sb):
            if self_mode and bi < ai:
                continue
            for i, (ax, ay, at) in enumerate(A):
                best = None
                for j, (bx, by, bt) in enumerate(B):
                    if self_mode and ai == bi:
                        arc = abs(at - bt)
                        if closed_len[ai]:
                            arc = min(arc, closed_len[ai] - arc)
                        if arc < self_skip_mm:
                            continue
                    d = math.dist((ax, ay), (bx, by))
                    if d < min_gap and (best is None or d < best[0]):
                        best = (d, j)
                if best:
                    ta = _tangent(A, i)
                    tb = _tangent(B, best[1])
                    dot = abs(ta[0] * tb[0] + ta[1] * tb[1])
                    ang = math.degrees(math.acos(max(-1, min(1, dot))))
                    events.append((ai, i, bi, best[1], best[0], ang, ax, ay, at))
    # group consecutive sub-gap samples on the same (a,b) pair into runs
    events.sort(key=lambda e: (e[0], e[2], e[8]))
    runs = []
    for e in events:
        if runs and runs[-1]["a"] == e[0] and runs[-1]["b"] == e[2] and \
           e[8] - runs[-1]["_end_t"] <= step * 1.5:
            r = runs[-1]
            r["run"] = e[8] - r["_start_t"]
            r["_end_t"] = e[8]
            if e[4] < r["d"]:
                r["d"], r["ax"], r["ay"] = e[4], e[6], e[7]
            r["angle"] = min(r["angle"], e[5])
        else:
            runs.append({"a": e[0], "b": e[2], "d": e[4], "angle": e[5],
                         "ax": e[6], "ay": e[7], "run": 0.0,
                         "_start_t": e[8], "_end_t": e[8]})
    for r in runs:
        r.pop("_start_t"); r.pop("_end_t")
        r["violation"] = r["angle"] < crisp_deg and r["run"] > run_mm
    return runs

def summarize(runs, label=""):
    vio = [r for r in runs if r["violation"]]
    print("%s: %d sub-gap contact runs, %d VIOLATIONS (parallel mush)"
          % (label or "audit", len(runs), len(vio)))
    for r in sorted(runs, key=lambda r: (not r["violation"], r["d"])):
        print("  %s d=%.1f angle=%.0f deg run=%.0fmm at (%.0f,%.0f) [%d-%d]"
              % ("VIOLATION" if r["violation"] else "crisp/ok ",
                 r["d"], r["angle"], r["run"], r["ax"], r["ay"], r["a"], r["b"]))
    return len(vio)

if __name__ == "__main__":
    import sys, re, json
    txt = open(sys.argv[1]).read()
    name = re.search(r"^(\w+)_paths", txt, re.M).group(1)
    paths = json.loads(re.search(name + r"_paths\s*=\s*(.*?);", txt, re.S).group(1))
    sys.exit(0 if summarize(audit(paths), sys.argv[1]) == 0 else 1)
