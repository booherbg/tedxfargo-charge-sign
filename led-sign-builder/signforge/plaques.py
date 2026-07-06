"""Backer plaque shape catalog — the sign silhouette behind the letters.

Every shape function takes the CONTENT bounds (art bbox, mm) plus the tile
margin and returns a Polygon guaranteed to contain that content. Shapes are
built with shapely primitives (buffer/union), so they inherit healing and
work everywhere a rectangular tile worked (panelize, screws, textures).
"""

from __future__ import annotations

import math

from shapely.affinity import scale as _sc
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from .geom2d import heal

SHAPES = ("rect", "rounded", "oval", "shield", "starburst", "scallop")


def plaque(
    shape: str,
    bounds: tuple[float, float, float, float],
    margin: float,
    corner_radius: float = 12.0,
    rays: int = 16,
) -> Polygon:
    x0, y0, x1, y1 = bounds
    x0, y0, x1, y1 = x0 - margin, y0 - margin, x1 + margin, y1 + margin
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    if shape == "rect":
        return box(x0, y0, x1, y1)

    if shape == "rounded":
        r = min(corner_radius, w / 2 - 1, h / 2 - 1)
        return box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=12)

    if shape == "oval":
        # ellipse through the rect's corners (k = √2 covers them exactly)
        k = math.sqrt(2.0)
        return _sc(Point(cx, cy).buffer(1.0, quad_segs=48), w / 2 * k, h / 2 * k, origin=(cx, cy))

    if shape == "shield":
        # flat top, straight sides past the content, rounded point below —
        # sides stay at x0/x1 for the full content height so corners are covered
        drop = 0.5 * h
        pts = [
            (x0, y1), (x1, y1),                       # top edge
            (x1, y0),                                 # full-height side
            (cx + w * 0.22, y0 - drop * 0.6),
            (cx, y0 - drop),                          # bottom point
            (cx - w * 0.22, y0 - drop * 0.6),
            (x0, y0),
        ]
        r = min(corner_radius, w / 6, h / 6)
        return Polygon(pts).buffer(r, quad_segs=10).buffer(-r, quad_segs=10).buffer(
            r / 2, quad_segs=10
        )

    if shape == "starburst":
        # atomic-age starburst: spikes on an ellipse, content on the inner radius
        n = max(8, rays)
        rx_in = w / 2 * math.sqrt(2.0)                # inner ellipse covers corners
        ry_in = h / 2 * math.sqrt(2.0)
        pts = []
        for i in range(2 * n):
            a = math.pi * i / n
            k = 1.28 if i % 2 == 0 else 1.0
            pts.append((cx + rx_in * k * math.cos(a), cy + ry_in * k * math.sin(a)))
        return Polygon(pts)

    if shape == "scallop":
        base = box(x0, y0, x1, y1)
        r = max(8.0, min(w, h) / 10)
        bumps = []
        for edge, horiz in (((x0, x1, y1), True), ((x0, x1, y0), True)):
            lo, hi, c = edge
            n = max(2, int((hi - lo) / (2.2 * r)))
            for i in range(n + 1):
                bumps.append(Point(lo + (hi - lo) * i / n, c).buffer(r, quad_segs=10))
        for c in (x0, x1):
            n = max(1, int(h / (2.2 * r)))
            for i in range(n + 1):
                bumps.append(Point(c, y0 + h * i / n).buffer(r, quad_segs=10))
        merged = heal(base.union(unary_union(bumps)))
        return max(merged.geoms, key=lambda g: g.area)

    raise ValueError(f"unknown plaque shape {shape!r}; known: {SHAPES}")
