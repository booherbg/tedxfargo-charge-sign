"""Per-piece body preparation: mask clipping, screw drilling, label debossing."""

from __future__ import annotations

import manifold3d as m3d

from ..geom2d import as_multipolygon, heal
from ..model import Body, Piece
from ..params import SignParams
from ..solids import cylinder, prism
from shapely.affinity import scale as _sc
from shapely.affinity import translate as _tr


def _label_solid(pc: Piece, params: SignParams) -> m3d.Manifold | None:
    """Piece label, MIRRORED, debossed into the plate back (reads right when
    the sign is face-up on the wall; lesson 27 — and show it in previews)."""
    from ..ingest.fonts import text_to_artwork

    art = text_to_artwork(None, pc.label, cap_height_mm=8.0)
    if art.fills is None or art.fills.is_empty:
        return None
    fills = art.fills
    fx0, fy0, fx1, fy1 = fills.bounds
    mx0, my0, mx1, my1 = pc.mask.bounds
    cx = (mx0 + mx1) / 2
    y = my0 + 11.0
    fills = _tr(fills, xoff=cx - (fx0 + fx1) / 2, yoff=y - fy0)
    fills = heal(_sc(fills, xfact=-1, yfact=1, origin=(cx, 0)))  # mirror for the back
    return prism(fills, -0.1, 0.6)


def _rotate_z90(man: m3d.Manifold, cx: float, cy: float) -> m3d.Manifold:
    return man.translate([-cx, -cy, 0]).rotate([0.0, 0.0, 90.0]).translate([cx, cy, 0])


def fit_flat_plate(
    man: m3d.Manifold, bed: tuple[float, float], seam: float = 0.06
) -> tuple[list[m3d.Manifold], bool, int]:
    """Make a flat plate print-ready: rotate to fit if that suffices, else
    grid-split into bed-sized panels (hairline butt joints — the CHARGE
    continuous-mode precedent). Returns (parts, rotated, n_cuts)."""
    import math

    x0, y0, _z0, x1, y1, _z1 = man.bounding_box()
    w, h = x1 - x0, y1 - y0
    bx, by = bed
    if w <= bx and h <= by:
        return [man], False, 0

    def n_parts(w_, h_):
        return math.ceil(w_ / bx) * math.ceil(h_ / by)

    rotated = False
    if n_parts(h, w) < n_parts(w, h):
        man = _rotate_z90(man, (x0 + x1) / 2, (y0 + y1) / 2)
        rotated = True
        x0, y0, _z0, x1, y1, _z1 = man.bounding_box()
        w, h = x1 - x0, y1 - y0
    if w <= bx and h <= by:
        return [man], rotated, 0

    nx = max(1, math.ceil(w / bx))
    ny = max(1, math.ceil(h / by))
    parts: list[m3d.Manifold] = []
    for j in range(ny):
        ylo = y0 + h * j / ny
        yhi = y0 + h * (j + 1) / ny
        strip = man
        if ny > 1:
            strip = strip.trim_by_plane([0, 1, 0], ylo + (seam / 2 if j else -1))
            strip = strip.trim_by_plane([0, -1, 0], -(yhi - (seam / 2 if j < ny - 1 else -1)))
        for i in range(nx):
            xlo = x0 + w * i / nx
            xhi = x0 + w * (i + 1) / nx
            part = strip
            if nx > 1:
                part = part.trim_by_plane([1, 0, 0], xlo + (seam / 2 if i else -1))
                part = part.trim_by_plane([-1, 0, 0], -(xhi - (seam / 2 if i < nx - 1 else -1)))
            if not part.is_empty():
                parts.append(part)
    return parts, rotated, nx * ny - 1


def clip_bodies_to_piece(
    bodies: list[Body], pc: Piece, params: SignParams, multi: bool, first: bool = True
) -> tuple[list[tuple[str, m3d.Manifold, int, str, str]], list[str]]:
    """Returns ([(body_name, manifold, extruder, plate, color)], notes) for one piece."""
    notes: list[str] = []
    out: list[tuple[str, m3d.Manifold, int, str, str]] = []
    clip_poly = pc.clip_mask if pc.clip_mask is not None else pc.mask
    clip = prism(as_multipolygon(clip_poly), -2.0, 800.0) if multi else None

    for body in bodies:
        man = body.man
        if body.plate != "main":
            if first:  # emit separate plates exactly once, made print-ready
                parts, rotated, cuts = fit_flat_plate(man, params.printer.bed,
                                                      params.fit.seam_clearance_mm)
                if rotated:
                    notes.append(f"{body.name}: rotated 90° to fit the bed")
                if cuts:
                    notes.append(
                        f"{body.name}: split into {len(parts)} bed-sized panels "
                        "(hairline butt joints; glue at assembly)"
                    )
                if len(parts) == 1:
                    out.append((body.name, parts[0], body.extruder, body.plate, body.color))
                else:
                    for pi_, part in enumerate(parts):
                        out.append((f"{body.name}_p{pi_ + 1}", part, body.extruder,
                                    f"{body.plate}_p{pi_ + 1}", body.color))
            continue
        if clip is not None:
            man = man ^ clip
            if man.is_empty():
                continue
        if body.name == "shell":
            if pc.screws:
                drills = [
                    cylinder(params.style.screw_d_mm, 60.0, x, y, -5.0) for x, y in pc.screws
                ]
                hole = (
                    m3d.Manifold.batch_boolean(drills, m3d.OpType.Add)
                    if len(drills) > 1
                    else drills[0]
                )
                man = man - hole
            if multi and pc.clip_mask is None:   # mirrored styles skip deboss (v1)
                lab = _label_solid(pc, params)
                if lab is not None:
                    labeled = man - lab
                    if not labeled.is_empty():
                        man = labeled
        if pc.rotated:
            # fits the bed only sideways — export it PHYSICALLY rotated so the
            # kit is print-ready as-is ('respects height but not width' report)
            rx0, ry0, rx1, ry1 = clip_poly.bounds
            man = _rotate_z90(man, (rx0 + rx1) / 2, (ry0 + ry1) / 2)
        out.append((body.name, man, body.extruder, body.plate, body.color))
    return out, notes
