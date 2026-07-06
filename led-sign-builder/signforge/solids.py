"""Manifold-by-construction 3D builders on top of manifold3d.

Rules (docs/LESSONS-FROM-CHARGE.md §B9-10): prefer construction over booleans,
keep ≥standoff between fields and partner planes, 0.1mm fuse overlaps for welds.
manifold3d output is guaranteed manifold in its own indexing; the export path
re-audits position-welded topology (verify.audit_mesh) — the Bambu-equivalent check.
"""

from __future__ import annotations

import manifold3d as m3d
import numpy as np
from shapely.geometry import MultiPolygon

from .geom2d import as_multipolygon, rings
from .verify import BuildError

CIRCLE_SEGS = 72  # CHARGE $fn


def cross_section(mpoly: MultiPolygon) -> m3d.CrossSection:
    ctrs = rings(as_multipolygon(mpoly))
    if not ctrs:
        raise BuildError("cross_section: empty geometry")
    return m3d.CrossSection(ctrs, m3d.FillRule.Positive)


def prism(mpoly: MultiPolygon, z0: float, z1: float) -> m3d.Manifold:
    if z1 <= z0:
        raise BuildError(f"prism: z1 ({z1}) must exceed z0 ({z0})")
    man = cross_section(mpoly).extrude(z1 - z0).translate([0.0, 0.0, z0])
    if man.is_empty():
        raise BuildError("prism: produced empty manifold")
    return man


def cylinder(d: float, h: float, cx: float, cy: float, z0: float) -> m3d.Manifold:
    return m3d.Manifold.cylinder(h, d / 2, d / 2, CIRCLE_SEGS).translate([cx, cy, z0])


def revolve_profile(
    profile_rz: list[tuple[float, float]], cx: float, cy: float, z0: float
) -> m3d.Manifold:
    """Lathe a closed (r, z) profile around the vertical axis at (cx, cy).

    Profile points: r >= 0 (radius), z relative to z0. CCW in the r-z plane.
    """
    pts = np.asarray(profile_rz, dtype=np.float64)
    if pts.ndim != 2 or len(pts) < 3:
        raise BuildError("revolve_profile: need >=3 (r,z) points")
    cs = m3d.CrossSection([pts], m3d.FillRule.Positive)
    man = cs.revolve(CIRCLE_SEGS)
    if man.is_empty():
        raise BuildError("revolve_profile: empty manifold (check winding/r>=0)")
    return man.translate([cx, cy, z0])


def box(x0: float, y0: float, x1: float, y1: float, z0: float, z1: float) -> m3d.Manifold:
    return m3d.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def heightfield(
    grid: np.ndarray, cell: float, origin: tuple[float, float], z_base: float
) -> m3d.Manifold:
    """Closed solid: flat bottom at z_base, displaced top at z_base + grid.

    grid[j, i] is the height (>0) at (origin_x + i*cell, origin_y + j*cell).
    Built as an indexed mesh — no boolean, no tangency, manifold by construction.
    """
    g = np.asarray(grid, dtype=np.float64)
    if g.ndim != 2 or g.shape[0] < 2 or g.shape[1] < 2:
        raise BuildError("heightfield: grid must be at least 2x2")
    if (g <= 0).any():
        raise BuildError("heightfield: all heights must be > 0 (closed solid)")
    ny, nx = g.shape
    ox, oy = origin

    xs = ox + np.arange(nx) * cell
    ys = oy + np.arange(ny) * cell
    xx, yy = np.meshgrid(xs, ys)                      # (ny, nx)

    top = np.stack([xx, yy, z_base + g], axis=-1).reshape(-1, 3)
    bot = np.stack([xx, yy, np.full_like(g, z_base)], axis=-1).reshape(-1, 3)
    verts = np.concatenate([top, bot]).astype(np.float32)
    nb = ny * nx                                      # bottom index offset

    def vid(i, j):                                    # top vertex index grid
        return j * nx + i

    tris: list[tuple[int, int, int]] = []
    # top (up-facing, CCW from +Z) and bottom (mirrored winding)
    for j in range(ny - 1):
        for i in range(nx - 1):
            v00, v10 = vid(i, j), vid(i + 1, j)
            v01, v11 = vid(i, j + 1), vid(i + 1, j + 1)
            tris += [(v00, v10, v11), (v00, v11, v01)]
            b00, b10, b01, b11 = v00 + nb, v10 + nb, v01 + nb, v11 + nb
            tris += [(b00, b11, b10), (b00, b01, b11)]
    # sides: walk the top boundary CCW (viewed from +Z); quad (ta,tb) -> bottom
    boundary: list[int] = []
    boundary += [vid(i, 0) for i in range(nx)]                      # south, +x
    boundary += [vid(nx - 1, j) for j in range(1, ny)]              # east,  +y
    boundary += [vid(i, ny - 1) for i in range(nx - 2, -1, -1)]     # north, -x
    boundary += [vid(0, j) for j in range(ny - 2, 0, -1)]           # west,  -y
    for a, b in zip(boundary, boundary[1:] + boundary[:1]):
        ta, tb, ba, bb = a, b, a + nb, b + nb
        tris += [(ta, ba, bb), (ta, bb, tb)]

    mesh = m3d.Mesh(
        vert_properties=verts, tri_verts=np.asarray(tris, dtype=np.uint32)
    )
    man = m3d.Manifold(mesh)
    if man.is_empty() or man.status() != m3d.Error.NoError:
        raise BuildError(f"heightfield: manifold rejected mesh ({man.status()})")
    if man.volume() <= 0:
        raise BuildError("heightfield: non-positive volume (winding bug)")
    return man


def mesh_of(man: m3d.Manifold) -> tuple[np.ndarray, np.ndarray]:
    """(verts float64 [n,3], tris int64 [m,3]) from a Manifold."""
    m = man.to_mesh64() if hasattr(man, "to_mesh64") else man.to_mesh()
    verts = np.asarray(m.vert_properties, dtype=np.float64)[:, :3]
    tris = np.asarray(m.tri_verts, dtype=np.int64).reshape(-1, 3)
    return verts, tris
