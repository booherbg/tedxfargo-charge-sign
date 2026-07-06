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


def clip_bodies_to_piece(
    bodies: list[Body], pc: Piece, params: SignParams, multi: bool
) -> tuple[list[tuple[str, m3d.Manifold, int, str]], list[str]]:
    """Returns ([(body_name, manifold, extruder, plate)], notes) for one piece."""
    notes: list[str] = []
    out: list[tuple[str, m3d.Manifold, int, str]] = []
    clip = prism(as_multipolygon(pc.mask), -2.0, 800.0) if multi else None

    for body in bodies:
        man = body.man
        if body.plate != "main":
            if multi:
                notes.append(
                    f"{body.name}: press-fit part is not panelized (v1) — exported whole; "
                    "split manually if it exceeds the bed"
                )
            if pc.name == "piece1":  # emit un-panelized plates exactly once
                out.append((body.name, man, body.extruder, body.plate))
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
            if multi:
                lab = _label_solid(pc, params)
                if lab is not None:
                    labeled = man - lab
                    if not labeled.is_empty():
                        man = labeled
        out.append((body.name, man, body.extruder, body.plate))
    return out, notes
