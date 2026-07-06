"""Channel-letter style: back pan + perimeter/counter walls + press-fit face lens.

Geometry rules:
- Back pan spans the FILLED outline (counters enclosed) so nothing floats.
- Walls rise from the pan along the letter boundary INCLUDING counter boundaries.
- Face lens is a separate press-fit part with a lip (CHARGE fit: -0.2 mm
  interference). It prints face-DOWN and is therefore PRE-MIRRORED (flip-to-use
  = mirror; lesson 2). Emitted in its own print coordinates.
- 0.1 mm fuse overlaps between stacked prisms — never exact tangency.
"""

from __future__ import annotations

from shapely.geometry import MultiPolygon

from ..geom2d import heal, ring_offset
from ..model import Body, Layout
from ..params import SignParams
from ..solids import prism
from ..verify import BuildError
from .common import bore_stack, collar, filled, union_all

LIP_WALL = 1.5  # lens lip ring thickness (bolt lens value)


def channel_pan_footprint(layout: Layout, params: SignParams) -> MultiPolygon:
    F_solid = filled(layout.fills)
    if params.style.backer == "tile" and layout.backer is not None:
        return heal(MultiPolygon([layout.backer]).union(F_solid))
    if params.style.backer == "contour":
        pan = heal(ring_offset(F_solid, params.style.contour_margin_mm))
        if layout.backer is not None:
            pan = heal(pan.union(MultiPolygon([layout.backer])))
        return pan
    return F_solid


def build_channel_bodies(
    layout: Layout, pixels: list, params: SignParams
) -> tuple[list[Body], MultiPolygon]:
    """Returns (bodies, plate footprint in sign coords)."""
    if layout.fills is None or layout.fills.is_empty:
        raise BuildError("channel style needs filled artwork (text or filled vectors)")
    st = params.style.channel
    fuse = params.fit.fuse_mm
    ex = params.colors.extruders
    colors = params.colors.preview

    F = layout.fills                       # letters with counter holes
    F_solid = filled(F)                    # counters filled (back pan)
    pan_poly = channel_pan_footprint(layout, params)

    cavity = ring_offset(F, -st.wall_t)    # channel interior (per letter, honors counters)
    if cavity.is_empty:
        raise BuildError(
            f"channel: letters too small for wall_t={st.wall_t} (cavity vanished); "
            "reduce wall_t or increase cap height"
        )

    bodies: list[Body] = []

    # ---- shell: pan + walls -------------------------------------------------
    pan = prism(pan_poly, 0, st.plate_t)
    bores = bore_stack(pixels, params.leds.collar_od_mm, -0.1, st.plate_t + 0.1)
    if bores is not None:
        pan = pan - bores
    wall_band = heal(F.difference(cavity))
    walls = prism(wall_band, st.plate_t - fuse, st.plate_t + st.wall_height)
    bodies.append(Body("shell", union_all([pan, walls]), ex["shell"], colors["shell"]))

    # ---- liner: white floor + inner wall lining + collars (LED builds) ------
    if pixels:
        liner_floor = prism(cavity, st.plate_t - fuse, st.plate_t + 0.4)
        thin = bore_stack(pixels, params.leds.bore_mm, -0.2, st.plate_t + 0.5)
        if thin is not None:
            liner_floor = liner_floor - thin
        liner_ring_poly = heal(cavity.difference(ring_offset(cavity, -0.8)))
        parts = [liner_floor]
        if not liner_ring_poly.is_empty:
            parts.append(prism(liner_ring_poly, st.plate_t + 0.4 - fuse, st.plate_t + st.wall_height))
        parts += [
            collar(x, y, 0.0, params.leds.collar_od_mm, params.leds.collar_h_mm)
            for (x, y) in pixels
            if params.leds.collar
        ]
        bodies.append(Body("liner", union_all(parts), ex["liner"], colors["liner"]))

    # ---- lens: separate press-fit part, own print coords, PRE-MIRRORED ------
    face_poly = F_solid if st.counter_mode == "glow" else F
    lip_seat = ring_offset(cavity, -0.8)  # inside the liner ring
    lip_outer = ring_offset(lip_seat, -st.lip_clear / 2)   # interference grows it
    lip_ring = heal(lip_outer.difference(ring_offset(lip_outer, -LIP_WALL)))
    lens_parts = [prism(face_poly, 0, st.lens_t)]
    if st.lip_depth > 0 and not lip_ring.is_empty:
        lens_parts.append(prism(lip_ring, st.lens_t - fuse, st.lens_t + st.lip_depth))
    lens = union_all(lens_parts)
    cx = (layout.bbox[0] + layout.bbox[2]) / 2
    lens = lens.mirror((1, 0, 0)).translate([2 * cx, 0, 0])   # pre-mirror about x=cx
    bodies.append(Body("lens", lens, ex["lens"], colors["lens"], plate="lens"))

    return bodies, pan_poly
