"""DXF -> Artwork. Closed entities become fills (even-odd nesting = holes);
open chains become tube centerlines. Uses ezdxf's path add-on so LWPOLYLINE
bulges, SPLINE, ARC, CIRCLE, and ELLIPSE all flatten uniformly."""

from __future__ import annotations

import ezdxf
from ezdxf import path as ezpath
from shapely.affinity import scale as _sc
from shapely.ops import unary_union

from ..geom2d import fill_contours, heal
from ..model import Artwork, Stroke

FLATTEN = 0.2  # max sagitta in drawing units
SUPPORTED = {"LWPOLYLINE", "POLYLINE", "LINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE"}


def dxf_to_artwork(path: str, target_height_mm: float) -> Artwork:
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    closed_contours: list[list[tuple[float, float]]] = []
    open_lines: list[list[tuple[float, float]]] = []
    skipped: set[str] = set()

    for e in msp:
        t = e.dxftype()
        if t not in SUPPORTED:
            skipped.add(t)
            continue
        try:
            p = ezpath.make_path(e)
        except Exception:
            skipped.add(t)
            continue
        pts = [(v.x, v.y) for v in p.flattening(FLATTEN)]
        if len(pts) < 2:
            continue
        is_closed = p.is_closed or (
            len(pts) > 3
            and abs(pts[0][0] - pts[-1][0]) < 1e-6
            and abs(pts[0][1] - pts[-1][1]) < 1e-6
        )
        if is_closed and len(pts) >= 4:
            closed_contours.append(pts)
        else:
            open_lines.append(pts)

    fills = None
    if closed_contours:
        fills = fill_contours(closed_contours, rule="evenodd", min_area=1e-9)
    strokes = [Stroke(pts=pl, width=None, closed=False) for pl in open_lines]

    ys = []
    if fills is not None and not fills.is_empty:
        ys += [fills.bounds[1], fills.bounds[3]]
    for s in strokes:
        ys += [q[1] for q in s.pts]
    if not ys:
        return Artwork(fills=None, strokes=[], glyphs=[], source=f"dxf:{path} (empty)")
    k = target_height_mm / max(max(ys) - min(ys), 1e-6)
    if fills is not None and not fills.is_empty:
        fills = heal(_sc(fills, k, k, origin=(0, 0)))
    strokes = [
        Stroke(pts=[(x * k, y * k) for x, y in s.pts], width=None, closed=s.closed)
        for s in strokes
    ]
    src = f"dxf:{path}"
    if skipped:
        src += f" (skipped: {sorted(skipped)})"
    return Artwork(fills=fills if fills is not None else None, strokes=strokes, glyphs=[], source=src)
