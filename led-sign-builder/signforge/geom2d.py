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
