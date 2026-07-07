"""Halo/backlit style: opaque face toward the viewer, pixels firing backward
at the wall, glow spilling around the letter silhouette.

Print orientation: FACE DOWN (glass-smooth face off the bed, everything else
grows upward — no supports). The part flips to install, so all bodies are
PRE-MIRRORED (flip = mirror, lesson 2). Interior surfaces are white (the
liner body): every photon that bounces forward gets recycled backward.

Geometry (print coords, z=0 is the face front):
  face   z 0..face_t                         (letter WITH counters — holes stay holes)
  walls  z face_t-fuse .. face_t+depth       (perimeter + counter boundaries)
  flange z top-flange_t .. top               (inner ring; carries pixel bores+collars)
  bosses standoffs past the flange, bored for wall anchors
  diffuser (optional, separate clear part): drop-in rear disc seated on the flange
"""

from __future__ import annotations

import math

from shapely.geometry import MultiPolygon

from ..geom2d import as_multipolygon, heal, ring_offset
from ..model import Body, Layout, Point2, Stroke
from ..params import SignParams
from ..solids import cylinder, prism
from ..verify import BuildError
from .common import bore_stack, collar, filled, union_all


def halo_footprint(layout: Layout, params: SignParams) -> MultiPolygon:
    return filled(layout.fills)


def halo_pixel_strokes(layout: Layout, params: SignParams) -> list[Stroke]:
    """Pixel runs on the rear flange.

    Wide letters: a closed racetrack along the flange centerline. Narrow
    letters (flange fills the whole cavity — opposing racetrack sides would
    sit closer than the pixel floor): collapse to the cavity's skeleton
    centerline instead, like a neon run."""
    st = params.style.halo
    cavity = ring_offset(layout.fills, -st.wall_t)
    strokes: list[Stroke] = []
    for comp in as_multipolygon(cavity).geoms:
        from shapely.geometry import MultiPolygon as _MP

        inner = comp.buffer(-st.flange_w)
        if inner.is_empty or inner.area < 4.0:
            from ..skeleton import extract_centerlines

            subs, _meta = extract_centerlines(_MP([comp]))
            strokes += subs
            continue
        ring = ring_offset(_MP([comp]), -st.flange_w / 2)
        for p in as_multipolygon(ring).geoms:
            for boundary in [p.exterior, *p.interiors]:
                pts = [(x, y) for x, y in boundary.coords[:-1]]
                if len(pts) >= 3:
                    strokes.append(Stroke(pts=pts, width=None, closed=True))
    return strokes


def _standoff_points(layout: Layout, params: SignParams) -> list[Point2]:
    """3-4 anchor points spread around the flange centerline."""
    st = params.style.halo
    ring = ring_offset(layout.fills, -(st.wall_t + st.flange_w / 2))
    pts: list[Point2] = []
    for p in as_multipolygon(ring).geoms:
        coords = list(p.exterior.coords[:-1])
        if len(coords) < 4:
            continue
        for pick in (
            max(coords, key=lambda q: q[0]),
            min(coords, key=lambda q: q[0]),
            max(coords, key=lambda q: q[1]),
        ):
            if all(math.dist(pick, e) > st.standoff_d * 1.5 for e in pts):
                pts.append((pick[0], pick[1]))
    return pts


