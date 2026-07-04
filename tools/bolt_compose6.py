#!/usr/bin/env python3
"""Compose the element-6 bolt board (C1 look: yellow fused bolt+X outline + red
inner zigzag) into src/parts/bolt_el6.json for tools/boltboard.py.

- Yellow: src/parts/boltx_data.scad (element-6 extraction, 3 open runs, y-up mm).
- Red:    RED_PATH below (billboard-derived single-stroke zigzag, clearance-audited
          legal vs yellow: see tools/clearance_audit.py).
- Face 410x550, 4 rectangular plates. Y-seam at face y=255 (below the red tail
  tip -> red never crosses a seam). Each row gets its OWN vertical seam position
  (piecewise seam: a full-height vertical cut cannot avoid grazing the X's
  near-vertical leg strokes). Each x-seam segment chosen by scan: fewest
  crossings, all crisp (stroke >= CRISP deg off the seam direction), no cut
  within KEEPOUT of a path end/junction, pieces >= MIN_PIECE after pullbacks.
Writes bolt_el6.json {face, seam_y, seam_x_top, seam_x_bot, c1:{...}}.
"""
import json, math, re, sys

FW, FH = 410.0, 550.0
SEAM_Y_FACE = 255.0
PULL = 13.0            # pullback from seam to tube-end centerline (styled neon break)
MIN_PIECE = 22.0       # drop any post-split stub shorter than this
# Angle floor for seam cuts: with 13mm pullbacks a cut at >=25 deg reads as a
# normal neon segment gap (the 35-deg "crisp" bar is the CHANNEL-PROXIMITY mush
# rule, enforced separately by clearance_audit + the graze check below). The
# element-6 body edges run 28 deg off vertical, so 35 would leave NO legal
# vertical seam through the upper row.
CRISP = 25.0
KEEPOUT = 18.0         # no seam cut within this arc-distance of an existing path end
RED_PATH = [[228.0, 466.0], [118.0, 349.0], [253.0, 349.0], [194.0, 239.0]]

def load_paths(scad, name):
    txt = open(scad).read()
    return json.loads(re.search(name + r"_paths\s*=\s*(.*?);", txt, re.S).group(1))

def plen(p):
    return sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))

def cut_at(p, coord, axis, band=None):
    """Split polyline p where it crosses `coord` on axis, but only inside
    `band` = (lo, hi) on the OTHER axis (None = everywhere)."""
    pieces, cur = [], [p[0]]
    for i in range(len(p) - 1):
        a, b = p[i], p[i + 1]
        va, vb = a[axis] - coord, b[axis] - coord
        if va == 0:
            va = 1e-9
        f = va / (va - vb) if (va < 0) != (vb < 0) else None
        if f is None:
            cur.append(b)
            continue
        hit = [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]
        if band and not (band[0] <= hit[1 - axis] <= band[1]):
            cur.append(b)
            continue
        cur.append(hit)
        pieces.append(cur)
        cur = [hit, b]
    pieces.append(cur)
    return pieces

def trim(p, amount, from_start):
    """Remove `amount` mm of arc length from one end."""
    if from_start:
        p = p[::-1]
    total, out = 0.0, [p[0]]
    keep = plen(p) - amount
    for i in range(len(p) - 1):
        d = math.dist(p[i], p[i + 1])
        if total + d >= keep:
            f = (keep - total) / d if d else 0
            out.append([p[i][0] + (p[i + 1][0] - p[i][0]) * f,
                        p[i][1] + (p[i + 1][1] - p[i][1]) * f])
            break
        out.append(p[i + 1])
        total += d
    return out[::-1] if from_start else out

def _pull_arc(piece, axis, at_start):
    """Arc length to trim so the new end sits PULL mm perpendicular from the
    seam plane (pullback is arc-based; shallow crossings need a longer trim)."""
    a = piece[0] if at_start else piece[-1]
    b = piece[1] if at_start else piece[-2]
    dx, dy = b[0] - a[0], b[1] - a[1]
    nl = math.hypot(dx, dy) or 1
    sin_off = abs((dx, dy)[axis]) / nl        # component perpendicular to seam
    return PULL / max(sin_off, 0.42)

