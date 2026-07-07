"""Raster preview: a lit-look PNG of the sign (kit thumbnail + visual QA).

Renders in assembly view (viewer's side): backer plaque, glow halos, tube
lenses / letter faces, pixels, seams. PIL only — no GL, no browser.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from ..geom2d import as_multipolygon
from ..model import Layout, LedPlan, Piece
from ..params import SignParams

BG = (16, 16, 20)


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def render_png(
    layout: Layout,
    pieces: list[Piece],
    ledplan: LedPlan | None,
    params: SignParams,
    path: str,
    width_px: int = 1100,
) -> None:
    xs: list[float] = []
    ys: list[float] = []
    for src in ([layout.backer] if layout.backer is not None else []) + (
        [layout.fills] if layout.fills is not None and not layout.fills.is_empty else []
    ):
        b = src.bounds
        xs += [b[0], b[2]]
        ys += [b[1], b[3]]
    for s in layout.strokes:
        xs += [p[0] for p in s.pts]
        ys += [p[1] for p in s.pts]
    if not xs:
        Image.new("RGB", (200, 120), BG).save(path)
        return
    pad = 18.0
    x0, y0, x1, y1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    k = width_px / (x1 - x0)
    H = max(80, int((y1 - y0) * k))
    c = {name: _hex(v) for name, v in params.colors.preview.items()}

    def P(pt):  # mm -> px, y flipped
        return (int((pt[0] - x0) * k), int((y1 - pt[1]) * k))

    img = Image.new("RGB", (width_px, H), BG)
    draw = ImageDraw.Draw(img)

    def fill_mpoly(geom, color):
        for poly in as_multipolygon(geom).geoms:
            draw.polygon([P(q) for q in poly.exterior.coords], fill=color)
            for hole in poly.interiors:
                draw.polygon([P(q) for q in hole.coords], fill=c["shell"] if geom is layout.backer else BG)

    if layout.backer is not None:
        fill_mpoly(as_multipolygon(layout.backer), c["shell"])

    glow = Image.new("RGB", (width_px, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)

    if params.style.kind == "neon" and layout.strokes:
        w_out = max(2, int(params.style.neon.band_outer * k))
        w_in = max(1, int(params.style.neon.channel_interior * k))
        for s in layout.strokes:
            pts = [P(q) for q in (s.pts + ([s.pts[0]] if s.closed else []))]
            gd.line(pts, fill=c["lens"], width=w_in + 8, joint="curve")
        shellish = tuple(min(255, v + 24) for v in c["shell"])
        for s in layout.strokes:
            pts = [P(q) for q in (s.pts + ([s.pts[0]] if s.closed else []))]
            draw.line(pts, fill=shellish, width=w_out, joint="curve")
        for s in layout.strokes:
            pts = [P(q) for q in (s.pts + ([s.pts[0]] if s.closed else []))]
            draw.line(pts, fill=c["lens"], width=w_in, joint="curve")
    elif layout.fills is not None and not layout.fills.is_empty:
        # pre-blend: only the LIGHT goes into the glow layer
        if params.style.kind == "halo":
            for poly in as_multipolygon(layout.fills.buffer(9.0)).geoms:
                gd.polygon([P(q) for q in poly.exterior.coords], fill=c["lens"])
        else:  # channel: the lit face itself blooms
            for poly in as_multipolygon(layout.fills).geoms:
                gd.polygon([P(q) for q in poly.exterior.coords], fill=c["lens"])

    # soft glow composite
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(3, int(6 * k))))
    img = Image.blend(img, Image.composite(glow, img, glow.convert("L").point(lambda v: min(255, v * 2))), 0.35)
    draw = ImageDraw.Draw(img)

    # post-blend: crisp faces over the bloom (blend smears everything under it)
    if (
        params.style.kind in ("channel", "halo")
        and layout.fills is not None
        and not layout.fills.is_empty
    ):
        face = c["lens"] if params.style.kind == "channel" else tuple(
            min(255, v + 24) for v in c["shell"]
        )
        hole_bg = c["shell"] if layout.backer is not None else BG
        for poly in as_multipolygon(layout.fills).geoms:
            draw.polygon([P(q) for q in poly.exterior.coords], fill=face)
            for hole in poly.interiors:
                draw.polygon([P(q) for q in hole.coords], fill=hole_bg)

    if len(pieces) > 1:
        for pc in pieces:
            for poly in as_multipolygon(pc.mask).geoms:
                pts = [P(q) for q in poly.exterior.coords]
                draw.line(pts + [pts[0]], fill=c["seam"], width=1)

    # halo pixels fire backward — the viewer never sees them
    if ledplan and ledplan.pixels and params.style.kind != "halo":
        r = max(2, int(params.leds.bore_mm / 2 * k * 0.7))
        for q in ledplan.pixels:
            cx, cy = P(q)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c["pixel"])

    img.save(path)
