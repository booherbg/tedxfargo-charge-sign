"""Internal support ribs for weak-bridging printers.

Thin transverse walls inside the neon channel, floor to lens underside, so
the lens never bridges more than rib_spacing unsupported. PERMANENT by
design: removable supports inside a sealed cavity are unprintable spaghetti
(CHARGE optics-matrix lesson) — these are engineered-in, white (reflective),
and sit clear of every pixel.
"""

from __future__ import annotations

import math

from shapely.geometry import MultiPolygon, Polygon

from ..geom2d import as_multipolygon, heal
from ..model import Point2, Stroke
from ..skeleton import resample


def support_ribs(
    strokes: list[Stroke],
    b_in: MultiPolygon,
    pixels: list[Point2],
    spacing: float = 28.0,
    rib_t: float = 0.9,
    span: float = 20.0,
    pixel_keepout: float = 7.0,   # led_void/2: the bullet insertion envelope
) -> list[MultiPolygon]:
    ribs: list[MultiPolygon] = []
    half = span / 2 + 2.0          # overshoot; clipped back to the channel
    for s in strokes:
        pts = s.pts + ([s.pts[0]] if s.closed else [])
        if len(pts) < 2:
            continue
        L = s.length()
        n = max(1, round(L / spacing))
        positions = resample(pts if s.closed else s.pts, L / n, s.closed)
        if not s.closed and len(positions) > 2:
            positions = positions[1:-1]        # end caps don't need ribs
        for p in positions:
            near = sorted(pixels, key=lambda q: math.dist(p, q))[:2]
            if near and math.dist(p, near[0]) < pixel_keepout:
                # pixels are pitched tighter than 2×keepout — the only legal
                # rib home is the midpoint between the two nearest pixels
                # (insertion envelope radius = led_void/2 = 7 mm)
                if len(near) < 2 or math.dist(near[0], near[1]) > 2.4 * pixel_keepout + 10:
                    continue
                p = ((near[0][0] + near[1][0]) / 2, (near[0][1] + near[1][1]) / 2)
                if math.dist(p, near[0]) < pixel_keepout:
                    continue
            # local tangent: nearest segment direction
            best, tang = 1e18, (1.0, 0.0)
            for a, b in zip(pts, pts[1:]):
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                d = (mx - p[0]) ** 2 + (my - p[1]) ** 2
                if d < best:
                    seg = math.dist(a, b) or 1.0
                    best, tang = d, ((b[0] - a[0]) / seg, (b[1] - a[1]) / seg)
            px, py = -tang[1], tang[0]         # perpendicular
            tx, ty = tang
            hw = rib_t / 2
            rect = Polygon(
                [
                    (p[0] - px * half - tx * hw, p[1] - py * half - ty * hw),
                    (p[0] + px * half - tx * hw, p[1] + py * half - ty * hw),
                    (p[0] + px * half + tx * hw, p[1] + py * half + ty * hw),
                    (p[0] - px * half + tx * hw, p[1] - py * half + ty * hw),
                ]
            )
            clipped = heal(as_multipolygon(rect.intersection(b_in)))
            if not clipped.is_empty and clipped.area > rib_t * 4:
                ribs.append(clipped)
    return ribs
