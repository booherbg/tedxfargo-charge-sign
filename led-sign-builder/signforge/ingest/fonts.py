"""Text + font file -> Artwork (healed glyph outlines in mm).

Supports TTF/OTF/WOFF/WOFF2 (fontTools). Kerning: 'kern' table format-0 pairs
when present (GPOS pair positioning is out of scope v1 — tracked in README).
Curves are flattened adaptively to ~0.25 mm chords at final scale.
"""

from __future__ import annotations

import io
import math
from importlib import resources
from pathlib import Path
from typing import Optional

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from shapely.affinity import scale as _sc
from shapely.affinity import translate as _tr
from shapely.geometry import MultiPolygon
from shapely.ops import unary_union

from ..geom2d import fill_contours, heal
from ..model import Artwork, GlyphBox

FLAT_MM = 0.25  # max chord length when flattening curves, in mm at final scale


def default_font_path() -> str:
    return str(resources.files("signforge") / "assets" / "fonts" / "Bungee-Regular.ttf")


class _FlatPen(BasePen):
    """Records flattened closed contours in font units."""

    def __init__(self, glyph_set, flat_units: float):
        super().__init__(glyph_set)
        self.flat = max(flat_units, 1.0)
        self.contours: list[list[tuple[float, float]]] = []
        self._cur: list[tuple[float, float]] = []

    def _moveTo(self, p):
        if len(self._cur) >= 3:
            self.contours.append(self._cur)
        self._cur = [p]

    def _lineTo(self, p):
        self._cur.append(p)

    def _curve(self, pts):
        p0 = self._cur[-1]
        ctrl = [p0, *pts]
        length = sum(math.dist(a, b) for a, b in zip(ctrl, ctrl[1:]))
        n = min(64, max(2, int(math.ceil(length / self.flat))))
        if len(pts) == 3:  # cubic
            c1, c2, p3 = pts
            for i in range(1, n + 1):
                t = i / n
                mt = 1 - t
                self._cur.append(
                    (
                        mt**3 * p0[0] + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * p3[0],
                        mt**3 * p0[1] + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * p3[1],
                    )
                )
        else:  # quadratic (single segment from BasePen)
            c, p2 = pts
            for i in range(1, n + 1):
                t = i / n
                mt = 1 - t
                self._cur.append(
                    (
                        mt**2 * p0[0] + 2 * mt * t * c[0] + t**2 * p2[0],
                        mt**2 * p0[1] + 2 * mt * t * c[1] + t**2 * p2[1],
                    )
                )

    def _curveToOne(self, c1, c2, p3):
        self._curve([c1, c2, p3])

    def _qCurveToOne(self, c, p2):
        self._curve([c, p2])

    def _closePath(self):
        if len(self._cur) >= 3:
            self.contours.append(self._cur)
        self._cur = []

    def _endPath(self):
        self._closePath()


def load_font(source: str | bytes | Path) -> TTFont:
    if isinstance(source, bytes):
        return TTFont(io.BytesIO(source), fontNumber=0)
    return TTFont(str(source), fontNumber=0)


def _cap_height_units(font: TTFont, cmap: dict) -> float:
    try:
        cap = font["OS/2"].sCapHeight
        if cap and cap > 0:
            return float(cap)
    except (KeyError, AttributeError):
        pass
    glyph_set = font.getGlyphSet()
    for probe in ("H", "X", "E", "0"):
        gname = cmap.get(ord(probe))
        if gname:
            pen = _FlatPen(glyph_set, 8.0)
            glyph_set[gname].draw(pen)
            ys = [p[1] for c in pen.contours for p in c]
            if ys:
                return max(ys) - min(ys)
    return float(font["hhea"].ascent)


def _kern_pairs(font: TTFont) -> dict[tuple[str, str], float]:
    pairs: dict[tuple[str, str], float] = {}
    if "kern" not in font:
        return pairs
    try:
        for st in font["kern"].kernTables:
            table = getattr(st, "kernTable", None)
            if table:
                pairs.update(table)
    except Exception:
        pass
    return pairs


def text_to_artwork(
    font_source: str | bytes | Path | None,
    text: str,
    cap_height_mm: float,
    letter_spacing_mm: float = 0.0,
    line_spacing: float = 1.2,
    align: str = "center",
) -> Artwork:
    font = load_font(font_source or default_font_path())
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()
    upm = font["head"].unitsPerEm
    cap_units = _cap_height_units(font, cmap)
    scale = cap_height_mm / cap_units
    kern = _kern_pairs(font)
    flat_units = FLAT_MM / scale

    lines = text.split("\n")
    all_glyphs: list[GlyphBox] = []
    line_geoms: list[tuple[list[tuple[str, MultiPolygon]], float]] = []
    missing: set[str] = set()

    for line in lines:
        pen_x = 0.0
        placed: list[tuple[str, MultiPolygon]] = []
        prev_gname: Optional[str] = None
        for ch in line:
            gname = cmap.get(ord(ch))
            if gname is None:
                if not ch.isspace():
                    missing.add(ch)
                pen_x += 0.5 * upm  # missing glyph: half-em advance
                prev_gname = None
                continue
            if prev_gname is not None:
                pen_x += kern.get((prev_gname, gname), 0.0)
            pen = _FlatPen(glyph_set, flat_units)
            glyph_set[gname].draw(pen)
            if pen.contours:
                merged = fill_contours(pen.contours, rule="nonzero", min_area=0.5)
                if not merged.is_empty:
                    placed.append((ch, heal(_tr(merged, xoff=pen_x))))
            pen_x += glyph_set[gname].width + letter_spacing_mm / scale
            prev_gname = gname
        if placed:
            ix0 = min(g.bounds[0] for _, g in placed)
            ix1 = max(g.bounds[2] for _, g in placed)
        else:
            ix0 = ix1 = 0.0
        line_geoms.append((placed, ix0, ix1))

    # align by INK bounds (this is a physical sign, not typesetting)
    max_w = max((x1 - x0 for _, x0, x1 in line_geoms), default=0.0)
    fills_parts = []
    for i, (placed, ix0, ix1) in enumerate(line_geoms):
        lw = ix1 - ix0
        dx = {
            "left": -ix0,
            "center": (max_w - lw) / 2 - ix0,
            "right": max_w - lw - ix0,
        }[align]
        dy = -i * (cap_height_mm / scale) * line_spacing
        for ch, geom in placed:
            g = _tr(geom, xoff=dx, yoff=dy)
            g_mm = _sc(g, xfact=scale, yfact=scale, origin=(0, 0))
            g_mm = heal(g_mm)
            if g_mm.is_empty:
                continue
            all_glyphs.append(GlyphBox(char=ch, fills=g_mm, bbox=g_mm.bounds))
            fills_parts.append(g_mm)

    fills = heal(unary_union(fills_parts)) if fills_parts else MultiPolygon([])
    art = Artwork(fills=fills, strokes=[], glyphs=all_glyphs, source=f"text:{text!r}")
    if missing:
        art.source += f" (missing glyphs: {sorted(missing)})"
    return art
