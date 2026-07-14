"""LED pixel placement + power planning.

Placement law (lessons 18/19): space by CHORD, not arc (raster skeletons
zigzag); pin stroke ends; flange floor 14.5 mm between ANY pair; report snug
pairs (13.0–14.5) instead of silently shipping them; budgets are hard caps
that surface loudly. Open strokes use the uniform-chord walker ported from
CHARGE make_repairs.py; closed loops use equal-arc resampling.
"""

from __future__ import annotations

import math

from .export.bundle import psu_pick
from .model import LedPlan, Point2, PowerPlan, Stroke
from .params import SignParams
from .skeleton import path_len, resample


JUMPER_MM = 101.6  # 4" pigtails between consecutive pixels


def wled_ledmap(
    pixels: list[Point2], per_stroke: list[list[int]], cell_mm: float | None = None
) -> dict:
    """WLED 2D ledmap: quantize the physical layout onto a matrix so WLED's 2D
    effects play across the sign's real shape.

    LED indices follow the wiring chain. Cells hold the LED index or -1.
    Rows are top-first (WLED's y grows downward). Upload the JSON as
    `ledmap.json`; on WLED 16.x the width/height keys switch the controller
    into 2D matrix mode at boot (no 2D Configuration needed). NOTE: once the
    map loads, segments are rectangles (start/stop = columns, startY/stopY =
    rows), not chain ranges."""
    order = [i for run in per_stroke for i in run]
    if not order:
        return {"width": 0, "height": 0, "map": [], "n": 0}
    led_of = {pix: led for led, pix in enumerate(order)}
    pts = [pixels[i] for i in order]
    if cell_mm is None:
        gaps = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
        cell_mm = max(6.0, min(gaps) * 0.9) if gaps else 15.0
    x0 = min(p[0] for p in pts)
    y1 = max(p[1] for p in pts)
    W = int((max(p[0] for p in pts) - x0) / cell_mm) + 2
    H = int((y1 - min(p[1] for p in pts)) / cell_mm) + 2
    grid = [[-1] * W for _ in range(H)]

    def place(cx: int, cy: int, led: int) -> bool:
        if 0 <= cx < W and 0 <= cy < H and grid[cy][cx] == -1:
            grid[cy][cx] = led
            return True
        return False

    for pix_i in order:
        x, y = pixels[pix_i]
        cx = round((x - x0) / cell_mm)
        cy = round((y1 - y) / cell_mm)          # flip: WLED y is down
        if place(cx, cy, led_of[pix_i]):
            continue
        placed = False
        for ring in (1, 2):                      # nudge to a nearby free cell
            for dy in range(-ring, ring + 1):
                for dx in range(-ring, ring + 1):
                    if max(abs(dx), abs(dy)) == ring and place(cx + dx, cy + dy, led_of[pix_i]):
                        placed = True
                        break
                if placed:
                    break
            if placed:
                break
    return {
        "width": W,
        "height": H,
        "n": len(order),
        "cell_mm": round(cell_mm, 2),
        "map": [v for row in grid for v in row],
    }


def chain_hops(
    pixels: list[Point2], per_stroke: list[list[int]]
) -> list[tuple[Point2, Point2, bool]]:
    """Wiring order (one data line): pixels within each run in placement
    order, runs in stroke order. Returns (a, b, needs_jumper) per hop."""
    order = [i for run in per_stroke for i in run]
    return [
        (pixels[a], pixels[b], math.dist(pixels[a], pixels[b]) > JUMPER_MM)
        for a, b in zip(order, order[1:])
    ]


def chain_length_mm(pixels: list[Point2], per_stroke: list[list[int]]) -> float:
    return sum(math.dist(a, b) for a, b, _ in chain_hops(pixels, per_stroke))


def densify(poly: list[Point2], step: float = 0.25) -> list[Point2]:
    out = [tuple(poly[0])]
    for a, b in zip(poly, poly[1:]):
        L = math.dist(a, b)
        n = max(1, int(L / step))
        for i in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return out


def chord_chain(poly: list[Point2], n: int) -> list[Point2]:
    """n+1 points along poly with equal consecutive CHORDS, ends pinned.
    Port of CHARGE tools/make_repairs.py chord_chain (binary-search walk)."""
    P = densify(poly)
    end = P[-1]

    def walk(t: float) -> list[Point2]:
        placed, last = [P[0]], P[0]
        for q in P[1:]:
            if math.dist(q, last) >= t:
                placed.append(q)
                last = q
        return placed

    lo, hi = 1.0, 400.0
    for _ in range(80):
        t = (lo + hi) / 2
        pl = walk(t)
        g = (len(pl) - 1) + math.dist(pl[-1], end) / t
        if g > n:
            lo = t
        else:
            hi = t

    def spread(pts: list[Point2]) -> float:
        chords = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
        return max(chords) - min(chords) if chords else 0.0

    # lo/hi can bracket an unstable placement boundary (uniform geometry):
    # evaluate both and keep the more uniform chain
    cands = [walk(lo)[:n] + [end], walk(hi)[:n] + [end]]
    return min(cands, key=spread)


