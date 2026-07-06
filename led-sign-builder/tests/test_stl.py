import numpy as np
import pytest

from signforge.export.stl import export_mesh, read_stl, write_stl
from signforge.geom2d import bbox_polygon, heal
from signforge.solids import mesh_of, prism
from signforge.verify import audit_mesh


def _signed_volume(verts, tris):
    p0, p1, p2 = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    return float(np.einsum("ij,ij->i", p0, np.cross(p1, p2)).sum() / 6.0)


def test_stl_round_trip_cube(tmp_path):
    man = prism(heal(bbox_polygon(0, 0, 10, 10)), 0, 10)
    v, t = mesh_of(man)
    path = tmp_path / "cube.stl"
    write_stl(path, v, t)
    rv, rt = read_stl(path)
    assert len(rt) == len(t)
    assert _signed_volume(rv, rt) == pytest.approx(1000.0, rel=1e-5)
    audit_mesh(rv, rt, "round-trip")   # weld-based audit closes the soup


def test_export_mesh_gates_and_writes(tmp_path):
    man = prism(heal(bbox_polygon(0, 0, 5, 8)), 0, 2)
    path = tmp_path / "part.stl"
    verts, tris, notes = export_mesh(path, man, "part")
    assert path.stat().st_size == 84 + 50 * len(tris)
    assert notes == []
