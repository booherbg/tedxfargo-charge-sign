"""The build orchestrator. CLI and web are thin clients of build()."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from .ingest.fonts import text_to_artwork
from .layout import build_layout
from .model import Artwork, Body, BuildResult
from .params import SignParams
from .export.stl import export_mesh
from .verify import BuildError

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
    from .ingest.art import art_to_artwork  # Phase 6

    return art_to_artwork(c.art_path, c.art_target_height_mm, c.trace_threshold, c.trace_invert)


def build(
    params: SignParams, outdir: str | Path, progress: Optional[ProgressFn] = None
) -> BuildResult:
    say = progress or (lambda msg: None)
    out = Path(outdir)
    (out / "stl").mkdir(parents=True, exist_ok=True)

    say("ingesting artwork")
    art = _ingest(params)
    if (art.fills is None or art.fills.is_empty) and not art.strokes:
        raise BuildError(f"ingest produced no geometry ({art.source})")

    say("laying out")
    layout = build_layout(art, params)

    warnings: list[str] = []
    pixels: list = []   # LED planning lands in Phase 4

    say(f"building {params.style.kind} bodies")
    if params.style.kind == "channel":
        from .parts.channel import build_channel_bodies

        bodies = build_channel_bodies(layout, pixels, params)
    else:
        from .parts.neon import build_neon_bodies

        bodies = build_neon_bodies(layout, pixels, params)

    files: list[str] = []
    body_stats: dict[str, dict] = {}
    for body in bodies:
        path = out / "stl" / f"{params.name}_{body.name}.stl"
        say(f"verifying + exporting {path.name}")
        verts, tris, notes = export_mesh(path, body.man, f"{params.name}_{body.name}")
        warnings += notes
        files.append(str(path))
        vol_mm3 = float(body.man.volume())
        body_stats[body.name] = {
            "tris": int(len(tris)),
            "volume_mm3": round(vol_mm3, 1),
            "grams_petg": round(vol_mm3 / 1000 * PETG_G_PER_CM3, 1),
            "extruder": body.extruder,
        }

    params_path = out / "params.json"
    params_path.write_text(params.to_json())
    files.append(str(params_path))

    x0, y0, x1, y1 = layout.bbox
    stats = {
        "sign_mm": [round(x1 - x0, 1), round(y1 - y0, 1)],
        "bodies": body_stats,
        "total_grams_petg": round(sum(b["grams_petg"] for b in body_stats.values()), 1),
        "pixels": len(pixels),
        "source": art.source,
    }
    say("done")
    return BuildResult(outdir=str(out), files=files, stats=stats, warnings=warnings)
