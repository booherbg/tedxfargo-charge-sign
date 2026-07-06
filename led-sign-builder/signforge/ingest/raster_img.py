"""PNG/JPG logo tracing: threshold + marching squares -> healed fills.

Dark pixels are ink by default (trace_invert flips). Sub-pixel accuracy via
edge-midpoint contours, then Douglas-Peucker simplification in shapely."""

from __future__ import annotations

import numpy as np
from PIL import Image
from shapely.affinity import scale as _sc

from ..geom2d import fill_contours, heal
from ..model import Artwork

# marching-squares segment table: case -> list of (edge_in, edge_out)
# edges: 0=top, 1=right, 2=bottom, 3=left (of the 2x2 cell), walking so ink
# stays on the LEFT gives consistently oriented loops
_SEGS = {
    1: [(3, 2)], 2: [(2, 1)], 3: [(3, 1)], 4: [(1, 0)], 5: [(1, 2), (3, 0)],
    6: [(2, 0)], 7: [(3, 0)], 8: [(0, 3)], 9: [(0, 2)], 10: [(0, 1), (2, 3)],
    11: [(0, 1)], 12: [(1, 3)], 13: [(1, 2)], 14: [(2, 3)],
}
_EDGE_MID = {0: (0.5, 0.0), 1: (1.0, 0.5), 2: (0.5, 1.0), 3: (0.0, 0.5)}


def _trace(ink: np.ndarray) -> list[list[tuple[float, float]]]:
    """Marching squares over a padded binary image -> closed loops (px coords)."""
    b = np.pad(ink, 1).astype(np.int8)
    case = b[:-1, :-1] * 8 + b[:-1, 1:] * 4 + b[1:, 1:] * 2 + b[1:, :-1] * 1
    segs: dict[tuple[float, float], tuple[float, float]] = {}
    ys, xs = np.nonzero((case > 0) & (case < 15))
    for j, i in zip(ys.tolist(), xs.tolist()):
        for e_in, e_out in _SEGS[case[j, i]]:
            a = (i + _EDGE_MID[e_in][0], j + _EDGE_MID[e_in][1])
            bpt = (i + _EDGE_MID[e_out][0], j + _EDGE_MID[e_out][1])
            segs[a] = bpt
    loops = []
    while segs:
        start, cur = next(iter(segs.items()))
        loop = [start]
        while True:
            nxt = segs.pop(loop[-1], None)
            if nxt is None or nxt == start:
                break
            loop.append(nxt)
        if len(loop) >= 3:
            loops.append(loop)
    return loops


def raster_to_artwork(
    path: str, target_height_mm: float, threshold: int = 128, invert: bool = False
) -> Artwork:
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "PA"):
        # composite onto white so transparency reads as background
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img.convert("RGBA"))
    g = np.asarray(img.convert("L"), dtype=np.uint8)
    ink = (g < threshold) ^ invert
    if not ink.any():
        return Artwork(fills=None, strokes=[], glyphs=[], source=f"raster:{path} (no ink)")

    loops = _trace(ink)
    fills = fill_contours(loops, rule="evenodd", min_area=4.0)
    if fills.is_empty:
        return Artwork(fills=None, strokes=[], glyphs=[], source=f"raster:{path} (no ink)")
    fills = heal(fills.simplify(0.75))

    x0, y0, x1, y1 = fills.bounds
    k = target_height_mm / max(y1 - y0, 1e-6)
    fills = heal(_sc(_sc(fills, 1, -1, origin=(0, (y0 + y1) / 2)), k, k, origin=(0, 0)))
    return Artwork(fills=fills, strokes=[], glyphs=[], source=f"raster:{path}")
