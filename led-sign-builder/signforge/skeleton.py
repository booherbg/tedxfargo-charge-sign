"""Filled 2D art -> tube centerlines. Port of CHARGE tools/centerline.py.

raster (even-odd scanline) -> Zhang-Suen thinning (vectorized) -> skeleton
graph decomposition: degree!=2 pixels cluster into nodes; short dangling edges
(spurs, ZS tip clumps) and short junction-junction "rungs" (sliver bridges
where art kisses) are dropped; surviving edge-ends pair by STRAIGHTEST
CONTINUATION so tubes that merely touch pass through crossings independently.
Prune thresholds auto-scale with the measured tube width. Always eyeball the
debug overlay (lesson 14).
"""

from __future__ import annotations

import math

import numpy as np
from shapely.geometry import MultiPolygon

from .geom2d import as_multipolygon
from .model import Stroke

# P2..P9 clockwise (image convention; orientation-consistent is all that matters)
N8 = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]


def rasterize(
    mpoly: MultiPolygon, px_per_mm: float, pad_mm: float = 2.0
) -> tuple[np.ndarray, tuple[float, float]]:
    """Even-odd scanline fill. Returns (ink[ny, nx] bool, origin_mm).
    Pixel (i, j) center is at origin + ((i + .5)/ppm, (j + .5)/ppm)."""
    mp = as_multipolygon(mpoly)
    x0, y0, x1, y1 = mp.bounds
    ox, oy = x0 - pad_mm, y0 - pad_mm
    nx = int(math.ceil((x1 - x0 + 2 * pad_mm) * px_per_mm)) + 1
    ny = int(math.ceil((y1 - y0 + 2 * pad_mm) * px_per_mm)) + 1

    ea, eb = [], []
    for p in mp.geoms:
        for ring in [p.exterior, *p.interiors]:
            c = (np.asarray(ring.coords, dtype=np.float64) - (ox, oy)) * px_per_mm
            ea.append(c[:-1])
            eb.append(c[1:])
    A = np.concatenate(ea)
    B = np.concatenate(eb)
    ink = np.zeros((ny, nx), dtype=bool)
    ay, by = A[:, 1], B[:, 1]
    for j in range(ny):
        y = j + 0.5
        m = ((ay <= y) & (y < by)) | ((by <= y) & (y < ay))
        if not m.any():
            continue
        a, b = A[m], B[m]
        t = (y - a[:, 1]) / (b[:, 1] - a[:, 1])
        xs = np.sort(a[:, 0] + t * (b[:, 0] - a[:, 0]))
        for k in range(0, len(xs) - 1, 2):
            i0 = max(0, int(math.ceil(xs[k] - 0.5)))
            i1 = min(nx - 1, int(math.floor(xs[k + 1] - 0.5)))
            if i1 >= i0:
                ink[j, i0 : i1 + 1] = True
    return ink, (ox, oy)


def thin(ink: np.ndarray) -> np.ndarray:
    """Zhang-Suen thinning, batch-per-phase (exact port, vectorized)."""
    S = np.pad(ink.copy(), 1)

    def shifted(k):
        dx, dy = N8[k]
        return S[1 + dy : S.shape[0] - 1 + dy, 1 + dx : S.shape[1] - 1 + dx]

    while True:
        removed = 0
        for phase in (0, 1):
            n = [shifted(k) for k in range(8)]
            core = S[1:-1, 1:-1]
            B = sum(x.astype(np.int8) for x in n)
            ring = n + [n[0]]
            Acnt = sum((~ring[i] & ring[i + 1]).astype(np.int8) for i in range(8))
            if phase == 0:
                cond = ~(n[0] & n[2] & n[4]) & ~(n[2] & n[4] & n[6])
            else:
                cond = ~(n[0] & n[2] & n[6]) & ~(n[0] & n[4] & n[6])
            kill = core & (B >= 2) & (B <= 6) & (Acnt == 1) & cond
            k = int(kill.sum())
            if k:
                core[kill] = False
                removed += k
        if not removed:
            return S[1:-1, 1:-1]


