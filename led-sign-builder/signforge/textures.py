"""Baked lens textures (port of CHARGE tools/make_fuzz.py, V1→V9 ladder).

Winner (V8, PETG bake-off): pyramid-jitter — square-pyramid facet lattice,
per-cell random peak height (0.6–1.0×) and offset (±0.25 cell), MAX-UNION of
neighboring tents (no cliffs → no degenerate-sliver populations), sampled at
cell/3 (the 0.4 nozzle is the real resolution limit).

Anti-sliver canon (lesson 9), preserved even though Manifold booleans are
robust: height floor keeps the field strictly proud of the lens plane; the
field overlaps its lens by the fuse (never exact tangency). Slicer fuzzy skin
can't texture top faces — that's why these are geometry (lesson 6).
"""

from __future__ import annotations

import numpy as np
from shapely.geometry import MultiPolygon

import manifold3d as m3d

from .params import SignParams
from .solids import heightfield, prism

FLOOR = 0.02  # mm — never let a cell height hit zero (lesson 9)


def fuzz_grid(
    mode: str,
    cell: float,
    hmax: float,
    seed: int,
    area_xy: tuple[float, float],
    sample_div: int = 3,
) -> tuple[np.ndarray, float]:
    """Height grid covering area_xy. Returns (grid_mm, sample_spacing_mm)."""
    rng = np.random.default_rng(seed)
    ax, ay = area_xy
    if mode == "random":
        nx = int(ax / cell) + 2
        ny = int(ay / cell) + 2
        grid = np.maximum(FLOOR, rng.uniform(0.0, hmax, size=(ny, nx)))
        return grid, cell

    if mode not in ("pyramid", "pyramid_jitter"):
        raise ValueError(f"unknown texture mode {mode!r}")

    s = max(2, sample_div)
    step = cell / s
    nx = int(ax / step) + 2
    ny = int(ay / step) + 2
    ncx = nx // s + 3
    ncy = ny // s + 3
    if mode == "pyramid_jitter":
        h = hmax * rng.uniform(0.6, 1.0, size=(ncy, ncx))
        ox = rng.uniform(-0.25, 0.25, size=(ncy, ncx))
        oy = rng.uniform(-0.25, 0.25, size=(ncy, ncx))
    else:
        h = np.full((ncy, ncx), hmax)
        ox = np.zeros((ncy, ncx))
        oy = np.zeros((ncy, ncx))

    gx = (np.arange(nx) / s)[None, :]          # sample positions, cell units
    gy = (np.arange(ny) / s)[:, None]
    cx0 = np.floor(gx).astype(int)             # home cell per sample column
    cy0 = np.floor(gy).astype(int)
    best = np.zeros((ny, nx))
    # MAX-UNION of the 3x3 neighboring cells' tents: per-cell-only evaluation
    # leaves cliffs at cell borders (jittered neighbors disagree) — the exact
    # bug that bred non-manifold slivers in CHARGE round 2 (commit 6208a8d).
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx = np.clip(cx0 + dx, 0, ncx - 1)
            cy = np.clip(cy0 + dy, 0, ncy - 1)
            hh = h[cy, cx]
            fx = gx - (cx + 0.5 + ox[cy, cx])
            fy = gy - (cy + 0.5 + oy[cy, cx])
            t = np.maximum(np.abs(fx), np.abs(fy)) * 2.0
            best = np.maximum(best, (hh / hmax) * np.clip(1.0 - t, 0.0, None))
    grid = FLOOR + best * (hmax - FLOOR)
    return grid, step


def textured_lens_top(
    band: MultiPolygon,
    z_top: float,
    params: SignParams,
    piece_seed: int,
    fuse: float,
) -> m3d.Manifold:
    """The texture solid to union onto a flat lens whose top face is z_top.

    Field base sinks fuse below z_top (weld overlap, no tangency); heights are
    floored so every peak stays strictly proud of the lens plane."""
    t = params.texture
    x0, y0, x1, y1 = band.bounds
    margin = t.cell_mm
    grid, step = fuzz_grid(
        t.mode,
        t.cell_mm,
        t.height_mm,
        piece_seed,
        (x1 - x0 + 2 * margin, y1 - y0 + 2 * margin),
        t.sample_div,
    )
    grid = grid + fuse + t.standoff_mm            # keep peaks proud after sinking
    hf = heightfield(grid, step, (x0 - margin, y0 - margin), z_top - fuse)
    clip = prism(band, z_top - fuse - 0.5, z_top + t.height_mm + fuse + 1.0)
    tex = hf ^ clip
    if tex.is_empty():
        from .verify import BuildError

        raise BuildError("textured_lens_top: texture∩band came up empty")
    return tex
