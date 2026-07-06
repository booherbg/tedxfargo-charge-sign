"""SVG -> Artwork. Filled shapes become fills (honoring each element's
fill-rule); stroked paths become tube centerlines DIRECTLY (no skeleton needed
— the best possible neon source). Text elements are skipped with a warning:
convert text to outlines in your editor (the vector is the authority)."""

from __future__ import annotations

import math

from shapely.affinity import scale as _sc
from shapely.affinity import translate as _tr
from shapely.ops import unary_union
from svgelements import SVG, Close, Line, Move, Path as SvgPath, Shape, SVGText

from ..geom2d import fill_contours, heal
from ..model import Artwork, Stroke

FLAT_MM = 0.4  # curve flattening step in source units (rescaled later anyway)


def _flatten_path(p: SvgPath) -> list[tuple[list[tuple[float, float]], bool]]:
    """[(polyline, closed)] per subpath."""
    subs: list[tuple[list[tuple[float, float]], bool]] = []
    cur: list[tuple[float, float]] = []
    closed = False
    for seg in p:
        if isinstance(seg, Move):
            if len(cur) >= 2:
                subs.append((cur, closed))
            cur = [(seg.end.x, seg.end.y)] if seg.end is not None else []
            closed = False
            continue
        if isinstance(seg, Close):
            closed = True
            if cur:
                cur.append((cur[0][0], cur[0][1]))
            continue
        if seg.start is None or seg.end is None:
            continue
        if not cur:
            cur = [(seg.start.x, seg.start.y)]
        if isinstance(seg, Line):
            cur.append((seg.end.x, seg.end.y))
        else:
            try:
                L = seg.length(error=1e-3)
            except Exception:
                L = math.dist((seg.start.x, seg.start.y), (seg.end.x, seg.end.y)) * 2
            n = max(2, min(200, int(math.ceil(L / FLAT_MM))))
            for i in range(1, n + 1):
                q = seg.point(i / n)
                cur.append((q.x, q.y))
    if len(cur) >= 2:
        subs.append((cur, closed))
    return subs


def svg_to_artwork(path: str, target_height_mm: float) -> Artwork:
    svg = SVG.parse(path, reify=True)
    fill_polys = []
    strokes: list[Stroke] = []
    notes: list[str] = []

    for el in svg.elements():
        if isinstance(el, SVGText):
            notes.append("text element skipped — convert text to outlines")
            continue
        if not isinstance(el, Shape):
            continue
        p = el if isinstance(el, SvgPath) else SvgPath(el)
        subs = _flatten_path(p)
        if not subs:
            continue
        has_fill = el.fill is not None and el.fill.value is not None
        has_stroke = el.stroke is not None and el.stroke.value is not None
        sw = float(el.stroke_width or 0) if has_stroke else 0.0

        if has_fill:
            rule_raw = str(getattr(el, "values", {}).get("fill-rule", "nonzero")).lower()
            rule = "evenodd" if rule_raw == "evenodd" else "nonzero"
            contours = [pl for pl, _closed in subs if len(pl) >= 3]
            merged = fill_contours(contours, rule=rule, min_area=1e-6)
            if not merged.is_empty:
                fill_polys.append(merged)
        elif has_stroke and sw > 0:
            for pl, closed in subs:
                pts = pl[:-1] if closed and len(pl) > 2 else pl
                strokes.append(Stroke(pts=[(x, y) for x, y in pts], width=sw, closed=closed))

    fills = heal(unary_union(fill_polys)) if fill_polys else None

    # y-flip (SVG y-down -> mm y-up), then scale to target height
    xs: list[float] = []
    ys: list[float] = []
    if fills is not None and not fills.is_empty:
        b = fills.bounds
        xs += [b[0], b[2]]
        ys += [b[1], b[3]]
    for s in strokes:
        xs += [q[0] for q in s.pts]
        ys += [q[1] for q in s.pts]
    if not xs:
        return Artwork(fills=None, strokes=[], glyphs=[], source=f"svg:{path} (empty)")
    y1 = max(ys)
    h = max(y1 - min(ys), 1e-6)
    k = target_height_mm / h
    if fills is not None and not fills.is_empty:
        flipped = _sc(fills, 1, -1, origin=(0, y1 / 2))   # y' = y1 - y (matches strokes)
        fills = heal(_sc(flipped, k, k, origin=(0, 0)))
    out_strokes = [
        Stroke(
            pts=[((x) * k, (y1 - y) * k) for x, y in s.pts],
            width=(s.width or 0) * k or None,
            closed=s.closed,
        )
        for s in strokes
    ]
    src = f"svg:{path}"
    if notes:
        src += " (" + "; ".join(sorted(set(notes))) + ")"
    return Artwork(fills=fills, strokes=out_strokes, glyphs=[], source=src)
