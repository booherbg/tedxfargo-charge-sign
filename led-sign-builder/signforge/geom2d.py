"""2D geometry: healing, stroking (bands), offsets, ring extraction.

The band construction is the shapely port of the OpenSCAD hull-chain
(src/parts/piece.scad path_stroke/band): a round-capped, round-joined buffer
of the centerline at half the tube width.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
from shapely import make_valid, unary_union
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.polygon import orient

from .model import Stroke

QUAD_SEGS = 18  # ~matches CHARGE's $fn=72 quality on full circles


def as_multipolygon(geom) -> MultiPolygon:
    if geom is None or geom.is_empty:
        return MultiPolygon([])
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, GeometryCollection):
        polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        return as_multipolygon(unary_union(polys)) if polys else MultiPolygon([])
    return MultiPolygon([])


def heal(geom, min_area: float = 0.01) -> MultiPolygon:
    """Valid, oriented (CCW shells / CW holes), sliver-free multipolygon."""
    if geom is None:
        return MultiPolygon([])
    g = make_valid(geom)
    g = as_multipolygon(g)
    if g.is_empty:
        return g
    g = as_multipolygon(unary_union(g))
    polys = []
    for p in g.geoms:
        if p.area < min_area:
            continue
        holes = [h for h in p.interiors if Polygon(h).area >= min_area]
        polys.append(orient(Polygon(p.exterior, holes), sign=1.0))
    return MultiPolygon(polys)


def band(strokes: Iterable[Stroke], width: float, min_area: float = 0.01) -> MultiPolygon:
    """Stroke centerlines into a tube band of the given width (round caps/joins)."""
    parts = []
    for s in strokes:
        pts = list(s.pts)
        if len(pts) < 2:
            parts.append(Point(pts[0]).buffer(width / 2, quad_segs=QUAD_SEGS))
            continue
        if s.closed and pts[0] != pts[-1]:
            pts = pts + [pts[0]]
        parts.append(
            LineString(pts).buffer(
                width / 2, quad_segs=QUAD_SEGS, cap_style="round", join_style="round"
            )
        )
    if not parts:
        return MultiPolygon([])
    return heal(unary_union(parts), min_area=min_area)


def ring_offset(mpoly: MultiPolygon, delta: float, min_area: float = 0.01) -> MultiPolygon:
    """Grow (+) / shrink (−) a region; round joins; healed output."""
    if mpoly.is_empty:
        return mpoly
    return heal(mpoly.buffer(delta, quad_segs=QUAD_SEGS, join_style="round"), min_area=min_area)


def rings(mpoly: MultiPolygon) -> list[np.ndarray]:
    """Contours for manifold3d.CrossSection FillRule.Positive:
    shells CCW, holes CW, no repeated closing point."""
    out: list[np.ndarray] = []
    for p in as_multipolygon(mpoly).geoms:
        p = orient(p, sign=1.0)
        out.append(np.asarray(p.exterior.coords[:-1], dtype=np.float64))
        for h in p.interiors:
            out.append(np.asarray(h.coords[:-1], dtype=np.float64))
    return out


def bbox_polygon(x0: float, y0: float, x1: float, y1: float) -> Polygon:
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def fill_contours(
    contours: Iterable[Iterable[tuple[float, float]]],
    rule: str = "nonzero",
    min_area: float = 0.01,
) -> MultiPolygon:
    """Resolve raw contours into filled polygons under a fill rule.

    Fonts use NONZERO winding (counters are opposite-oriented contours; naive
    unioning fills the 'O'); SVG may use evenodd. Clipper2 (via manifold3d's
    CrossSection) implements both exactly; output is CCW shells / CW holes.
    """
    import manifold3d as m3d

    ctrs = [np.asarray(list(c), dtype=np.float64) for c in contours]
    ctrs = [c for c in ctrs if len(c) >= 3]
    if not ctrs:
        return MultiPolygon([])
    fr = m3d.FillRule.NonZero if rule == "nonzero" else m3d.FillRule.EvenOdd
    out_rings = m3d.CrossSection(ctrs, fr).to_polygons()

    def signed_area(r: np.ndarray) -> float:
        x, y = r[:, 0], r[:, 1]
        return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

    shells: list[tuple[Polygon, float]] = []
    holes: list[np.ndarray] = []
    for r in out_rings:
        r = np.asarray(r, dtype=np.float64)
        if len(r) < 3:
            continue
        a = signed_area(r)
        if a > 0:
            shells.append((Polygon(r), a))
        elif a < 0:
            holes.append(r)

    # each hole belongs to the smallest shell containing it
    assigned: dict[int, list[np.ndarray]] = {i: [] for i in range(len(shells))}
    for h in holes:
        probe = Point(h[0])
        best, best_area = None, None
        for i, (shell, a) in enumerate(shells):
            if shell.contains(probe) and (best_area is None or a < best_area):
                best, best_area = i, a
        if best is not None:
            assigned[best].append(h)
    polys = [Polygon(shell.exterior, assigned[i]) for i, (shell, _) in enumerate(shells)]
    return heal(MultiPolygon(polys), min_area=min_area)
