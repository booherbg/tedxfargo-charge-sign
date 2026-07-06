"""Environment smoke: the geometry stack imports and does real work."""

import numpy as np


def test_manifold_boolean_roundtrip():
    import manifold3d as m3d

    cube = m3d.Manifold.cube([10.0, 10.0, 10.0])
    sphere = m3d.Manifold.sphere(6.0, 48).translate([10.0, 10.0, 10.0])
    union = cube + sphere
    assert union.volume() > cube.volume() > 0
    mesh = union.to_mesh()
    verts = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    tris = np.asarray(mesh.tri_verts, dtype=np.int64)
    assert len(verts) > 8 and len(tris) > 12


def test_shapely_and_fonttools_present():
    import fontTools  # noqa: F401
    from shapely.geometry import Polygon

    sq = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    assert abs(sq.buffer(1.0).area - sq.area) > 0
