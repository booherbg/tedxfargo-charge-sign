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
from dataclasses import dataclass

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import split as shapely_split
from shapely.ops import unary_union

from .geom2d import as_multipolygon, bbox_polygon, heal
from .model import Piece, Point2, Stroke
from .params import SignParams

CUT_GRID_MM = 5.0
EDGE_KEEPOUT_MM = 40.0   # don't cut within this of a region edge
CRISP_MIN_DEG = 25.0


@dataclass
class _Region:
    poly: Polygon

    @property
    def bounds(self):
        return self.poly.bounds

    @property
    def w(self) -> float:
        b = self.bounds
        return b[2] - b[0]

    @property
    def h(self) -> float:
        b = self.bounds
        return b[3] - b[1]


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
) -> tuple[str, float, int] | None:
    """Best straight cut: (axis, coordinate, n_tube_crossings)."""
    rx0, ry0, rx1, ry1 = region.bounds
    axis = "x" if region.w >= region.h else "y"
    lo = (rx0 if axis == "x" else ry0) + EDGE_KEEPOUT_MM
    hi = (rx1 if axis == "x" else ry1) - EDGE_KEEPOUT_MM
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
    return axis, best[1], best[0][0]


def _seam_line(region: _Region, axis: str, c: float) -> LineString:
    rx0, ry0, rx1, ry1 = region.bounds
    if axis == "x":
        return LineString([(c, ry0 - 5), (c, ry1 + 5)])
    return LineString([(rx0 - 5, c), (rx1 + 5, c)])


def _split_region(r: _Region, seam: LineString) -> list[_Region]:
    parts = shapely_split(r.poly, seam)
    out = [
        _Region(heal(g).geoms[0] if len(heal(g).geoms) == 1 else g)
        for g in parts.geoms
        if isinstance(g, Polygon) and g.area > 25.0
    ]
    return out


def panelize(
    footprint: Polygon,
    strokes: list[Stroke],
    pixels: list[Point2],
    params: SignParams,
    avoid=None,
) -> tuple[list[Piece], list[LineString], list[str]]:
    """Split the sign footprint into bed-fitting pieces.

    Straight cuts where the dark field allows; when every straight candidate
    would cross a tube, a corridor seam is routed through the field between
    channels (lesson 17 — piecewise seams on real artwork). Returns
    (pieces, seam_lines, warnings); call BEFORE pixel placement and feed
    seam_lines to leds.place_pixels(seams=...)."""
    warnings: list[str] = []
    bed = params.printer.bed
    regions: list[_Region] = []
    seams: list[LineString] = []
    fp = heal(footprint if not hasattr(footprint, "geoms") else footprint)
    start_poly = fp.geoms[0] if len(fp.geoms) == 1 else fp.convex_hull
    queue = [_Region(start_poly)]
    while queue:
        r = queue.pop(0)
        fits, _rot = _fits(r.w, r.h, bed)
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
        axis, c, crossings = cut
        seam = _seam_line(r, axis, c)
        if crossings > 0 and avoid is not None and not avoid.is_empty:
            # a zero-crossing corridor beats any straight cut through a tube;
            # search the full legal span — the dark snake may be far from c
            from .corridors import route_corridor

            rx0, ry0, rx1, ry1 = r.bounds
            lo = (rx0 if axis == "x" else ry0) + EDGE_KEEPOUT_MM
            hi = (rx1 if axis == "x" else ry1) - EDGE_KEEPOUT_MM
            corridor_pts = route_corridor(r.bounds, avoid, axis, (lo, hi))
            if corridor_pts:
                seam = LineString(corridor_pts)
                warnings.append(
                    f"corridor seam routed through the dark field "
                    f"(straight cut would cross {crossings} tube(s))"
                )
        children = _split_region(r, seam)
        if len(children) < 2:
            regions.append(r)
            warnings.append(
                f"seam near {axis}={c:.0f} failed to split the region — exported oversized"
            )
            continue
        seams.append(seam)
        queue.extend(children)

    regions.sort(key=lambda r: (round(r.bounds[1]), round(r.bounds[0])))
    sc = params.fit.seam_clearance_mm
    seam_relief = unary_union([s.buffer(sc) for s in seams]) if seams else None
    pieces: list[Piece] = []
    for i, r in enumerate(regions):
        mask_geom = r.poly if seam_relief is None else r.poly.difference(seam_relief)
        mask_mp = as_multipolygon(mask_geom)
        mask = max(mask_mp.geoms, key=lambda g: g.area) if len(mask_mp.geoms) else r.poly
        _, rotated = _fits(r.w, r.h, bed)
        pieces.append(
            Piece(
                name=f"piece{i + 1}",
                label=f"P{i + 1}",
                mask=mask,
                rotated=rotated,
                screws=_screws(r, params, avoid),
                pixel_idx=[],
            )
        )
    return pieces, seams, warnings


def assign_pixels(pieces: list[Piece], pixels: list[Point2]) -> None:
    """Assign each pixel to exactly one piece (covering mask wins; bounds fallback)."""
    for pc in pieces:
        pc.pixel_idx = []
    taken: set[int] = set()
    for k, p in enumerate(pixels):
        pt = Point(p)
        home = None
        for pc in pieces:
            if pc.mask.buffer(0.5).covers(pt):
                home = pc
                break
        if home is None:
            for pc in pieces:
                x0, y0, x1, y1 = pc.mask.bounds
                if x0 - 0.5 <= p[0] <= x1 + 0.5 and y0 - 0.5 <= p[1] <= y1 + 0.5:
                    home = pc
                    break
        if home is not None and k not in taken:
            home.pixel_idx.append(k)
            taken.add(k)


def _screws(r: _Region, params: SignParams, avoid=None) -> list[Point2]:
    if not params.style.screw_holes or params.style.backer == "none":
        return []
    rx0, ry0, rx1, ry1 = r.bounds
    inset = params.style.screw_inset_mm
    xs = [rx0 + inset, rx1 - inset]
    ys = [ry0 + inset, ry1 - inset]
    if xs[1] <= xs[0] or ys[1] <= ys[0]:
        return []
    pts = [(x, y) for x in xs for y in ys]
    span = params.style.screw_midspan_mm
    if r.w > span:
        pts += [((rx0 + rx1) / 2, ys[0]), ((rx0 + rx1) / 2, ys[1])]
    if r.h > span:
        pts += [(xs[0], (ry0 + ry1) / 2), (xs[1], (ry0 + ry1) / 2)]
    # stay on this piece and out of lit channels (light-leak law)
    pts = [p for p in pts if r.poly.buffer(0.5).covers(Point(p))]
    if avoid is not None and not avoid.is_empty:
        clear = params.style.screw_d_mm / 2 + 1.0
        pts = [p for p in pts if avoid.distance(Point(p)) >= clear]
    return pts
