"""Tube planning for neon signs: centerlines from art, auto-kern, QA gates.

- Stroked source art (SVG paths with stroke width) is used directly.
- Filled art is skeletonized PER GLYPH when glyph structure exists (prevents
  cross-letter kiss-welding), else as a whole.
- Auto-kern (lesson 16): widened bands change the art's collision rules —
  kissing glyphs are nudged apart until their bands clear.
- Gates: coverage QA vs the source ink (lesson 12 — the check that would have
  caught the A amputation) and channel clearance audit (lesson 16).
"""

from __future__ import annotations

from dataclasses import replace

from shapely.affinity import translate
from shapely.ops import unary_union

from .geom2d import band, heal
from .layout import build_layout
from .model import Artwork, GlyphBox, Layout, Stroke
from .params import SignParams
from .skeleton import extract_centerlines
from .verify import BuildError, clearance_audit, coverage_qa

COVERAGE_FAIL_MM2 = 100.0
COVERAGE_NOTE_MM2 = 60.0
MAX_KERN_MM = 20.0


def _shift_stroke(s: Stroke, dx: float) -> Stroke:
    return Stroke(pts=[(x + dx, y) for x, y in s.pts], width=s.width, closed=s.closed)


def _rescue_clusters(missed: list, tube_w: float) -> list[Stroke]:
    """Recover centerlines from uncovered ink clusters (script terminals)."""
    rescued: list[Stroke] = []
    for poly in missed:
        cluster = heal(poly)
        if cluster.is_empty:
            continue
        subs, _meta = extract_centerlines(
            cluster, spur_mm=2.5, rung_mm=4.0, min_path_mm=5.0, step_mm=3.0
        )
        if subs:
            rescued += subs
            continue
        # compact blob: fall back to the midline of its oriented bbox,
        # trimmed so the round band caps land on the ink boundary
        if cluster.area < 4.0:
            continue
        try:
            import numpy as _np

            with _np.errstate(divide="ignore", invalid="ignore"):
                rect = cluster.minimum_rotated_rectangle
            cs = list(rect.exterior.coords)[:4]
        except Exception:
            continue
        if len(cs) < 4:
            continue
        import math as _m

        e1 = (_m.dist(cs[0], cs[1]), (cs[0], cs[1]), (cs[3], cs[2]))
        e2 = (_m.dist(cs[1], cs[2]), (cs[1], cs[2]), (cs[0], cs[3]))
        _, (a0, a1), (b0, b1) = max(e1, e2)
        mid0 = ((a0[0] + b0[0]) / 2, (a0[1] + b0[1]) / 2)
        mid1 = ((a1[0] + b1[0]) / 2, (a1[1] + b1[1]) / 2)
        L = _m.dist(mid0, mid1)
        if L < 2.0:
            continue
        trim = min(tube_w / 2, L * 0.35) / L
        p0 = (mid0[0] + (mid1[0] - mid0[0]) * trim, mid0[1] + (mid1[1] - mid0[1]) * trim)
        p1 = (mid1[0] + (mid0[0] - mid1[0]) * trim, mid1[1] + (mid0[1] - mid1[1]) * trim)
        rescued.append(Stroke(pts=[p0, p1], width=None, closed=False))
    return rescued


