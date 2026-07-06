import math

import numpy as np
import pytest

from signforge.geom2d import bbox_polygon, heal
from signforge.solids import cylinder, heightfield, mesh_of, prism, revolve_profile
from signforge.verify import BuildError, audit_mesh


def test_prism_square_volume_and_z():
    man = prism(heal(bbox_polygon(0, 0, 10, 10)), z0=2, z1=5)
    assert man.volume() == pytest.approx(300.0)
    v, t = mesh_of(man)
    assert v[:, 2].min() == pytest.approx(2.0) and v[:, 2].max() == pytest.approx(5.0)
    audit_mesh(v, t, "prism")


def test_prism_donut_volume():
    donut = heal(bbox_polygon(0, 0, 20, 20).difference(bbox_polygon(5, 5, 15, 15)))
    man = prism(donut, 0, 3)
    assert man.volume() == pytest.approx((400 - 100) * 3)


def test_cylinder_volume():
    man = cylinder(d=12.3, h=2.0, cx=5, cy=5, z0=0)
    n = 72
    poly_area = 0.5 * n * (12.3 / 2) ** 2 * math.sin(2 * math.pi / n)
    assert man.volume() == pytest.approx(poly_area * 2.0, rel=1e-6)


def test_revolve_collar_ring():
    # rectangle r in [5, 8], z in [0, 2] -> washer
    man = revolve_profile([(5, 0), (8, 0), (8, 2), (5, 2)], cx=0, cy=0, z0=0)
    n = 72
    k = 0.5 * n * math.sin(2 * math.pi / n)  # polygonized circle factor
    assert man.volume() == pytest.approx((k * 64 - k * 25) * 2, rel=1e-6)
    v, t = mesh_of(man)
    audit_mesh(v, t, "collar")


def test_heightfield_flat_grid_volume_and_manifold():
    grid = np.full((5, 5), 2.0)
    man = heightfield(grid, cell=1.0, origin=(0, 0), z_base=10.0)
    assert man.volume() == pytest.approx(4 * 4 * 2.0)
    v, t = mesh_of(man)
    assert v[:, 2].min() == pytest.approx(10.0)
    audit_mesh(v, t, "heightfield")


def test_heightfield_bumpy_is_manifold():
    rng = np.random.default_rng(7)
    grid = 0.17 + rng.uniform(0, 0.6, size=(40, 60))
    man = heightfield(grid, cell=0.667, origin=(-3, -2), z_base=21.0)
    v, t = mesh_of(man)
    audit_mesh(v, t, "fuzz-field")
    assert man.volume() > 40 * 60 * 0.667**2 * 0.17 * 0.9


def test_heightfield_rejects_nonpositive():
    with pytest.raises(BuildError):
        heightfield(np.zeros((3, 3)), 1.0, (0, 0), 0.0)