def split_with_pullback(paths, coord, axis, band=None):
    out, breaks = [], 0
    for p in paths:
        pieces = cut_at(p, coord, axis, band)
        if len(pieces) == 1:
            out.append(p)
            continue
        for k, piece in enumerate(pieces):
            q = piece
            if k > 0 and len(q) > 1:
                q = trim(q, _pull_arc(q, axis, True), from_start=True)
            if k < len(pieces) - 1 and len(q) > 1:
                q = trim(q, _pull_arc(q, axis, False), from_start=False)
            if plen(q) >= MIN_PIECE:
                out.append([[round(v, 2) for v in pt] for pt in q])
        breaks += len(pieces) - 1
    return out, breaks

def corners(p, min_turn=30.0, leg=8.0):
    """Interior vertices where the path turns >= min_turn deg (protected like
    endpoints: a seam cut near one amputates the corner)."""
    out = []
    for i in range(1, len(p) - 1):
        a, b, c = p[i - 1], p[i], p[i + 1]
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        n1, n2 = math.hypot(*v1), math.hypot(*v2)
        if n1 < leg / 4 or n2 < leg / 4:
            continue
        dot = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
        if math.degrees(math.acos(max(-1, min(1, dot)))) >= min_turn:
            out.append(b)
    return out

def seam_quality(paths, coord, axis, ends, band=None):
    """Return (n_crossings, worst_angle_off_seam, min_end_dist, ok) for the
    seam segment at `coord` on axis, restricted to `band` on the other axis.
    min_end_dist covers path ends AND sharp corners. Double-crossings closer
    than 24mm arc (tangent apexes) are rejected outright."""
    n, worst, mind = 0, 90.0, 1e9
    for p in paths:
        acc = 0.0
        L = plen(p)
        arcs_this = []
        for i in range(len(p) - 1):
            a, b = p[i], p[i + 1]
            d = math.dist(a, b)
            va, vb = a[axis] - coord, b[axis] - coord
            if (va < 0) != (vb < 0) and va != 0:
                dx, dy = b[0] - a[0], b[1] - a[1]
                nl = math.hypot(dx, dy) or 1
                f = va / (va - vb)
                hit = (a[0] + dx * f, a[1] + dy * f)
                if band is None or band[0] <= hit[1 - axis] <= band[1]:
                    n += 1
                    seam_dir = (0, 1) if axis == 0 else (1, 0)
                    dot = abs(dx / nl * seam_dir[0] + dy / nl * seam_dir[1])
                    ang = math.degrees(math.acos(max(-1, min(1, dot))))
                    worst = min(worst, ang)
                    arc = acc + d * f
                    arcs_this.append(arc)
                    mind = min(mind, arc, L - arc,
                               *(math.dist(hit, e) for e in ends))
            acc += d
        if any(b2 - a2 < 24.0 for a2, b2 in
               zip(sorted(arcs_this), sorted(arcs_this)[1:])):
            return n, worst, -1.0, False       # tangent apex / sliver cut
    # graze check: any sample hugging the seam line (band edge would be cut
    # lengthwise) that is not part of a legitimate crossing
    for p in paths:
        acc2, L = 0.0, plen(p)
        xarcs = []
        for i in range(len(p) - 1):
            a, b = p[i], p[i + 1]
            d = math.dist(a, b)
            va, vb = a[axis] - coord, b[axis] - coord
            if (va < 0) != (vb < 0) and va != 0:
                f = va / (va - vb)
                hit = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
                if band is None or band[0] <= hit[1 - axis] <= band[1]:
                    xarcs.append(acc2 + d * f)
            acc2 += d
        acc2 = 0.0
        for i in range(len(p)):
            q = p[i]
            if i:
                acc2 += math.dist(p[i - 1], q)
            in_band = band is None or band[0] - 2 <= q[1 - axis] <= band[1] + 2
            if in_band and abs(q[axis] - coord) < 12.0 and \
               not any(abs(acc2 - xa) < 30.0 for xa in xarcs):
                return n, worst, -1.0, False        # graze -> illegal
    ok = worst >= CRISP and mind >= KEEPOUT
    return n, worst, mind, ok

