"""Shared part-building helpers."""

from __future__ import annotations

import manifold3d as m3d
from shapely.geometry import MultiPolygon, Polygon

from ..geom2d import as_multipolygon, heal
from ..solids import CIRCLE_SEGS, cylinder, revolve_profile


def filled(mpoly: MultiPolygon) -> MultiPolygon:
    """Fill all holes (counters become enclosed dead space — nothing floats)."""
    return heal(MultiPolygon([Polygon(p.exterior) for p in as_multipolygon(mpoly).geoms]))


def bore_stack(pixels, d: float, z0: float, z1: float) -> m3d.Manifold | None:
    """Union of vertical bores for subtracting pixel holes."""
    if not pixels:
        return None
    mans = [cylinder(d, z1 - z0, x, y, z0) for (x, y) in pixels]
    return m3d.Manifold.batch_boolean(mans, m3d.OpType.Add) if len(mans) > 1 else mans[0]


def collar(cx: float, cy: float, z0: float, od: float = 16.0, h: float = 2.0) -> m3d.Manifold:
    """Press-fit bullet-pixel collar (CHARGE-calibrated): bore Ø12.19 with
    0.5 mm 45° lead-ins at both faces (collar_v2 recipe)."""
    bore_face_r = 6.10
    chamfer = 0.5
    mouth_r = bore_face_r + chamfer
    profile = [
        (mouth_r, 0.0),
        (od / 2, 0.0),
        (od / 2, h),
        (mouth_r, h),
        (bore_face_r, h - chamfer),
        (bore_face_r, chamfer),
    ]
    return revolve_profile(profile, cx, cy, z0)


def union_all(mans: list[m3d.Manifold]) -> m3d.Manifold:
    mans = [m for m in mans if m is not None and not m.is_empty()]
    if not mans:
        raise ValueError("union_all: nothing to union")
    if len(mans) == 1:
        return mans[0]
    return m3d.Manifold.batch_boolean(mans, m3d.OpType.Add)
