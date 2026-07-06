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
    """Audit; on pinch-only failure attempt the principled heal, re-audit.
    Returns export-ready (verts, tris, notes). Raises BuildError if unhealable."""
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
    audit_mesh(verts, tris, name)
    return verts, tris, notes


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