def _neighbors(p, S):
    x, y = p
    return [(x + dx, y + dy) for dx, dy in N8 if (x + dx, y + dy) in S]


def _components(S):
    S, comps = set(S), []
    while S:
        seed = next(iter(S))
        comp, stack = {seed}, [seed]
        while stack:
            for n in _neighbors(stack.pop(), comp | S):
                if n in S and n not in comp:
                    comp.add(n)
                    stack.append(n)
        comps.append(comp)
        S -= comp
    return comps


def _plen(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def decompose(S, mm_px, spur_mm=6.0, rung_mm=9.0, min_mm=30.0):
    """Skeleton pixel set -> ordered centerline segments [(pts, closed)].
    Faithful port of centerline.py:117-229 (see module docstring)."""
    segments = []
    for comp in _components(S):
        nodepx = {p for p in comp if len(_neighbors(p, comp)) != 2}
        if not nodepx:  # pure cycle
            start = next(iter(comp))
            prev, cur, pts = None, start, [start]
            while True:
                nxt = [n for n in _neighbors(cur, comp) if n != prev][0]
                if nxt == start:
                    break
                pts.append(nxt)
                prev, cur = cur, nxt
            segments.append((pts, True))
            continue
        clusters = _components(nodepx)
        cid = {p: i for i, c in enumerate(clusters) for p in c}
        edges, seen = [], set()
        for c in clusters:
            for p in c:
                for n in _neighbors(p, comp):
                    if n in cid or (p, n) in seen:
                        continue
                    pts, prev, cur = [p, n], p, n
                    while cur not in cid:
                        nxt = [q for q in _neighbors(cur, comp) if q != prev][0]
                        pts.append(nxt)
                        prev, cur = cur, nxt
                    seen.add((pts[0], pts[1]))
                    seen.add((pts[-1], pts[-2]))
                    edges.append(pts)
        # drop spurs (short + a dead end) and rungs (short junction-junction), iteratively
        while True:
            nedges: dict[int, int] = {}
            for e in edges:
                for cl in (cid[e[0]], cid[e[-1]]):
                    nedges[cl] = nedges.get(cl, 0) + 1
            drop = []
            for e in edges:
                L = _plen(e) * mm_px
                da = nedges[cid[e[0]]] == 1
                db = nedges[cid[e[-1]]] == 1
                if (da or db) and L < spur_mm:
                    drop.append(e)
                elif nedges[cid[e[0]]] >= 3 and nedges[cid[e[-1]]] >= 3 and L < rung_mm:
                    drop.append(e)  # sliver rung between REAL junctions
            if not drop:
                break
            edges = [e for e in edges if e not in drop]
        if not edges:
            continue

        def outdir(e, side):
            a = e[0] if side == 0 else e[-1]
            b = e[min(6, len(e) - 1)] if side == 0 else e[max(-7, -len(e))]
            d = math.dist(a, b) or 1.0
            return ((b[0] - a[0]) / d, (b[1] - a[1]) / d)

        at: dict[int, list[tuple[int, int]]] = {}
        for ei, e in enumerate(edges):
            at.setdefault(cid[e[0]], []).append((ei, 0))
            at.setdefault(cid[e[-1]], []).append((ei, 1))
        link: dict[tuple[int, int], tuple[int, int]] = {}
        for cl, ends in at.items():
            free = list(ends)
            while len(free) >= 2:
                best, bi, bj = 2.0, None, None
                for i in range(len(free)):
                    for j in range(i + 1, len(free)):
                        di = outdir(edges[free[i][0]], free[i][1])
                        dj = outdir(edges[free[j][0]], free[j][1])
                        dot = di[0] * dj[0] + di[1] * dj[1]
                        if dot < best:
                            best, bi, bj = dot, i, j
                if best >= 0.3:  # nothing continues straight enough
                    break
                link[free[bi]] = free[bj]
                link[free[bj]] = free[bi]
                free.pop(bj)
                free.pop(bi)
        visited = set()

        def run(ei, entry):
            pts = []
            while True:
                visited.add(ei)
                e = edges[ei] if entry == 0 else edges[ei][::-1]
                pts.extend(e)
                exit_end = (ei, 1 - entry)
                if exit_end not in link:
                    return pts, False
                nei, nside = link[exit_end]
                if nei in visited:
                    return pts, True  # closed the loop
                ei, entry = nei, nside

        for ei in range(len(edges)):
            if ei in visited:
                continue
            side = 0 if (ei, 0) not in link else (1 if (ei, 1) not in link else None)
            if side is not None:
                pts, closed = run(ei, side)
                segments.append((pts, closed))
        for ei in range(len(edges)):  # remaining = pure cycles via links
            if ei not in visited:
                pts, _ = run(ei, 0)
                segments.append((pts, True))
    return [(pts, cl) for pts, cl in segments if _plen(pts) * mm_px >= min_mm]


def smooth(pts, win, closed):
    n, half = len(pts), win // 2
    outp = []
    for i in range(n):
        if closed:
            w = [pts[(i + j) % n] for j in range(-half, half + 1)]
        else:
            w = pts[max(0, i - half) : min(n, i + half + 1)]
        outp.append((sum(p[0] for p in w) / len(w), sum(p[1] for p in w) / len(w)))
    return outp


def path_len(pts, closed):
    L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    return L + (math.dist(pts[-1], pts[0]) if closed else 0)


def resample(pts, step, closed):
    """Even respacing at ~step. Open: includes BOTH endpoints. Closed: N=round(L/step)."""
    L = path_len(pts, closed)
    if closed:
        n = max(3, round(L / step))
        targets = [i * L / n for i in range(n)]
        src = pts + [pts[0]]
    else:
        n = max(2, round(L / step) + 1)
        targets = [i * L / (n - 1) for i in range(n)]
        src = pts
    outp, acc, i = [], 0.0, 0
    for t in targets:
        while i < len(src) - 2 and acc + math.dist(src[i], src[i + 1]) < t:
            acc += math.dist(src[i], src[i + 1])
            i += 1
        d = math.dist(src[i], src[i + 1])
        f = (t - acc) / d if d > 1e-9 else 0
        f = min(max(f, 0.0), 1.0)
        outp.append(
            (
                src[i][0] + (src[i + 1][0] - src[i][0]) * f,
                src[i][1] + (src[i + 1][1] - src[i][1]) * f,
            )
        )
    return outp


def _extend_open_ends(pts, ink, origin, px_per_mm, tube_w):
    """March each open end along its tangent to the ink tip's cap center.

    ZS thinning erodes rounded tube ends by ~tube_w/2 (the A/G truncations that
    CHARGE hand-repaired). Extending to (ink boundary − tube_w/2) restores the
    true end: the round band cap then lands exactly on the art tip."""
    ox, oy = origin
    ny, nx = ink.shape

    def inside(p):
        i = int((p[0] - ox) * px_per_mm)
        j = int((p[1] - oy) * px_per_mm)
        return 0 <= i < nx and 0 <= j < ny and bool(ink[j, i])

    out = list(pts)
    for end in (0, 1):
        seq = out if end else out[::-1]
        a, b = seq[-2], seq[-1]
        d = math.dist(a, b) or 1.0
        u = ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
        step, marched = 0.4, 0.0
        p = b
        while marched < 4 * tube_w:
            q = (p[0] + u[0] * step, p[1] + u[1] * step)
            if not inside(q):
                break
            p, marched = q, marched + step
        ext = marched - tube_w / 2
        if ext > 0.3:
            tip = (b[0] + u[0] * ext, b[1] + u[1] * ext)
            if end:
                out.append(tip)
            else:
                out.insert(0, tip)
    return out


def extract_centerlines(
    mpoly: MultiPolygon,
    px_per_mm: float = 2.4,
    spur_mm: float | None = None,
    rung_mm: float | None = None,
    min_path_mm: float | None = None,
    step_mm: float = 4.0,
) -> tuple[list[Stroke], dict]:
    """Filled art -> centerline Strokes (mm) + meta (measured tube width etc.)."""
    ink, (ox, oy) = rasterize(mpoly, px_per_mm)
    skel = thin(ink)
    mm_px = 1.0 / px_per_mm
    skel_set = {(int(x), int(y)) for y, x in np.argwhere(skel)}
    if not skel_set:
        return [], {"tube_w": 0.0, "ink_mm2": 0.0}

    ink_mm2 = float(ink.sum()) * mm_px * mm_px
    skel_len0 = len(skel_set) * mm_px  # rough first-cut length estimate
    w_est = ink_mm2 / max(skel_len0, 1e-6)

    spur = spur_mm if spur_mm is not None else min(8.0, max(2.0, 0.55 * w_est))
    rung = rung_mm if rung_mm is not None else min(12.0, max(3.0, 0.85 * w_est))
    # clamp: ultra-bold fonts measure huge "tube" widths; 2.6*w would prune
    # real strokes (Bungee N's verticals). 45 mm keeps them; debris still dies.
    min_path = min_path_mm if min_path_mm is not None else max(6.0, min(2.6 * w_est, 45.0))

    traced = decompose(skel_set, mm_px, spur_mm=spur, rung_mm=rung, min_mm=min_path)
    if not traced:
        return [], {"tube_w": w_est, "ink_mm2": ink_mm2}

    win = max(3, int(2.0 * px_per_mm) | 1)  # ~2 mm moving average, odd
    strokes: list[Stroke] = []
    total = 0.0
    for pts, closed in traced:
        mm = [
            (ox + (p[0] + 0.5) * mm_px, oy + (p[1] + 0.5) * mm_px)
            for p in smooth(pts, win, closed)
        ]
        fine = resample(mm, 1.5, closed)
        if not closed and len(fine) >= 2:
            fine = _extend_open_ends(fine, ink, (ox, oy), px_per_mm, w_est)
        geo = resample(fine, step_mm, closed)
        strokes.append(Stroke(pts=geo, width=None, closed=closed))
        total += path_len(fine, closed)

    meta = {
        "tube_w": ink_mm2 / max(total, 1e-6),  # measured original tube width
        "ink_mm2": ink_mm2,
        "total_len_mm": total,
        "prune": {"spur": spur, "rung": rung, "min_path": min_path},
    }
    return strokes, meta


def debug_overlay(
    mpoly: MultiPolygon,
    strokes: list[Stroke],
    pixels: list[tuple[float, float]],
    path: str,
    px_per_mm: float = 2.4,
) -> None:
    """Ink gray, centerlines red, pixels blue — the 'always eyeball it' artifact."""
    from PIL import Image, ImageDraw

    ink, (ox, oy) = rasterize(mpoly, px_per_mm)
    ny, nx = ink.shape
    img = Image.new("RGB", (nx, ny), (255, 255, 255))
    arr = np.array(img)
    arr[ink] = (208, 208, 208)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)

    def to_px(p):
        return ((p[0] - ox) * px_per_mm, (p[1] - oy) * px_per_mm)

    for s in strokes:
        pts = s.pts + ([s.pts[0]] if s.closed else [])
        draw.line([to_px(p) for p in pts], fill=(220, 0, 0), width=2)
    for p in pixels:
        x, y = to_px(p)
        draw.rectangle([x - 3, y - 3, x + 3, y + 3], fill=(0, 0, 220))
    img.transpose(Image.FLIP_TOP_BOTTOM).save(path)  # math y-up -> image y-down
