"""Verification gates. Part 1: the hard manifold audit + pinch healing.

Port of tools/make_3mf.py (CHARGE): every undirected edge of a closed mesh is
shared by exactly two triangles; degenerate triangles are build failures.
The audit runs on POSITION-WELDED topology — the same view a slicer's
non-manifold check sees — and it HARD-FAILS (warn-only once let defects ship;
lesson 10). heal_pinch_edges() is the principled repair for self-tangency
"pinch" edges: fan-split the sheets so indices separate while every written
coordinate stays identical (sliced result unchanged).
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

QUANT = 1e-6  # position-weld quantum, mm


class BuildError(Exception):
    """A verification gate failed. Fix the geometry; do not ship."""


def _weld(verts: np.ndarray, tris: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Merge vertices that share a quantized position; drop degenerate tris."""
    q = np.round(verts / QUANT).astype(np.int64)
    _, first_idx, inverse = np.unique(
        q.view([("x", np.int64), ("y", np.int64), ("z", np.int64)]).reshape(-1),
        return_index=True,
        return_inverse=True,
    )
    wtris = inverse[tris]
    keep = (
        (wtris[:, 0] != wtris[:, 1])
        & (wtris[:, 1] != wtris[:, 2])
        & (wtris[:, 0] != wtris[:, 2])
    )
    return verts[first_idx], wtris[keep]