def _place_stroke(s: Stroke, pitch: float, min_chord: float) -> list[Point2]:
    L = s.length()
    if s.closed:
        pts = s.pts + [s.pts[0]]
        n = max(3, round(L / pitch))
        placed = resample(pts[:-1], L / n, True)
        return placed
    n_pts = max(2, round(L / pitch) + 1)
    for n in range(n_pts, max(2, n_pts - 4), -1):
        cand = chord_chain(s.pts, n - 1)
        chords = [math.dist(a, b) for a, b in zip(cand, cand[1:])]
        if min(chords) >= min_chord:
            return cand
    return [s.pts[0], s.pts[-1]] if L >= min_chord else [s.pts[0]]


def strip_plan(strokes: list[Stroke], params: SignParams) -> LedPlan:
    """LED strip in the channel instead of pixels: no bores, length-based power."""
    lp = params.leds
    length_mm = sum(s.length() for s in strokes)
    watts = length_mm / 1000 * lp.watts_per_m
    power = PowerPlan(
        count=0,
        watts=watts,
        amps=watts / lp.volts if lp.volts else 0.0,
        psu_watts=psu_pick(watts, lp.psu_headroom) if watts else 0,
        strings=0,
        budget_px=None,
    )
    audits = [
        f"strip mode: {length_mm / 1000:.2f} m of channel — buy ~{length_mm / 1000 * 1.1:.1f} m "
        f"({lp.watts_per_m} W/m); feed both ends past 3 m to avoid voltage droop"
    ]
    return LedPlan(pixels=[], per_stroke=[[] for _ in strokes], power=power, audits=audits)


def _seam_dist(p: Point2, seams: list) -> float:
    """Distance to the nearest seam. Seams may be ('x'|'y', coord) axis lines
    or shapely LineStrings (corridor seams)."""
    if not seams:
        return 1e9
    best = 1e9
    for s in seams:
        if isinstance(s, tuple):
            axis, c = s
            d = abs((p[0] if axis == "x" else p[1]) - c)
        else:
            from shapely.geometry import Point as _P

            d = s.distance(_P(p))
        if d < best:
            best = d
    return best


def _split_at_seams(
    stroke: Stroke, seams: list, keepout: float
) -> list[list[Point2]]:
    """Cut a stroke into seam-bounded segments, each inset by the keepout.

    This is the CHARGE order of operations: pixels are placed per piece-run,
    evenly, with ends pinned at the keepout — so no collar can straddle a
    joint BY CONSTRUCTION (vs. nudging placed pixels, which corners itself
    when the pitch is tighter than 2× keepout)."""
    dense = densify(stroke.pts + ([stroke.pts[0]] if stroke.closed else []))
    if not seams:
        return [dense]
    keep = [_seam_dist(q, seams) >= keepout for q in dense]
    runs: list[list[Point2]] = []
    cur: list[Point2] = []
    for q, ok in zip(dense, keep):
        if ok:
            cur.append(q)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    # a closed loop whose start sample isn't near a seam: first+last runs are
    # actually one continuous run across the arbitrary start point
    if stroke.closed and len(runs) >= 2 and keep[0] and keep[-1]:
        runs[0] = runs.pop() + runs[0]
    return [r for r in runs if len(r) >= 2]


def _place_segment(seg: list[Point2], pitch: float, min_chord: float) -> list[Point2]:
    L = sum(math.dist(a, b) for a, b in zip(seg, seg[1:]))
    if L < min_chord * 0.7:
        return []
    n_pts = max(2, round(L / pitch) + 1)
    for n in range(n_pts, 1, -1):
        cand = chord_chain(seg, n - 1) if n > 2 else [seg[0], seg[-1]]
        chords = [math.dist(a, b) for a, b in zip(cand, cand[1:])]
        if not chords or min(chords) >= min_chord:
            return cand
    return [seg[0]]


