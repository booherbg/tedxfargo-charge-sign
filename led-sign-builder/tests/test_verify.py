import numpy as np
import pytest

from signforge.verify import (
    BuildError,
    audit_mesh,
    edge_report_indexed,
    gated_mesh,
    heal_pinch_edges,
)

# One tetra with verified outward winding.
TETRA_V = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
TETRA_T = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], dtype=np.int64)


def _two_tetras_sharing_edge():
    """Second tetra = first rotated 180° about the x-axis; shares edge (0,0,0)-(1,0,0)."""
    rot = TETRA_V * np.array([1, -1, -1])
    verts = np.concatenate([TETRA_V, rot])
    tris = np.concatenate([TETRA_T, TETRA_T + 4])
    return verts, tris


def test_clean_tetra_passes():
    audit_mesh(TETRA_V, TETRA_T, "tetra")


def test_open_mesh_fails():
    with pytest.raises(BuildError, match="boundary"):
        audit_mesh(TETRA_V, TETRA_T[:3], "open-tetra")


def test_degenerate_tri_fails():
    tris = np.concatenate([TETRA_T, [[0, 0, 1]]])
    with pytest.raises(BuildError):
        audit_mesh(TETRA_V, tris, "degenerate")


def test_pinch_edge_detected_and_healed():
    verts, tris = _two_tetras_sharing_edge()
    with pytest.raises(BuildError, match="pinch"):
        audit_mesh(verts, tris, "pinched")

    hv, ht, n = heal_pinch_edges(verts, tris)
    assert n == 1
    rep = edge_report_indexed(ht)
    assert rep == {"degenerate": 0, "boundary": 0, "pinch": 0}
    # sheets separated: the two shared-position vertices are duplicated
    assert len(hv) == 8


def test_gated_mesh_heals_pinch_and_reports():
    verts, tris = _two_tetras_sharing_edge()
    gv, gt, notes = gated_mesh(verts, tris, "pinched")
    assert len(notes) == 1 and "fan-split" in notes[0]
    assert edge_report_indexed(gt) == {"degenerate": 0, "boundary": 0, "pinch": 0}
