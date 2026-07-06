"""Artwork dispatcher: route uploaded files to the right ingester."""

from __future__ import annotations

from pathlib import Path

from ..model import Artwork
from ..verify import BuildError


def art_to_artwork(
    path: str, target_height_mm: float, trace_threshold: int = 128, trace_invert: bool = False
) -> Artwork:
    ext = Path(path).suffix.lower()
    if ext == ".svg":
        from .svg import svg_to_artwork

        return svg_to_artwork(path, target_height_mm)
    if ext == ".dxf":
        from .dxf import dxf_to_artwork

        return dxf_to_artwork(path, target_height_mm)
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
        from .raster_img import raster_to_artwork

        return raster_to_artwork(path, target_height_mm, trace_threshold, trace_invert)
    raise BuildError(
        f"unsupported artwork format {ext!r} — use SVG, DXF, or PNG/JPG "
        "(EPS: convert to SVG first, e.g. with ghostscript/pdftocairo)"
    )
