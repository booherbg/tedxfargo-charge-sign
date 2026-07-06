"""Fit-ladder coupons: never dial fits on full parts (lesson 1).

CHARGE found its -0.2 mm lens interference by printing a LADDER of small
labeled slices of the real joint and feeling each one. This generator ships
that methodology: a strip of channel slices + matching lens plugs across a
range of fit values, each debossed with its value. Print, snap, pick, set
`style.channel.lip_clear` (or neon equivalents) with evidence.
"""

from __future__ import annotations

from shapely.affinity import translate as _tr

from .geom2d import band, bbox_polygon, heal, ring_offset
from .ingest.fonts import text_to_artwork
from .model import Body, Stroke
from .params import SignParams
from .parts.common import union_all
from .solids import prism

SLICE_LEN = 30.0     # each coupon: a short straight run of the real channel
GAP = 8.0            # spacing between coupons on the strip


def _value_label(v: float, cap_mm: float = 5.0):
    art = text_to_artwork(None, f"{v:+.1f}", cap_height_mm=cap_mm)
    return art.fills


def fit_ladder(
    params: SignParams, values: list[float] | None = None
) -> tuple[list[Body], list[str]]:
    """Bodies for one plate: N female channel slices + N male lens plugs.

    values are lip clearances (negative = interference), default the CHARGE
    ladder around the proven -0.2.
    """
    if values is None:
        values = [0.1, 0.0, -0.1, -0.2, -0.3]
    st = params.style.neon
    fuse = params.fit.fuse_mm
    ex = params.colors.extruders
    colors = params.colors.preview
    notes = [f"fit ladder: lip clearances {values} (print, snap, pick the winner)"]

    females = []
    males = []
    for i, v in enumerate(values):
        y = i * (st.band_outer + GAP)
        stroke = Stroke(pts=[(0.0, y), (SLICE_LEN, y)])
        b_in = band([stroke], st.channel_interior)
        b_out = band([stroke], st.band_outer)
        # female: plate + walls (the real cross-section, no liner needed to feel fit)
        base = prism(heal(bbox_polygon(-4, y - st.band_outer / 2 - 4, SLICE_LEN + 4, y + st.band_outer / 2 + 4)), 0, st.plate_t)
        wall = prism(heal(b_out.difference(b_in)), st.plate_t - fuse, st.plate_t + 6.0)
        lab = _value_label(v)
        if lab is not None and not lab.is_empty:
            lx0, ly0, lx1, ly1 = lab.bounds
            lab = heal(_tr(lab, xoff=SLICE_LEN + 4 - lx1 - 1, yoff=y + st.band_outer / 2 + 4 - ly1 - 1))
            base = base - prism(lab, st.plate_t - 0.4, st.plate_t + 0.1)
        females.append(union_all([base, wall]))

        # male: lens plug sized channel_interior + (-v) interference, on a handle
        plug_poly = ring_offset(b_in, -v / 2)
        xoff = SLICE_LEN + 30.0
        plug = prism(heal(_tr(plug_poly, xoff=xoff)), 0, 4.0)
        handle = prism(
            heal(bbox_polygon(xoff, y - st.band_outer / 2, xoff + SLICE_LEN, y + st.band_outer / 2)),
            4.0 - fuse,
            5.2,
        )
        males.append(union_all([plug, handle]))

    bodies = [
        Body("shell", union_all(females), ex["shell"], colors["shell"]),
        Body("lens", union_all(males), ex["lens"], colors["lens"]),
    ]
    return bodies, notes