def build_halo_bodies(
    layout: Layout, pixels: list, params: SignParams
) -> tuple[list[Body], MultiPolygon]:
    if layout.fills is None or layout.fills.is_empty:
        raise BuildError("halo style needs filled artwork (text or filled vectors)")
    st = params.style.halo
    fuse = params.fit.fuse_mm
    ex = params.colors.extruders
    colors = params.colors.preview

    F = layout.fills
    top = st.face_t + st.depth
    cavity = ring_offset(F, -st.wall_t)
    if cavity.is_empty:
        raise BuildError(
            f"halo: letters too small for wall_t={st.wall_t}; increase cap height"
        )
    flange = heal(cavity.difference(ring_offset(cavity, -st.flange_w)))
    if flange.is_empty:
        raise BuildError("halo: flange vanished — reduce flange_w or enlarge letters")

    standoffs = _standoff_points(layout, params)

    # ---- shell (opaque): face + walls + standoff bosses ----------------------
    face = prism(F, 0, st.face_t)
    walls = prism(heal(F.difference(cavity)), st.face_t - fuse, top)
    shell_parts = [face, walls]
    for sx, sy in standoffs:
        shell_parts.append(cylinder(st.standoff_d, st.flange_t + st.standoff_len + fuse, sx, sy, top - st.flange_t - fuse))
    shell = union_all(shell_parts)
    if standoffs:
        drills = [
            cylinder(st.standoff_bore, st.flange_t + st.standoff_len + 4, sx, sy, top - st.flange_t - 2)
            for sx, sy in standoffs
        ]
        shell = shell - union_all(drills)
    bodies = [Body("shell", shell, ex["shell"], colors["shell"])]

    # ---- liner (white): rear flange w/ pixel bores + collars -----------------
    flange_solid = prism(flange, top - st.flange_t, top)
    bores = bore_stack(pixels, params.leds.bore_mm, top - st.flange_t - 0.2, top + 0.2)
    if bores is not None:
        flange_solid = flange_solid - bores
    liner_parts = [flange_solid]
    if params.leds.collar and pixels:
        liner_parts += [
            collar(x, y, top - params.leds.collar_h_mm, params.leds.collar_od_mm, params.leds.collar_h_mm)
            for (x, y) in pixels
        ]
    bodies.append(Body("liner", union_all(liner_parts), ex["liner"], colors["liner"]))

    # ---- optional rear diffuser (separate clear drop-in) ---------------------
    if st.back_mode == "diffuser":
        seat = ring_offset(cavity, -st.flange_w / 2)
        if not seat.is_empty:
            disc = prism(seat, 0, st.diffuser_t)  # its own print coords, flat
            bodies.append(Body("lens", disc, ex["lens"], colors["lens"], plate="lens"))

    # ---- mounting plaque (backer tile/contour): the board the letter floats on
    # UNMIRRORED — it sits behind the flipped letter, so viewer-space anchor
    # holes line up with the letter's standoffs exactly as drawn
    if params.style.backer != "none":
        if params.style.backer == "tile" and layout.backer is not None:
            plaque_poly = heal(as_multipolygon(layout.backer))
        else:
            plaque_poly = ring_offset(filled(F), params.style.contour_margin_mm)
        if not plaque_poly.is_empty:
            PLAQUE_T = 3.0
            plate = prism(plaque_poly, 0, PLAQUE_T)
            drills = [
                cylinder(st.standoff_bore, PLAQUE_T + 2, sx, sy, -1.0)
                for sx, sy in standoffs
            ]
            px0, py0, px1, py1 = plaque_poly.bounds
            inset = params.style.screw_inset_mm
            from shapely.geometry import Point as _Pt

            for wx in (px0 + inset, px1 - inset):
                for wy in (py0 + inset, py1 - inset):
                    if plaque_poly.buffer(0.5).covers(_Pt((wx, wy))) and all(
                        math.dist((wx, wy), s) > 12 for s in standoffs
                    ):
                        drills.append(cylinder(params.style.screw_d_mm, PLAQUE_T + 2, wx, wy, -1.0))
            if drills:
                plate = plate - union_all(drills)
            bodies.append(Body("plaque", plate, ex["shell"], colors["shell"], plate="plaque"))

    # pre-mirror everything (flip-to-use); footprint mirrors for panelize/preview
    cx = (layout.bbox[0] + layout.bbox[2]) / 2
    for b in bodies:
        if b.plate == "main":
            b.man = b.man.mirror((1, 0, 0)).translate([2 * cx, 0, 0])
    return bodies, halo_footprint(layout, params)
