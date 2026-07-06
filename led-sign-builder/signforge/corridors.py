"""Corridor seam router (port of CHARGE tools/panelize.py cut logic).

Straight guillotine cuts fail on dense art: "a straight seam almost always
grazes a steep stroke" (lesson 17). This router threads a piecewise seam
through the DARK FIELD between tubes: build a coarse clearance grid (distance
to the nearest obstacle), then run Dijkstra across the region maximizing the
minimum clearance along the path, tie-broken by length. Seams never cross a
lit channel if any dark corridor exists.
"""

from __future__ import annotations

import heapq
import math

import numpy as np
from shapely.geometry import LineString, MultiPolygon

from .model import Point2

GRID = 4.0           # clearance-field resolution, mm
MIN_CLEAR = 5.0      # a corridor must keep this far from channel walls
SMOOTH_WIN = 3


def clearance_field(
    bounds: tuple[float, float, float, float], obstacle: MultiPolygon, grid: float = GRID
) -> tuple[np.ndarray, tuple[float, float]]:
    """dist[j, i] = distance (mm) from grid point to the obstacle region.
    Chamfer 3-4 distance transform over an obstacle rasterization — O(cells)."""
    x0, y0, x1, y1 = bounds
    nx = max(2, int(math.ceil((x1 - x0) / grid)) + 1)
    ny = max(2, int(math.ceil((y1 - y0) / grid)) + 1)
    INF = 1e9
    dist = np.full((ny, nx), INF, dtype=np.float64)

    if obstacle is not None and not obstacle.is_empty:
        from .skeleton import rasterize

        pad = grid  # rasterize() pads by pad_mm internally at ppm resolution
        ink, (ox, oy) = rasterize(obstacle, px_per_mm=1.0 / grid, pad_mm=pad)
        # map ink cells into our grid frame
        for j in range(ny):
            for i in range(nx):
                gx = int((x0 + i * grid - ox) / grid)
                gy = int((y0 + j * grid - oy) / grid)
                if 0 <= gy < ink.shape[0] and 0 <= gx < ink.shape[1] and ink[gy, gx]:
                    dist[j, i] = 0.0
        # two-pass chamfer (3-4 mask scaled to grid units)
        c1, c2 = grid, grid * math.sqrt(2)
        for j in range(ny):
            for i in range(nx):
                d = dist[j, i]
                if j > 0:
                    d = min(d, dist[j - 1, i] + c1)
                    if i > 0:
                        d = min(d, dist[j - 1, i - 1] + c2)
                    if i < nx - 1:
                        d = min(d, dist[j - 1, i + 1] + c2)
                if i > 0:
                    d = min(d, dist[j, i - 1] + c1)
                dist[j, i] = d
        for j in range(ny - 1, -1, -1):
            for i in range(nx - 1, -1, -1):
                d = dist[j, i]
                if j < ny - 1:
                    d = min(d, dist[j + 1, i] + c1)
                    if i > 0:
                        d = min(d, dist[j + 1, i - 1] + c2)
                    if i < nx - 1:
                        d = min(d, dist[j + 1, i + 1] + c2)
                if i < nx - 1:
                    d = min(d, dist[j, i + 1] + c1)
                dist[j, i] = d
    return dist, (x0, y0)


def route_corridor(
    bounds: tuple[float, float, float, float],
    obstacle: MultiPolygon,
    axis: str,
    window: tuple[float, float],
    min_clear: float = MIN_CLEAR,
    grid: float = GRID,
) -> list[Point2] | None:
    """Route a seam across the region within a coordinate window.

    axis="x": seam runs bottom→top, its x confined to window (a vertical-ish
    cut). axis="y": left→right, y confined. Returns a smoothed polyline in mm,
    or None if no corridor clears min_clear.
    """
    dist, (ox, oy) = clearance_field(bounds, obstacle, grid)
    ny, nx = dist.shape
    if axis == "x":
        lanes = range(
            max(0, int((window[0] - ox) / grid)), min(nx, int((window[1] - ox) / grid) + 1)
        )
        starts = [(0, i) for i in lanes]
        goal_row = ny - 1
    else:
        lanes = range(
            max(0, int((window[0] - oy) / grid)), min(ny, int((window[1] - oy) / grid) + 1)
        )
        starts = [(j, 0) for j in lanes]
        goal_col = nx - 1

    def ok(j: int, i: int) -> bool:
        if not (0 <= j < ny and 0 <= i < nx):
            return False
        if axis == "x" and not (window[0] <= ox + i * grid <= window[1]):
            return False
        if axis == "y" and not (window[0] <= oy + j * grid <= window[1]):
            return False
        return dist[j, i] >= min_clear

    # Dijkstra on cost = length penalized by tightness (prefers wide corridors,
    # then short paths — the widest-then-shortest CHARGE heuristic in one pass)
    def cost(j: int, i: int, diag: bool) -> float:
        step = grid * (math.sqrt(2) if diag else 1.0)
        tightness = max(0.0, 30.0 - dist[j, i])  # 0 when ≥30mm clear
        return step * (1.0 + 0.15 * tightness)

    best: dict[tuple[int, int], float] = {}
    prev: dict[tuple[int, int], tuple[int, int]] = {}
    pq: list[tuple[float, tuple[int, int]]] = []
    for s in starts:
        if ok(*s):
            best[s] = 0.0
            heapq.heappush(pq, (0.0, s))
    goal = None
    while pq:
        d, (j, i) = heapq.heappop(pq)
        if d > best.get((j, i), 1e18):
            continue
        if (axis == "x" and j == goal_row) or (axis == "y" and i == goal_col):
            goal = (j, i)
            break
        for dj in (-1, 0, 1):
            for di in (-1, 0, 1):
                if dj == 0 and di == 0:
                    continue
                nj, ni = j + dj, i + di
                if not ok(nj, ni):
                    continue
                nd = d + cost(nj, ni, dj != 0 and di != 0)
                if nd < best.get((nj, ni), 1e18):
                    best[(nj, ni)] = nd
                    prev[(nj, ni)] = (j, i)
                    heapq.heappush(pq, (nd, (nj, ni)))
    if goal is None:
        return None
    cells = [goal]
    while cells[-1] in prev:
        cells.append(prev[cells[-1]])
    cells.reverse()
    pts = [(ox + i * grid, oy + j * grid) for j, i in cells]
    # extend past the region so the seam fully separates the footprint
    if axis == "x":
        pts = [(pts[0][0], bounds[1] - 2 * grid)] + pts + [(pts[-1][0], bounds[3] + 2 * grid)]
    else:
        pts = [(bounds[0] - 2 * grid, pts[0][1])] + pts + [(pts[-1][0] + 0, pts[-1][1])]
        pts[-1] = (bounds[2] + 2 * grid, pts[-1][1])
    # light smoothing (keeps clearance: window is small vs corridor width)
    half = SMOOTH_WIN // 2
    sm = [
        (
            sum(p[0] for p in pts[max(0, k - half) : k + half + 1])
            / len(pts[max(0, k - half) : k + half + 1]),
            sum(p[1] for p in pts[max(0, k - half) : k + half + 1])
            / len(pts[max(0, k - half) : k + half + 1]),
        )
        for k in range(len(pts))
    ]
    sm[0], sm[-1] = pts[0], pts[-1]
    return sm


def seam_linestring(pts: list[Point2]) -> LineString:
    return LineString(pts)
