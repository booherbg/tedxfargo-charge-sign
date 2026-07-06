"""Neon-tube style bodies (port of CHARGE src/parts/piece.scad).

Cross-section (locked-specs): black plate + black outer wall / white liner
floor + white inner wall + collars / clear welded lens on top. The lens
deliberately overlaps the wall tops by the fuse (0.1 mm) — the CHARGE-proven
"welded lens" co-print. All bodies share sign coordinates (co-registered).
"""

from __future__ import annotations

from shapely.geometry import MultiPolygon

from ..geom2d import band, heal, ring_offset
from ..model import Body, Layout, Stroke
from ..params import SignParams
from ..solids import prism
from ..verify import BuildError
from .common import bore_stack, collar, union_all


def build_neon_bodies(
    layout: Layout, strokes: list[Stroke], pixels: list, params: SignParams
) -> list[Body]:
    if not strokes:
        raise BuildError("neon bodies need tube centerlines")
    st = params.style.neon
    fuse = params.fit.fuse_mm
    ex = params.colors.extruders
    colors = params.colors.preview

    b_in = band(strokes, st.channel_interior)
    b_liner = band(strokes, st.channel_interior + 2 * st.liner_wall)
    b_out = band(strokes, st.band_outer)

    if params.style.backer == "tile" and layout.backer is not None:
        plate_fp = heal(MultiPolygon([layout.backer]).union(b_out))
    elif params.style.backer == "contour":
        plate_fp = ring_offset(b_out, params.style.contour_margin_mm)
    else:
        plate_fp = b_out

    wall_top = st.plate_t + st.wall_height
    bodies: list[Body] = []

    # ---- shell (black): plate − collar bores + outer wall ring --------------
    plate = prism(plate_fp, 0, st.plate_t)
    bores = bore_stack(pixels, params.leds.collar_od_mm, -0.1, st.plate_t + 0.1)
    if bores is not None:
        plate = plate - bores
    outer_ring = heal(b_out.difference(b_liner))
    walls = prism(outer_ring, st.plate_t - fuse, wall_top)
    bodies.append(Body("shell", union_all([plate, walls]), ex["shell"], colors["shell"]))

    # ---- liner (white): floor + inner wall + collars -------------------------
    if pixels or params.leds.kind != "none":
        floor_top = st.plate_t + st.liner_floor_t
        floor = prism(b_liner, st.plate_t, floor_top)
        thin = bore_stack(pixels, params.leds.bore_mm, st.plate_t - 0.2, floor_top + 0.1)
        if thin is not None:
            floor = floor - thin
        liner_ring = heal(b_liner.difference(b_in))
        parts = [floor]
        if not liner_ring.is_empty:
            parts.append(prism(liner_ring, floor_top - fuse, wall_top))
        if params.leds.collar:
            parts += [
                collar(x, y, 0.0, params.leds.collar_od_mm, params.leds.collar_h_mm)
                for (x, y) in pixels
            ]
        bodies.append(Body("liner", union_all(parts), ex["liner"], colors["liner"]))

    # ---- lens (clear): welded band over the walls, baked fuzzy top -----------
    lens = prism(b_out, wall_top - fuse, wall_top + st.lens_t)
    if params.texture.mode != "none":
        from ..textures import textured_lens_top

        tex = textured_lens_top(
            b_out, wall_top + st.lens_t, params, params.texture.seed, fuse
        )
        lens = lens + tex
    bodies.append(Body("lens", lens, ex["lens"], colors["lens"]))
    return bodies