def place_pixels(
    strokes: list[Stroke],
    params: SignParams,
    seams: list | None = None,
) -> LedPlan:
    lp = params.leds
    pixels: list[Point2] = []
    per_stroke: list[list[int]] = []
    audits: list[str] = []

    for s in strokes:
        crosses_seam = False
        if seams:
            probe = densify(s.pts + ([s.pts[0]] if s.closed else []), step=2.0)
            crosses_seam = any(_seam_dist(q, seams) < lp.seam_keepout_mm for q in probe)
        idx: list[int] = []
        if crosses_seam:
            for seg in _split_at_seams(s, seams or [], lp.seam_keepout_mm):
                placed = _place_segment(seg, lp.pitch_mm, lp.min_chord_mm)
                for p in placed:
                    idx.append(len(pixels))
                    pixels.append((round(p[0], 2), round(p[1], 2)))
        else:
            placed = _place_stroke(s, lp.pitch_mm, lp.min_chord_mm)
            for p in placed:
                idx.append(len(pixels))
                pixels.append((round(p[0], 2), round(p[1], 2)))
        per_stroke.append(idx)

    # pass 1: drop coincident / hard-floor violators (keep the earlier pixel)
    drop: set[int] = set()
    drop_msgs: list[str] = []
    for i in range(len(pixels)):
        if i in drop:
            continue
        for j in range(i + 1, len(pixels)):
            if j in drop:
                continue
            d = math.dist(pixels[i], pixels[j])
            if d < 0.01:
                drop.add(j)  # coincident (stroke endpoints kissing)
            elif d < 13.0:
                drop.add(j)
                drop_msgs.append(
                    f"({pixels[j][0]:.0f},{pixels[j][1]:.0f}) {d:.1f} mm"
                )
    # thinning at tight corners is NORMAL de-confliction (two flanges can't
    # share <13 mm) — neighbors carry the glow. Say so, don't alarm.
    if len(drop_msgs) > 4:
        audits.append(
            f"{len(drop_msgs)} corners too tight for two flanges — thinned one "
            f"pixel at each (glow stays continuous); first at "
            f"{', '.join(drop_msgs[:3])}. A larger sign or sparser pitch avoids this"
        )
    else:
        audits += [
            f"tight corner at {m} — thinned one pixel (two flanges can't share "
            "<13.0 mm; glow stays continuous)" for m in drop_msgs
        ]
    if drop:
        keep = [k for k in range(len(pixels)) if k not in drop]
        remap = {old: new for new, old in enumerate(keep)}
        pixels = [pixels[k] for k in keep]
        per_stroke = [[remap[k] for k in run if k in remap] for run in per_stroke]

    # pass 2: audit final spacing (chord-measured, cross-stroke included)
    snug: list[tuple[int, int, float]] = []
    worst: float | None = None
    for i in range(len(pixels)):
        for j in range(i + 1, len(pixels)):
            d = math.dist(pixels[i], pixels[j])
            if d > 2 * lp.pitch_mm:
                continue
            if worst is None or d < worst:
                worst = d
            if d < lp.flange_floor_mm:
                snug.append((i, j, round(d, 2)))
    if len(snug) > 4:
        worst_snug = min(d for _, _, d in snug)
        audits.append(
            f"{len(snug)} snug pairs (13.0–14.5 mm, worst {worst_snug:.1f}) — "
            "flange Ø13.6, check/trim flanges at install (positions in the preview)"
        )
    else:
        for i, j, d in snug:
            audits.append(
                f"snug pair {d:.1f} mm at ({pixels[i][0]:.0f},{pixels[i][1]:.0f}) — "
                "flange Ø13.6, check/trim flanges at install"
            )

    # wiring: stroke order; long hops need extension jumpers (4" pigtails)
    for pa, pb, is_jumper in chain_hops(pixels, per_stroke):
        if is_jumper:
            audits.append(
                f"chain hop {math.dist(pa, pb):.0f} mm at ({pa[0]:.0f},{pa[1]:.0f})→"
                f"({pb[0]:.0f},{pb[1]:.0f}) — needs an extension jumper"
            )

    n = len(pixels)
    watts = n * lp.watts_per_px
    power = PowerPlan(
        count=n,
        watts=watts,
        amps=watts / lp.volts if lp.volts else 0.0,
        psu_watts=psu_pick(watts, lp.psu_headroom) if n else 0,
        strings=math.ceil(n / 50) if n else 0,
        budget_px=lp.budget_px,
    )
    if power.over_budget:
        audits.insert(
            0,
            f"PIXEL BUDGET EXCEEDED: {n} needed > {lp.budget_px} budgeted — "
            "raise the budget explicitly or reduce pitch/size",
        )
    return LedPlan(
        pixels=pixels,
        per_stroke=per_stroke,
        power=power,
        audits=audits,
        snug_pairs=snug,
        worst_chord=worst,
    )