def edge_report(verts: np.ndarray, tris: np.ndarray) -> dict:
    """Edge-topology census on position-welded geometry."""
    wverts, wtris = _weld(verts, tris)
    if len(wtris) == 0:
        return {"tris": 0, "boundary": 1, "pinch": 0, "degenerate": len(tris)}
    edges = np.concatenate([wtris[:, [0, 1]], wtris[:, [1, 2]], wtris[:, [2, 0]]])
    edges.sort(axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return {
        "tris": int(len(wtris)),
        "degenerate": int(len(tris) - len(wtris)),
        "boundary": int((counts == 1).sum()),
        "pinch": int((counts > 2).sum()),
    }


def audit_mesh(verts: np.ndarray, tris: np.ndarray, name: str = "mesh") -> None:
    """Hard gate: raise BuildError unless the welded mesh is 2-manifold."""
    r = edge_report(verts, tris)
    bad = r["boundary"] + r["pinch"]
    if bad or r["degenerate"]:
        raise BuildError(
            f"FAIL {name}: {r['boundary']} boundary edge(s), {r['pinch']} pinch "
            f"edge(s), {r['degenerate']} degenerate tri(s) — fix the geometry, "
            "do not ship (docs/LESSONS-FROM-CHARGE.md B10)"
        )


def heal_pinch_edges(
    verts: np.ndarray, tris: np.ndarray
) -> tuple[np.ndarray, np.ndarray, int]:
    """Fan-split pinch edges (>2 triangles on one position-edge) into separate
    sheets. Port of tools/make_3mf.py:18-100 — weld corners only through clean
    2-sided edges, then pair pinch-edge wings sheet-by-sheet via shared
    endpoint classes, iterating so pairing propagates along pinch chains.

    Returns (verts, tris, n_pinch_edges_healed); coordinates are unchanged.
    """
    wverts, wtris = _weld(verts, tris)
    ntri = len(wtris)
    corners_pos = wtris.reshape(-1)                     # welded position id per corner
    parent = list(range(3 * ntri))                      # union-find over corners

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    sides: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for t in range(ntri):
        for s in range(3):
            cu, cv = 3 * t + s, 3 * t + (s + 1) % 3
            u, v = corners_pos[cu], corners_pos[cv]
            side = (cu, cv) if u < v else (cv, cu)      # corners in key order
            sides[(min(u, v), max(u, v))].append(side)

    pinch_edges: list[list[tuple[int, int]]] = []
    for ss in sides.values():
        if len(ss) == 2:
            union(ss[0][0], ss[1][0])
            union(ss[0][1], ss[1][1])
        elif len(ss) > 2:
            pinch_edges.append(ss)

    if pinch_edges:
        changed = True
        while changed:
            changed = False
            for ss in pinch_edges:
                for slot in (0, 1):
                    groups: dict[int, list[tuple[int, int]]] = defaultdict(list)
                    for side in ss:
                        groups[find(side[slot])].append(side)
                    for g in groups.values():
                        if len(g) == 2:
                            oa, ob = g[0][1 - slot], g[1][1 - slot]
                            if find(oa) != find(ob):
                                union(oa, ob)
                                changed = True

    out_verts: list[np.ndarray] = []
    vid: dict[int, int] = {}
    out_tris = np.empty_like(wtris)
    for t in range(ntri):
        for s in range(3):
            c = 3 * t + s
            r = find(c)
            i = vid.get(r)
            if i is None:
                i = len(out_verts)
                vid[r] = i
                out_verts.append(wverts[corners_pos[c]])
            out_tris[t, s] = i
    return np.asarray(out_verts), out_tris, len(pinch_edges)


def gated_mesh(
    verts: np.ndarray, tris: np.ndarray, name: str = "mesh"
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Audit; heal what is principled to heal; hard-fail the rest.

    Returns export-ready (verts, tris, notes) — position-welded and free of
    zero-area facets. Degenerate tris that collapse UNDER THE WELD carry no
    surface (unlike dropping small-but-real soup triangles, which punches
    holes — deleted-healer lesson); we drop them and then REQUIRE the result
    to be 2-manifold. Pinch edges get the CHARGE fan-split. Anything else
    (boundary edges) is unshippable."""
    notes: list[str] = []
    r = edge_report(verts, tris)
    if r["pinch"] and not r["boundary"]:
        verts, tris, healed = heal_pinch_edges(verts, tris)
        notes.append(f"healed {name}: {healed} pinch edge(s) fan-split (geometry unchanged)")
        # after fan-split, audit UNwelded topology (welding would re-create the pinch)
        er = edge_report_indexed(tris)
        if er["boundary"] or er["pinch"] or er["degenerate"]:
            raise BuildError(f"FAIL {name}: unhealable after fan-split ({er})")
        return verts, tris, notes
    if r["boundary"] or r["pinch"]:
        audit_mesh(verts, tris, name)  # raises with the full message
    wverts, wtris = _weld(verts, tris)
    if r["degenerate"]:
        er = edge_report_indexed(wtris)
        if er["boundary"] or er["pinch"] or er["degenerate"]:
            raise BuildError(f"FAIL {name}: not manifold after weld ({er})")
        notes.append(
            f"welded {name}: {r['degenerate']} zero-area sliver tri(s) collapsed "
            "(sub-µm boolean seams; surface unchanged)"
        )
    return wverts, wtris, notes


def clearance_audit(
    strokes,
    min_gap: float,
    crisp_deg: float = 35.0,
    run_mm: float = 14.0,
    step: float = 2.0,
    self_skip_mm: float = 40.0,
) -> list[str]:
    """Channel-nesting audit (port of CHARGE tools/clearance_audit.py).

    Two bands need >= min_gap centerline separation UNLESS they meet at a crisp
    crossing (tangents > crisp_deg apart). Long parallel sub-gap runs are the
    rejected 'mush'. Returns human-readable violation strings.
    """
    import math as _m

    def _resample(p):
        out = [(p[0][0], p[0][1], 0.0)]
        acc = 0.0
        for i in range(len(p) - 1):
            ax, ay = p[i]
            bx, by = p[i + 1]
            d = _m.dist((ax, ay), (bx, by))
            if d == 0:
                continue
            n = max(1, int(d / step))
            for k in range(1, n + 1):
                t = k / n
                out.append((ax + (bx - ax) * t, ay + (by - ay) * t, acc + d * t))
            acc += d
        return out

    def _tangent(samples, i):
        j0, j1 = max(0, i - 2), min(len(samples) - 1, i + 2)
        dx = samples[j1][0] - samples[j0][0]
        dy = samples[j1][1] - samples[j0][1]
        n = _m.hypot(dx, dy) or 1.0
        return (dx / n, dy / n)

    paths = [
        (s.pts + [s.pts[0]] if s.closed else s.pts) for s in strokes if len(s.pts) >= 2
    ]
    sa = [_resample(p) for p in paths]
    closed_len = [
        s[-1][2] if _m.dist(s[0][:2], s[-1][:2]) < 0.1 else None for s in sa
    ]
    events = []
    for ai, A in enumerate(sa):
        for bi in range(ai, len(sa)):
            B = sa[bi]
            for i, (ax, ay, at) in enumerate(A):
                best = None
                for j, (bx, by, bt) in enumerate(B):
                    if ai == bi:
                        arc = abs(at - bt)
                        if closed_len[ai]:
                            arc = min(arc, closed_len[ai] - arc)
                        if arc < self_skip_mm:
                            continue
                    d = _m.dist((ax, ay), (bx, by))
                    if d < min_gap and (best is None or d < best[0]):
                        best = (d, j)
                if best:
                    ta = _tangent(A, i)
                    tb = _tangent(B, best[1])
                    dot = abs(ta[0] * tb[0] + ta[1] * tb[1])
                    ang = _m.degrees(_m.acos(max(-1, min(1, dot))))
                    events.append((ai, bi, best[0], ang, ax, ay, at))
    events.sort(key=lambda e: (e[0], e[1], e[6]))
    runs: list[dict] = []
    for ai, bi, d, ang, ax, ay, at in events:
        if runs and runs[-1]["a"] == ai and runs[-1]["b"] == bi and at - runs[-1]["end"] <= step * 1.5:
            r = runs[-1]
            r["run"] = at - r["start"]
            r["end"] = at
            if d < r["d"]:
                r["d"], r["ax"], r["ay"] = d, ax, ay
            r["angle"] = min(r["angle"], ang)
        else:
            runs.append(
                {"a": ai, "b": bi, "d": d, "angle": ang, "ax": ax, "ay": ay,
                 "run": 0.0, "start": at, "end": at}
            )
    return [
        f"channel clearance: {r['d']:.1f} mm gap (< {min_gap:.0f}) for {r['run']:.0f} mm "
        f"near ({r['ax']:.0f},{r['ay']:.0f}), tangents {r['angle']:.0f}° — parallel mush"
        for r in runs
        if r["angle"] < crisp_deg and r["run"] > run_mm
    ]


def coverage_qa(
    source_fills, band, max_mm2: float = 100.0, note_mm2: float = 60.0
) -> tuple[list[str], list[str]]:
    """Does the tube layout actually cover the source art? (Port of
    tools/qa_coverage.py intent, exact-geometry version.) The check the
    extractor never had: it validates against the ART, not its own graph."""
    from .geom2d import as_multipolygon

    fails: list[str] = []
    notes: list[str] = []
    if source_fills is None or source_fills.is_empty:
        return fails, notes
    missed = as_multipolygon(source_fills.difference(band))
    for p in missed.geoms:
        a = p.area
        if a < note_mm2:
            continue
        c = p.centroid
        msg = f"{a:.0f} mm² of source ink uncovered near ({c.x:.0f},{c.y:.0f})"
        (fails if a > max_mm2 else notes).append(msg)
    return fails, notes


def edge_report_indexed(tris: np.ndarray) -> dict:
    """Edge census trusting the given indexing (post-heal check)."""
    keep = (
        (tris[:, 0] != tris[:, 1])
        & (tris[:, 1] != tris[:, 2])
        & (tris[:, 0] != tris[:, 2])
    )
    t = tris[keep]
    edges = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    edges.sort(axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return {
        "degenerate": int(len(tris) - len(t)),
        "boundary": int((counts == 1).sum()),
        "pinch": int((counts > 2).sum()),
    }