def plan_tubes(
    layout: Layout, params: SignParams
) -> tuple[list[Stroke], Layout, dict, list[str]]:
    """Returns (strokes, possibly-rekerned layout, meta, warnings)."""
    st = params.style.neon
    warnings: list[str] = []
    meta: dict = {}

    if layout.strokes:
        strokes = layout.strokes
        meta["source"] = "strokes"
        meta["tube_w"] = max((s.width or 0) for s in strokes) or st.channel_interior
    elif layout.glyphs:
        # per-glyph skeletonization, then auto-kern glyphs whose bands collide
        glyph_strokes: list[list[Stroke]] = []
        tube_ws: list[float] = []
        for g in layout.glyphs:
            # prune relative to the GLYPH, not the tube: a 110mm bold K's lower
            # leg is a ~40mm chain — the absolute 45mm clamp amputated it
            gh = max(g.bbox[3] - g.bbox[1], g.bbox[2] - g.bbox[0], 1.0)
            s, m = extract_centerlines(g.fills, min_path_mm=max(8.0, 0.22 * gh))
            glyph_strokes.append(s)
            if m["tube_w"]:
                tube_ws.append(m["tube_w"])
        order = sorted(range(len(layout.glyphs)), key=lambda i: layout.glyphs[i].bbox[0])
        shifts = [0.0] * len(layout.glyphs)
        cum = 0.0
        prev_band = None
        for oi, gi in enumerate(order):
            shifts[gi] = cum
            gb = band([_shift_stroke(s, cum) for s in glyph_strokes[gi]], st.band_outer)
            if prev_band is not None and not gb.is_empty:
                extra = 0.0
                while gb.intersects(prev_band) and extra < MAX_KERN_MM:
                    extra += 0.5
                    gb = translate(gb, xoff=0.5)
                if extra:
                    cum += extra
                    shifts[gi] += extra
                    warnings.append(
                        f"auto-kern: '{layout.glyphs[gi].char}' +{extra:.1f} mm "
                        "(widened bands collided; lesson 16)"
                    )
            if not gb.is_empty:
                prev_band = gb if prev_band is None else heal(unary_union([prev_band, gb]))
        strokes = [
            _shift_stroke(s, shifts[gi])
            for gi in range(len(layout.glyphs))
            for s in glyph_strokes[gi]
        ]
        if any(shifts):
            art = Artwork(
                fills=heal(
                    unary_union(
                        [translate(g.fills, xoff=shifts[i]) for i, g in enumerate(layout.glyphs)]
                    )
                ),
                strokes=[],
                glyphs=[
                    GlyphBox(
                        g.char,
                        heal(translate(g.fills, xoff=shifts[i])),
                        translate(g.fills, xoff=shifts[i]).bounds,
                    )
                    for i, g in enumerate(layout.glyphs)
                ],
                source="auto-kerned",
            )
            layout = build_layout(art, params)
            strokes = [s for s in strokes]  # same coords: glyphs shifted in place
        meta["source"] = "skeleton:per-glyph"
        meta["tube_w"] = sum(tube_ws) / len(tube_ws) if tube_ws else st.channel_interior
    elif layout.fills is not None and not layout.fills.is_empty:
        strokes, m = extract_centerlines(layout.fills)
        meta["source"] = "skeleton:whole"
        meta["tube_w"] = m["tube_w"]
    else:
        raise BuildError("neon style needs artwork (text, fills, or stroked paths)")

    if not strokes:
        raise BuildError(
            "no tube centerlines found — art may be too small or too thin to skeletonize"
        )

    # --- gates -------------------------------------------------------------
    if layout.fills is not None and not layout.fills.is_empty and "skeleton" in meta["source"]:
        cover_w = max(meta["tube_w"], 1.0)
        x0, y0, x1, y1 = layout.bbox
        if cover_w > 0.30 * max(1.0, min(x1 - x0, y1 - y0)):
            warnings.append(
                f"heavy strokes (~{cover_w:.0f} mm wide): neon centerlines approximate "
                "slab letterforms coarsely — a rounded/medium font (or channel style) "
                "reads truer"
            )
        b = band(strokes, cover_w + 1.0)  # measured art width + raster tolerance
        # amputations are full-tube-sized; skeleton-vs-slab corner artifacts
        # scale with (tube_w/2)² — thresholds scale so bold fonts don't
        # false-fail, but CAP the scaling: at slab widths an uncapped (0.55w)²
        # (880mm² at w=54) hid a missing K-leg behind the neighbor's fat band
        fail_mm2 = min(max(COVERAGE_FAIL_MM2, (0.55 * cover_w) ** 2), 700.0)
        note_mm2 = min(max(COVERAGE_NOTE_MM2, fail_mm2 / 2), fail_mm2)
        fails, notes, missed = coverage_qa(
            layout.fills, b, fail_mm2, note_mm2, return_geoms=True
        )
        if missed:
            # TERMINAL RESCUE — the automated make_repairs.py: script fonts end
            # in blobs/tails whose skeletons prune as spurs. Re-skeletonize each
            # uncovered cluster with gentle pruning and add the recovered tubes.
            rescued = _rescue_clusters(missed, cover_w)
            if rescued:
                strokes = strokes + rescued
                warnings.append(
                    f"terminal rescue: {len(rescued)} tube(s) recovered from "
                    f"{len(missed)} uncovered cluster(s) (script terminals/tails)"
                )
                b = band(strokes, cover_w + 1.0)
                fails, notes = coverage_qa(layout.fills, b, fail_mm2, note_mm2)
        warnings += [f"coverage note: {n}" for n in notes]
        if fails:
            strict = params.style.neon.coverage_strict
            if strict is None:
                strict = meta["source"] == "skeleton:per-glyph"  # letterforms are law
            if strict:
                raise BuildError(
                    "coverage QA FAILED — tube layout misses source ink "
                    "(the A-amputation class): " + "; ".join(fails)
                )
            warnings += [
                f"coverage warning (shape art, tips are approximate): {f}" for f in fails
            ]

    min_gap = st.band_outer + 4.0
    violations = clearance_audit(strokes, min_gap=min_gap)
    warnings += violations
    return strokes, layout, meta, warnings
