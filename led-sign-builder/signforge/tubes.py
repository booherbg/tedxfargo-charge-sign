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


def _outline_tubes(
    fills, band_outer: float
) -> tuple[list[Stroke], float, list[str]]:
    """Silhouette tubes: every boundary ring inset by half the band, so the
    band's outer edge lands on the art edge.

    Per COMPONENT: a part too thin to inset (rocket fins, cup handles) falls
    back to its skeleton spine instead of silently vanishing."""
    from shapely.geometry import MultiPolygon as _MP

    from .geom2d import as_multipolygon, ring_offset

    strokes: list[Stroke] = []
    notes: list[str] = []
    for comp in as_multipolygon(fills).geoms:
        inset = ring_offset(_MP([comp]), -band_outer / 2)
        if inset.is_empty or inset.area < 2.0:
            subs, _m = extract_centerlines(_MP([comp]), min_path_mm=6.0, spur_mm=3.0)
            if subs:
                strokes += subs
                notes.append(
                    f"outline: a {comp.area:.0f} mm² part is thinner than the "
                    f"{band_outer:.0f} mm band — traced its spine instead"
                )
            else:
                notes.append(
                    f"outline: a {comp.area:.0f} mm² part vanished (too small "
                    "for the band) — enlarge the sign to keep it"
                )
            continue
        for p in as_multipolygon(inset).geoms:
            for boundary in [p.exterior, *p.interiors]:
                pts = [(x, y) for x, y in boundary.coords[:-1]]
                if len(pts) >= 3:
                    strokes.append(Stroke(pts=pts, width=None, closed=True))
    return strokes, band_outer, notes


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

    direct = list(layout.strokes)          # stroked art: tubes as drawn
    if direct and (layout.fills is None or layout.fills.is_empty):
        meta["source"] = "strokes"
        meta["tube_w"] = max((s.width or 0) for s in direct) or st.channel_interior
        strokes = direct
    elif layout.glyphs:
        # per-glyph tubes, then auto-kern glyphs whose bands collide.
        # source=skeleton → single-stroke script neon (spine of each glyph);
        # source=outline  → classic OPEN-TUBE channel letters (the neon-shop
        # treatment for bold faces: tube traces the letter outline, counters
        # become inner rings; everything mounts to the plate — nothing floats)
        # aesthetic rule, decided PER GLYPH (the '/' in shrikhand "24/7" must
        # not drag the slab digits away from outline mode): OUTLINE when the
        # glyph stroke fits TWO tube bands plus a visible dark gap
        # (gap = stroke − 2·band; calibrated Bungee@250 w̄71 good vs Bebas@240
        # w̄36 fused). w̄_g = 2·area/perimeter of the glyph.
        def glyph_mode(g) -> str:
            if st.source != "auto":
                return st.source
            w_g = 2 * g.fills.area / g.fills.length if g.fills.length else 0.0
            return "outline" if w_g >= 2.2 * st.band_outer else "skeleton"

        def _glyph_uncovered(g, s, cover_w: float) -> float:
            if not s:
                return g.fills.area
            b = band(s, cover_w + 1.0)
            return float(g.fills.difference(b).area)

        def _skeleton_glyph(g, w_g: float, gh: float):
            if w_g >= 2.2 * st.band_outer:
                # BOLD glyph on the spine treatment: prune relative to the
                # glyph (the 110mm K's ~40mm leg vs absolute clamps)
                return extract_centerlines(g.fills, min_path_mm=max(8.0, 0.22 * gh))
            # THIN/striped glyph (Monoton): tube-scaled auto pruning —
            # a glyph-sized min_path amputates whole stripes
            return extract_centerlines(g.fills)

        glyph_strokes: list[list[Stroke]] = []
        tube_ws: list[float] = []
        modes_used: set[str] = set()
        for g in layout.glyphs:
            mode_g = glyph_mode(g)
            w_g = 2 * g.fills.area / g.fills.length if g.fills.length else 0.0
            gh = max(g.bbox[3] - g.bbox[1], g.bbox[2] - g.bbox[0], 1.0)
            if mode_g == "outline":
                s, _w, onotes = _outline_tubes(g.fills, st.band_outer)
                warnings += onotes
                if not s:  # glyph too thin to inset — spine fallback
                    s, _m = extract_centerlines(g.fills)
                tube_ws.append(st.band_outer)
            else:
                s, m = _skeleton_glyph(g, w_g, gh)
                cover_w = (m["tube_w"] or w_g) if m else w_g
                # PER-GLYPH RETRY LADDER (word×font-sweep lesson): a glyph whose
                # spine misses real ink retries at 2× raster resolution (thin
                # Monoton stripes alias at 2.4 px/mm), then as an outline
                # (shrikhand digits at w̄≈46 scribble as spines but ring fine)
                miss = _glyph_uncovered(g, s, cover_w)
                # slab corners always escape a spine — scale like the coverage
                # gate: (0.55·w̄)² capped, floored at 80
                thresh = max(80.0, min((0.55 * max(w_g, cover_w)) ** 2, 700.0))
                if miss > thresh:
                    s2, m2 = extract_centerlines(g.fills, px_per_mm=4.8)
                    if _glyph_uncovered(g, s2, (m2["tube_w"] or cover_w)) < miss * 0.5:
                        s, m = s2, m2
                        miss = _glyph_uncovered(g, s, m["tube_w"] or cover_w)
                        warnings.append(
                            f"'{g.char}': fine detail — re-traced at high resolution"
                        )
                if miss > thresh and st.source == "auto":
                    # mode-switching is auto's prerogative — an explicit
                    # skeleton choice stands (the gate will say so honestly)
                    s3, _w3, _n3 = _outline_tubes(g.fills, st.band_outer)
                    if s3 and _glyph_uncovered(g, s3, st.band_outer) < miss:
                        s = s3
                        mode_g = "outline"
                        tube_ws.append(st.band_outer)
                        warnings.append(
                            f"'{g.char}': spine couldn't cover the letterform — "
                            "switched to outline tubes"
                        )
                if mode_g != "outline" and m and m["tube_w"]:
                    tube_ws.append(m["tube_w"])
            modes_used.add(mode_g)
            glyph_strokes.append(s)
        text_mode = "mixed" if len(modes_used) > 1 else (modes_used.pop() if modes_used else "skeleton")
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
        meta["source"] = f"{text_mode}:per-glyph"
        meta["tube_w"] = sum(tube_ws) / len(tube_ws) if tube_ws else st.channel_interior
    elif layout.fills is not None and not layout.fills.is_empty:
        mode = st.source
        if mode == "auto":
            mode = "outline"   # shape art: trace the silhouette (neon-shop treatment)
        if mode == "outline":
            strokes, meta["tube_w"], onotes = _outline_tubes(layout.fills, st.band_outer)
            warnings += onotes
            meta["source"] = "outline"
            if not strokes:   # everything too thin — fall back to the spine
                strokes, m = extract_centerlines(layout.fills)
                meta["source"] = "skeleton:whole"
                meta["tube_w"] = m["tube_w"]
        else:
            strokes, m = extract_centerlines(layout.fills)
            meta["source"] = "skeleton:whole"
            meta["tube_w"] = m["tube_w"]
        if direct:
            strokes = strokes + direct     # mixed art: keep drawn tubes too
            meta["source"] += "+strokes"
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
                    "this font + text loses letterform detail at this size — the "
                    "tube layout can't cover the source ink. Try a LARGER sign, "
                    "style.neon.source='outline', or a different typeface. "
                    "(Uncovered: " + "; ".join(fails) + ")"
                )
            warnings += [
                f"coverage warning (shape art, tips are approximate): {f}" for f in fails
            ]

    # ---- neon-aesthetic advisory (specimen-audit lesson): real neon tubes
    # run ≤~12% of letter height; past ~15% the sign reads as a lit slab
    x0a, y0a, x1a, y1a = layout.bbox
    art_h = max(y1a - y0a, 1.0)
    ratio = st.band_outer / art_h
    if layout.glyphs and ratio > 0.15:
        target_h = st.band_outer / 0.11
        tips = "switch leds to 'strip'/'none' for slimmer channels"
        if "skeleton" in meta["source"]:
            tips += ", or style.neon.source='outline' for open-tube channel letters"
        warnings.append(
            f"chunky tubes: the {st.band_outer:.0f} mm band is {ratio:.0%} of the "
            f"letter height — classic neon reads at ≤12%. Scale to ≥{target_h:.0f} mm, or "
            + tips + "."
        )

    min_gap = st.band_outer + 4.0
    violations, worst_gap = clearance_audit(strokes, min_gap=min_gap)
    if len(violations) > 4 and worst_gap is not None:
        # a flood of mush = the DESIGN is tighter than the channel (Monoton at
        # small caps). One line + the actionable number beats 50 red rows.
        x0, y0, x1, y1 = layout.bbox
        h = max(y1 - y0, 1.0)
        scale_needed = min_gap / max(worst_gap, 0.5)
        warnings.append(
            f"{len(violations)} channel-clearance violations — this design's lines "
            f"run {worst_gap:.1f} mm apart but {min_gap:.0f} mm is needed. "
            f"Scale to ≥{h * scale_needed:.0f} mm tall (~{scale_needed:.1f}×) or slim "
            "the channels (style.neon.channel_interior)."
        )
    else:
        warnings += violations
    return strokes, layout, meta, warnings
