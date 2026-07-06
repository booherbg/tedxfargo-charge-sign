"""The build orchestrator. CLI and web are thin clients of build()."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from .export.bundle import render_bom, zip_bundle
from .export.stl import stl_bytes
from .export.threemf import write_3mf
from .ingest.fonts import text_to_artwork
from .layout import build_layout
from .model import Artwork, BuildResult, LedPlan, Piece
from .params import SignParams
from .preview.html import render_preview
from .solids import mesh_of
from .verify import BuildError, gated_mesh

PETG_G_PER_CM3 = 1.27

ProgressFn = Callable[[str], None]


def _ingest(params: SignParams) -> Artwork:
    c = params.content
    if c.mode == "text":
        return text_to_artwork(
            c.font_path,
            c.text,
            cap_height_mm=c.cap_height_mm,
            letter_spacing_mm=c.letter_spacing_mm,
            line_spacing=c.line_spacing,
            align=c.align,
        )
    from .ingest.art import art_to_artwork

    return art_to_artwork(c.art_path, c.art_target_height_mm, c.trace_threshold, c.trace_invert)


def quick_plan(params: SignParams):
    """Fast planning pass for live previews: no solids, no exports.
    Returns (layout, ledplan|None, pieces, warnings)."""
    from .geom2d import band, ring_offset
    from .panelize import assign_pixels, panelize

    art = _ingest(params)
    if (art.fills is None or art.fills.is_empty) and not art.strokes:
        raise BuildError(f"ingest produced no geometry ({art.source})")
    layout = build_layout(art, params)
    warnings: list[str] = []
    ledplan = None
    pixels: list = []
    if params.style.kind == "channel":
        from .parts.channel import channel_pan_footprint

        if layout.fills is None or layout.fills.is_empty:
            raise BuildError(
                "channel style needs filled artwork (text or filled vectors) — "
                "stroke-only art suits the neon style"
            )
        footprint = channel_pan_footprint(layout, params)
        pieces, cuts, pwarn = panelize(
            footprint, [], [], params, avoid=ring_offset(layout.fills, 4.0)
        )
        warnings += pwarn
    elif params.style.kind == "halo":
        from .leds import place_pixels, strip_plan
        from .parts.halo import halo_footprint, halo_pixel_strokes

        if layout.fills is None or layout.fills.is_empty:
            raise BuildError("halo style needs filled artwork (text or filled vectors)")
        strokes = halo_pixel_strokes(layout, params)
        footprint = halo_footprint(layout, params)
        pieces, cuts, pwarn = panelize(footprint, strokes, [], params)
        warnings += pwarn
        if len(pieces) > 1:
            pieces, cuts = pieces[:1], []
            warnings.append("halo faces aren't split in v1 — build letters individually")
        if params.leds.kind == "bullet12":
            ledplan = place_pixels(strokes, params, seams=cuts)
            pixels = ledplan.pixels
        elif params.leds.kind == "strip":
            ledplan = strip_plan(strokes, params)
    else:
        from .leds import place_pixels
        from .parts.neon import neon_plate_footprint
        from .tubes import plan_tubes

        strokes, layout, _meta, tw = plan_tubes(layout, params)
        warnings += tw
        layout.strokes = strokes
        b_out = band(strokes, params.style.neon.band_outer)
        footprint = neon_plate_footprint(layout, b_out, params)
        pieces, cuts, pwarn = panelize(footprint, strokes, [], params, avoid=b_out)
        warnings += pwarn
        if params.leds.kind == "bullet12":
            ledplan = place_pixels(strokes, params, seams=cuts)
            pixels = ledplan.pixels
        elif params.leds.kind == "strip":
            from .leds import strip_plan

            ledplan = strip_plan(strokes, params)
    assign_pixels(pieces, pixels)
    return layout, ledplan, pieces, warnings


def build(
    params: SignParams, outdir: str | Path, progress: Optional[ProgressFn] = None
) -> BuildResult:
    say = progress or (lambda msg: None)
    out = Path(outdir)
    (out / "stl").mkdir(parents=True, exist_ok=True)
    (out / "3mf").mkdir(exist_ok=True)
    (out / "preview").mkdir(exist_ok=True)

    say("ingesting artwork")
    art = _ingest(params)
    if (art.fills is None or art.fills.is_empty) and not art.strokes:
        raise BuildError(f"ingest produced no geometry ({art.source})")

    say("laying out")
    layout = build_layout(art, params)

    warnings: list[str] = []
    files: list[str] = []
    ledplan: Optional[LedPlan] = None
    pixels: list = []
    pieces: list[Piece] = []

    say(f"building {params.style.kind} bodies")
    from .geom2d import band, ring_offset
    from .panelize import assign_pixels, panelize

    strokes = []
    if params.style.kind == "channel":
        from .parts.channel import build_channel_bodies, channel_pan_footprint

        if layout.fills is None or layout.fills.is_empty:
            raise BuildError(
                "channel style needs filled artwork (text or filled vectors) — "
                "stroke-only art suits the neon style"
            )
        footprint = channel_pan_footprint(layout, params)
        avoid = ring_offset(layout.fills, 4.0)
        say("panelizing")
        pieces, cuts, pwarn = panelize(footprint, [], [], params, avoid=avoid)
        warnings += pwarn
        bodies, _fp = build_channel_bodies(layout, pixels, params)
    elif params.style.kind == "halo":
        from .leds import place_pixels
        from .parts.halo import build_halo_bodies, halo_footprint, halo_pixel_strokes

        strokes = halo_pixel_strokes(layout, params)
        footprint = halo_footprint(layout, params)
        say("panelizing")
        pieces, cuts, pwarn = panelize(footprint, strokes, [], params)
        warnings += pwarn
        if len(pieces) > 1:
            warnings.append(
                "halo faces aren't split in v1 — build letters individually "
                "(one build per letter) or reduce size; exporting whole"
            )
            pieces, cuts = pieces[:1], []
            x0, y0, x1, y1 = footprint.bounds
            from .geom2d import bbox_polygon

            pieces[0].mask = bbox_polygon(x0 - 1, y0 - 1, x1 + 1, y1 + 1)
            pieces[0].screws = []
        if params.leds.kind == "bullet12":
            ledplan = place_pixels(strokes, params, seams=cuts)
            warnings += ledplan.audits
            pixels = ledplan.pixels
        elif params.leds.kind == "strip":
            from .leds import strip_plan

            ledplan = strip_plan(strokes, params)
            warnings += ledplan.audits
        bodies, _fp = build_halo_bodies(layout, pixels, params)
    else:
        from .leds import place_pixels
        from .parts.neon import build_neon_bodies, neon_plate_footprint
        from .tubes import plan_tubes

        say("planning tubes (skeletonize + QA gates)")
        strokes, layout, tube_meta, tube_warnings = plan_tubes(layout, params)
        warnings += tube_warnings
        layout.strokes = strokes
        b_out = band(strokes, params.style.neon.band_outer)
        footprint = neon_plate_footprint(layout, b_out, params)
        say("panelizing")
        pieces, cuts, pwarn = panelize(footprint, strokes, [], params, avoid=b_out)
        warnings += pwarn
        if params.leds.kind == "bullet12":
            ledplan = place_pixels(strokes, params, seams=cuts)
            warnings += ledplan.audits
            pixels = ledplan.pixels
        elif params.leds.kind == "strip":
            from .leds import strip_plan

            ledplan = strip_plan(strokes, params)
            warnings += ledplan.audits
        bodies, _fp = build_neon_bodies(layout, strokes, pixels, params)
        if params.output.debug_overlays and layout.fills is not None and not layout.fills.is_empty:
            from .skeleton import debug_overlay

            dpath = out / "preview" / "debug_tubes.png"
            debug_overlay(layout.fills, strokes, pixels, str(dpath))
            files.append(str(dpath))

    assign_pixels(pieces, pixels)
    multi = len(pieces) > 1
    for pc in pieces:
        if pc.rotated:
            warnings.append(f"{pc.label}: fits the bed rotated 90° — rotate at import")

    body_stats: dict[str, dict] = {}
    pieces_detail: list[dict] = []
    from .export.pieces import clip_bodies_to_piece

    viewer_pieces: list[dict] = []
    for pi, pc in enumerate(pieces):
        say(f"cutting + verifying {pc.label}" if multi else "verifying bodies")
        piece_bodies, notes = clip_bodies_to_piece(bodies, pc, params, multi)
        warnings += notes
        plates: dict[str, list[tuple[str, object, object, int]]] = {}
        detail = {"label": pc.label, "pixels": len(pc.pixel_idx), "grams": 0.0,
                  "rotated": pc.rotated, "bodies": {}}
        vc = pc.mask.centroid
        vpc = {"label": pc.label, "center": (vc.x, vc.y), "bodies": []}
        for bname, man, extruder, plate, color in piece_bodies:
            verts, tris = mesh_of(man)
            tag = f"{params.name}_{pc.name}_{bname}" if multi else f"{params.name}_{bname}"
            verts, tris, gnotes = gated_mesh(verts, tris, tag)
            warnings += gnotes
            data = stl_bytes(verts, tris)
            if params.output.stl:
                path = out / "stl" / f"{tag}.stl"
                path.write_bytes(data)
                files.append(str(path))
            if plate == "main" and params.output.preview:
                vpc["bodies"].append({"name": bname, "color": color, "stl": data})
            plates.setdefault(plate, []).append((bname, verts, tris, extruder))
            vol = float(man.volume())
            grams = round(vol / 1000 * PETG_G_PER_CM3, 1)
            detail["grams"] = round(detail["grams"] + grams, 1)
            detail["bodies"][bname] = grams
            agg = body_stats.setdefault(
                bname, {"tris": 0, "volume_mm3": 0.0, "grams_petg": 0.0, "extruder": extruder}
            )
            agg["tris"] += int(len(tris))
            agg["volume_mm3"] = round(agg["volume_mm3"] + vol, 1)
            agg["grams_petg"] = round(agg["grams_petg"] + grams, 1)
        if params.output.threemf:
            for plate, parts in plates.items():
                suffix = f"{pc.name}_{plate}" if multi else plate
                path = out / "3mf" / f"{params.name}_{suffix}.3mf"
                write_3mf(path, parts)
                files.append(str(path))
        pieces_detail.append(detail)
        if vpc["bodies"]:
            viewer_pieces.append(vpc)

    x0, y0, x1, y1 = layout.bbox
    stats = {
        "sign_mm": [round(x1 - x0, 1), round(y1 - y0, 1)],
        "bodies": body_stats,
        "total_grams_petg": round(sum(b["grams_petg"] for b in body_stats.values()), 1),
        "pixels": len(pixels),
        "pieces": max(1, len(pieces)),
        "pieces_detail": pieces_detail,
        "source": art.source,
    }

    if params.output.preview:
        say("rendering preview")
        html = render_preview(layout, pieces, ledplan, stats, params, body_notes=warnings)
        ppath = out / "preview" / "index.html"
        ppath.write_text(html)
        files.append(str(ppath))
        from .preview.viewer import render_viewer

        vhtml = render_viewer(params.name, viewer_pieces)
        if vhtml is not None:
            vpath = out / "preview" / "viewer.html"
            vpath.write_text(vhtml)
            files.append(str(vpath))
        else:
            warnings.append("kit too large to embed in the 3D viewer — use the web UI")

    if params.output.bom:
        bpath = out / "BOM.md"
        bpath.write_text(render_bom(params, stats, ledplan, warnings))
        files.append(str(bpath))

    params_path = out / "params.json"
    params_path.write_text(params.to_json())
    files.append(str(params_path))

    say("zipping bundle")
    zpath = zip_bundle(out, params.name, files)
    files.append(zpath)

    say("done")
    return BuildResult(outdir=str(out), files=files, stats=stats, warnings=warnings, pieces=pieces)
