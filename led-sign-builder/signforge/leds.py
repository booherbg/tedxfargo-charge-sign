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


def place_pixels(strokes: list[Stroke], params: SignParams) -> LedPlan:
    lp = params.leds
    pixels: list[Point2] = []
    per_stroke: list[list[int]] = []
    audits: list[str] = []

    for s in strokes:
        placed = _place_stroke(s, lp.pitch_mm, lp.min_chord_mm)
        idx = []
        for p in placed:
            idx.append(len(pixels))
            pixels.append((round(p[0], 2), round(p[1], 2)))
        per_stroke.append(idx)

    # pass 1: drop coincident / hard-floor violators (keep the earlier pixel)
    drop: set[int] = set()
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
                audits.append(
                    f"dropped pixel at ({pixels[j][0]:.0f},{pixels[j][1]:.0f}): "
                    f"{d:.1f} mm from a neighbor (< 13.0 hard floor)"
                )
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
    for i, j, d in snug:
        audits.append(
            f"snug pair {d:.1f} mm at ({pixels[i][0]:.0f},{pixels[i][1]:.0f}) — "
            "flange Ø13.6, check/trim flanges at install"
        )

    # wiring: stroke order; long jumps between consecutive stroke ends need jumpers
    for a, b in zip(per_stroke, per_stroke[1:]):
        if a and b:
            d = math.dist(pixels[a[-1]], pixels[b[0]])
            if d > 101.6:
                audits.append(
                    f"chain gap {d:.0f} mm between runs — needs an extension jumper (4\" strings)"
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