def main():
    yellow = load_paths("src/parts/boltx_data.scad", "BOLTX")
    red = [RED_PATH]
    ends = [p[0] for p in yellow + red] + [p[-1] for p in yellow + red]
    for p in yellow + red:
        ends += corners(p)

    # ---- place content on the face ----
    xs = [q[0] for p in yellow for q in p]
    ys = [q[1] for p in yellow for q in p]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    ox = (FW - (bw + 22)) / 2 + 11 - min(xs)
    oy = (FH - (bh + 22)) / 2 + 11 - min(ys)
    Y = [[[q[0] + ox, q[1] + oy] for q in p] for p in yellow]
    R = [[[q[0] + ox, q[1] + oy] for q in p] for p in red]
    ends = [[e[0] + ox, e[1] + oy] for e in ends]
    print("content %.0fx%.0f band-outer, margins x %.1f y %.1f"
          % (bw + 22, bh + 22, (FW - bw - 22) / 2, (FH - bh - 22) / 2))

    # ---- per-row x-seam scans (piecewise vertical seam) ----
    lo, hi = int(FW - 316 + 1), int(316 - 1)
    seams = {}
    for label, band in (("top", (SEAM_Y_FACE, FH)), ("bot", (0.0, SEAM_Y_FACE))):
        cands = []
        for sx in range(lo, hi):
            n, worst, mind, ok = seam_quality(Y + R, float(sx), 0, ends, band)
            if ok:
                cands.append((n, -worst, -mind, sx))
        if not cands:
            sys.exit("NO legal x-seam for row " + label)
        cands.sort()
        n, worst, mind, sx = cands[0][0], -cands[0][1], -cands[0][2], cands[0][3]
        seams[label] = float(sx)
        print("x-seam %s @ face x=%.0f: %d crossings, worst angle %.0f deg, "
              "min end-dist %.0f  (%d legal candidates)"
              % (label, sx, n, worst, mind, len(cands)))

    ny, wy, my, _ = seam_quality(Y + R, SEAM_Y_FACE, 1, ends)
    print("y-seam @ face y=%.0f: %d crossings, worst angle %.0f deg, "
          "min end-dist %.0f" % (SEAM_Y_FACE, ny, wy, my))

    # ---- split: y-seam, then each row's x-seam inside its band ----
    Y1, by = split_with_pullback(Y, SEAM_Y_FACE, 1)
    R1, bry = split_with_pullback(R, SEAM_Y_FACE, 1)
    Y2, bxt = split_with_pullback(Y1, seams["top"], 0, (SEAM_Y_FACE, FH))
    Y3, bxb = split_with_pullback(Y2, seams["bot"], 0, (0.0, SEAM_Y_FACE))
    R2, brt = split_with_pullback(R1, seams["top"], 0, (SEAM_Y_FACE, FH))
    R3, brb = split_with_pullback(R2, seams["bot"], 0, (0.0, SEAM_Y_FACE))
    breaks = by + bry + bxt + bxb + brt + brb
    tube = sum(plen(p) for p in Y3 + R3)
    print("after split: yellow %d runs, red %d runs, %d breaks, tube %.0f mm"
          % (len(Y3), len(R3), breaks, tube))

    # ---- post-split assertion: every point clears every seam segment ----
    segs = [(1, SEAM_Y_FACE, 0.0, FW),
            (0, seams["top"], SEAM_Y_FACE, FH),
            (0, seams["bot"], 0.0, SEAM_Y_FACE)]
    worst_clear = 1e9
    for p in Y3 + R3:
        for q in p:
            for axis, coord, b0, b1 in segs:
                if b0 - 1 <= q[1 - axis] <= b1 + 1:
                    worst_clear = min(worst_clear, abs(q[axis] - coord))
    print("post-split min point-to-seam clearance: %.1f mm (need >= ~12)"
          % worst_clear)
    if worst_clear < 11.5:
        sys.exit("SEAM CLEARANCE FAILURE")

    json.dump({"face": [FW, FH], "seam_y": SEAM_Y_FACE,
               "seam_x_top": seams["top"], "seam_x_bot": seams["bot"],
               "c1": {"yellow": Y3, "red": R3,
                      "breaks": breaks, "tube": round(tube)}},
              open("src/parts/bolt_el6.json", "w"))
    print("wrote src/parts/bolt_el6.json")

if __name__ == "__main__":
    main()
