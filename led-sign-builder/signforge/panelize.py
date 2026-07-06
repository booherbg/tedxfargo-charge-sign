"""Panelization: fit the sign to the printer bed.

Seam placement is a constraint solver, not a slice (lesson 17): candidate
guillotine cuts are scored by tube crossings, crossing angle (crisp ≥25°,
never a graze), and pixel keepout (≥12.5 mm — no collar straddles a joint).
Seam faces get the seam clearance (0.06 mm/face). Every piece gets a label
(debossed mirrored on the back AND shown in previews — lesson 27) and corner
screws with mid-span fill on long runs (anti-lift, lesson from 5b9d695).
v1 cuts are straight; corridor/piecewise seams are the documented P2 upgrade.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import Polygon

from .geom2d import bbox_polygon
from .model import Piece, Point2, Stroke
from .params import SignParams

CUT_GRID_MM = 5.0
EDGE_KEEPOUT_MM = 40.0   # don't cut within this of a region edge
CRISP_MIN_DEG = 25.0


@dataclass
class _Region:
    x0: float
    y0: float
    x1: float
    y1: float
    cuts: list[str] = field(default_factory=list)  # which sides are cut faces

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    @property
    def h(self) -> float:
        return self.y1 - self.y0


def _fits(w: float, h: float, bed: tuple[float, float]) -> tuple[bool, bool]:
    """(fits, rotated)"""
    bx, by = bed
    if w <= bx and h <= by:
        return True, False
    if h <= bx and w <= by:
        return True, True
    return False, False


def _crossings(strokes: list[Stroke], axis: str, c: float) -> list[float]:
    """Angles (deg vs the cut line) where strokes cross the line axis=c."""
    out = []
    for s in strokes:
        pts = s.pts + ([s.pts[0]] if s.closed else [])
        for a, b in zip(pts, pts[1:]):
            pa = a[0] if axis == "x" else a[1]
            pb = b[0] if axis == "x" else b[1]
            if (pa <= c < pb) or (pb <= c < pa):
                dx, dy = b[0] - a[0], b[1] - a[1]
                L = math.hypot(dx, dy) or 1.0
                # angle between segment and the cut LINE direction
                lined = (0.0, 1.0) if axis == "x" else (1.0, 0.0)
                dot = abs((dx * lined[0] + dy * lined[1]) / L)
                out.append(math.degrees(math.acos(max(-1.0, min(1.0, dot)))))
    return out


def _pixel_min_dist(pixels: list[Point2], axis: str, c: float) -> float:
    if not pixels:
        return 1e9
    return min(abs((p[0] if axis == "x" else p[1]) - c) for p in pixels)


def _best_cut(
    region: _Region, strokes: list[Stroke], pixels: list[Point2], params: SignParams
) -> tuple[str, float] | None:
    axis = "x" if region.w >= region.h else "y"
    lo = (region.x0 if axis == "x" else region.y0) + EDGE_KEEPOUT_MM
    hi = (region.x1 if axis == "x" else region.y1) - EDGE_KEEPOUT_MM
    if hi <= lo:
        return None
    mid = (lo + hi) / 2
    keep = params.leds.seam_keepout_mm
    best = None
    c = lo
    while c <= hi:
        angles = _crossings(strokes, axis, c)
        pxd = _pixel_min_dist(pixels, axis, c)
        if pxd >= keep:
            worst_angle = min(angles) if angles else 90.0
            score = (
                len(angles),                                   # fewest tube crossings
                0 if worst_angle >= CRISP_MIN_DEG else 1,      # never graze
                -pxd if pxd < 25 else -25,                     # pixel breathing room
                abs(c - mid),                                  # prefer the middle
            )
            if best is None or score < best[0]:
                best = (score, c)
        c += CUT_GRID_MM
    if best is None:
        return None
    return axis, best[1]


def panelize(
    footprint: Polygon,
    strokes: list[Stroke],
    pixels: list[Point2],
    params: SignParams,
    avoid=None,
) -> tuple[list[Piece], list[tuple[str, float]], list[str]]:
    """Split the sign footprint into bed-fitting rectangular pieces.

    Returns (pieces, cut_lines, warnings). Call BEFORE pixel placement and
    feed cut_lines to leds.place_pixels(seams=...) — pixels dodge seams, not
    the other way around (CHARGE panelizer order)."""
    warnings: list[str] = []
    fx0, fy0, fx1, fy1 = footprint.bounds
    bed = params.printer.bed
    regions: list[_Region] = []
    cut_lines: list[tuple[str, float]] = []
    queue = [_Region(fx0, fy0, fx1, fy1)]
    while queue:
        r = queue.pop(0)
        fits, rot = _fits(r.w, r.h, bed)
        if fits:
            regions.append(r)
            continue
        cut = _best_cut(r, strokes, pixels, params)
        if cut is None:
            regions.append(r)
            warnings.append(
                f"piece {r.w:.0f}×{r.h:.0f} mm exceeds the bed and no legal cut "
                "was found — reduce size or use a larger printer preset"
            )
            continue
        axis, c = cut
        cut_lines.append((axis, c))
        if axis == "x":
            queue.append(_Region(r.x0, r.y0, c, r.y1, r.cuts + ["x1"]))
            queue.append(_Region(c, r.y0, r.x1, r.y1, r.cuts + ["x0"]))
        else:
            queue.append(_Region(r.x0, r.y0, r.x1, c, r.cuts + ["y1"]))
            queue.append(_Region(r.x0, c, r.x1, r.y1, r.cuts + ["y0"]))

    regions.sort(key=lambda r: (r.y0, r.x0))
    sc = params.fit.seam_clearance_mm
    keep = params.leds.seam_keepout_mm
    pieces: list[Piece] = []
    for i, r in enumerate(regions):
        # seam clearance only on CUT faces; outer faces stay exact
        x0 = r.x0 + (sc if "x0" in r.cuts else -1.0)
        x1 = r.x1 - (sc if "x1" in r.cuts else -1.0)
        y0 = r.y0 + (sc if "y0" in r.cuts else -1.0)
        y1 = r.y1 - (sc if "y1" in r.cuts else -1.0)
        mask = bbox_polygon(x0, y0, x1, y1)
        _, rotated = _fits(r.w, r.h, bed)
        label = f"P{i + 1}"
        pix_idx = [
            k
            for k, p in enumerate(pixels)
            if r.x0 - 0.01 <= p[0] < r.x1 + (0.01 if "x1" not in r.cuts else 0)
            and r.y0 - 0.01 <= p[1] < r.y1 + (0.01 if "y1" not in r.cuts else 0)
        ]
        for k in pix_idx:
            p = pixels[k]
            d_cut = min(
                [abs(p[0] - r.x1)] * ("x1" in r.cuts)
                + [abs(p[0] - r.x0)] * ("x0" in r.cuts)
                + [abs(p[1] - r.y1)] * ("y1" in r.cuts)
                + [abs(p[1] - r.y0)] * ("y0" in r.cuts)
                + [1e9]
            )
            if d_cut < keep:
                warnings.append(
                    f"pixel at ({p[0]:.0f},{p[1]:.0f}) is {d_cut:.1f} mm from a seam "
                    f"(< {keep} keepout) — collar may straddle the joint"
                )
        pieces.append(
            Piece(
                name=f"piece{i + 1}",
                label=label,
                mask=mask,
                rotated=rotated,
                screws=_screws(r, params, avoid),
                pixel_idx=pix_idx,
            )
        )
    return pieces, cut_lines, warnings


def assign_pixels(pieces: list[Piece], pixels: list[Point2]) -> None:
    """Assign each pixel to exactly one piece (first mask whose bounds hold it)."""
    for pc in pieces:
        pc.pixel_idx = []
    taken: set[int] = set()
    for k, p in enumerate(pixels):
        for pc in pieces:
            x0, y0, x1, y1 = pc.mask.bounds
            if x0 - 0.5 <= p[0] <= x1 + 0.5 and y0 - 0.5 <= p[1] <= y1 + 0.5 and k not in taken:
                pc.pixel_idx.append(k)
                taken.add(k)
                break


def _screws(r: _Region, params: SignParams, avoid=None) -> list[Point2]:
    if not params.style.screw_holes or params.style.backer == "none":
        return []
    inset = params.style.screw_inset_mm
    xs = [r.x0 + inset, r.x1 - inset]
    ys = [r.y0 + inset, r.y1 - inset]
    if xs[1] <= xs[0] or ys[1] <= ys[0]:
        return []
    pts = [(x, y) for x in xs for y in ys]
    span = params.style.screw_midspan_mm
    if r.w > span:
        pts += [((r.x0 + r.x1) / 2, ys[0]), ((r.x0 + r.x1) / 2, ys[1])]
    if r.h > span:
        pts += [(xs[0], (r.y0 + r.y1) / 2), (xs[1], (r.y0 + r.y1) / 2)]
    if avoid is not None and not avoid.is_empty:
        # a screw through a lit channel is a light leak (lesson 8) — drop it
        from shapely.geometry import Point

        clear = params.style.screw_d_mm / 2 + 1.0
        pts = [p for p in pts if avoid.distance(Point(p)) >= clear]
    return pts
