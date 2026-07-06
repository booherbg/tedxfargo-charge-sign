"""The build orchestrator. CLI and web are thin clients of build()."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from .export.bundle import render_bom, zip_bundle
from .export.stl import write_stl
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
    ledplan: Optional[LedPlan] = None
    pixels: list = []
    pieces: list[Piece] = []

    say(f"building {params.style.kind} bodies")
    if params.style.kind == "channel":
        from .parts.channel import build_channel_bodies

        bodies = build_channel_bodies(layout, pixels, params)
    else:
        from .parts.neon import build_neon_bodies

        bodies = build_neon_bodies(layout, pixels, params)

    files: list[str] = []
    body_stats: dict[str, dict] = {}
    plates: dict[str, list[tuple[str, object, object, int]]] = {}
    for body in bodies:
        say(f"verifying {body.name}")
        verts, tris = mesh_of(body.man)
        verts, tris, notes = gated_mesh(verts, tris, f"{params.name}_{body.name}")
        warnings += notes
        if params.output.stl:
            path = out / "stl" / f"{params.name}_{body.name}.stl"
            write_stl(path, verts, tris)
            files.append(str(path))
        plates.setdefault(body.plate, []).append((body.name, verts, tris, body.extruder))
        vol_mm3 = float(body.man.volume())
        body_stats[body.name] = {
            "tris": int(len(tris)),
            "volume_mm3": round(vol_mm3, 1),
            "grams_petg": round(vol_mm3 / 1000 * PETG_G_PER_CM3, 1),
            "extruder": body.extruder,
        }

    if params.output.threemf:
        for plate, parts in plates.items():
            path = out / "3mf" / f"{params.name}_{plate}.3mf"
            say(f"writing {path.name}")
            write_3mf(path, parts)
            files.append(str(path))

    x0, y0, x1, y1 = layout.bbox
    stats = {
        "sign_mm": [round(x1 - x0, 1), round(y1 - y0, 1)],
        "bodies": body_stats,
        "total_grams_petg": round(sum(b["grams_petg"] for b in body_stats.values()), 1),
        "pixels": len(pixels),
        "pieces": max(1, len(pieces)),
        "source": art.source,
    }

    if params.output.preview:
        say("rendering preview")
        html = render_preview(layout, pieces, ledplan, stats, params, body_notes=warnings)
        ppath = out / "preview" / "index.html"
        ppath.write_text(html)
        files.append(str(ppath))

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
