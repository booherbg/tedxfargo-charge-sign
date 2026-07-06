"""Place artwork in sign coordinates and decide the backer footprint."""

from __future__ import annotations

from shapely.affinity import translate

from .geom2d import bbox_polygon, heal, ring_offset
from .model import Artwork, GlyphBox, Layout, Stroke
from .params import SignParams


def build_layout(art: Artwork, params: SignParams) -> Layout:
    x0, y0, x1, y1 = art.bbox()

    fills = None
    if art.fills is not None and not art.fills.is_empty:
        fills = heal(translate(art.fills, xoff=-x0, yoff=-y0))
    strokes = [
        Stroke(pts=[(p[0] - x0, p[1] - y0) for p in s.pts], width=s.width, closed=s.closed)
        for s in art.strokes
    ]
    glyphs = [
        GlyphBox(
            char=g.char,
            fills=heal(translate(g.fills, xoff=-x0, yoff=-y0)),
            bbox=(g.bbox[0] - x0, g.bbox[1] - y0, g.bbox[2] - x0, g.bbox[3] - y0),
        )
        for g in art.glyphs
    ]
    w, h = x1 - x0, y1 - y0

    backer = None
    if params.style.backer == "tile":
        from .plaques import plaque

        backer = plaque(
            params.style.backer_shape,
            (0, 0, w, h),
            params.style.tile_margin_mm,
            corner_radius=params.style.plaque_corner_radius_mm,
            rays=params.style.plaque_rays,
        )
    elif params.style.backer == "contour" and fills is not None:
        contour = ring_offset(fills, params.style.contour_margin_mm)
        if len(contour.geoms) == 1:
            backer = contour.geoms[0]
        elif len(contour.geoms) > 1:
            # keep disconnected islands joined via their convex bridge later;
            # v1: grow until connected or fall back to tile-style hull
            hull = contour.convex_hull
            backer = hull

    return Layout(fills=fills, strokes=strokes, glyphs=glyphs, backer=backer, bbox=(0, 0, w, h))
