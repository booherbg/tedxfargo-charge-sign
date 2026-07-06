import numpy as np
import pytest

from signforge.geom2d import band
from signforge.model import Stroke
from signforge.params import SignParams
from signforge.solids import mesh_of, prism
from signforge.textures import FLOOR, fuzz_grid, textured_lens_top
from signforge.verify import gated_mesh


def test_grid_invariants_pyramid_jitter():
    grid, step = fuzz_grid("pyramid_jitter", 2.0, 0.6, seed=7, area_xy=(60, 25))
    assert step == pytest.approx(2.0 / 3)
    assert grid.min() >= FLOOR - 1e-9
    assert grid.max() <= 0.6 + 1e-9
    assert grid.max() > 0.4                      # peaks actually reach up
    # no cliffs: max-union tents are continuous — adjacent samples can't jump
    # more than one tent slope step (2*h/cell * step) plus jitter slack
    dy = np.abs(np.diff(grid, axis=0)).max()
    dx = np.abs(np.diff(grid, axis=1)).max()
    assert max(dx, dy) < 0.6 * 0.8


def test_grid_random_floor():
    grid, step = fuzz_grid("random", 1.5, 0.8, seed=3, area_xy=(30, 20))
    assert step == 1.5
    assert grid.min() >= FLOOR


@pytest.mark.parametrize("mode", ["pyramid_jitter", "random"])
@pytest.mark.parametrize("seed", [7, 8])
def test_textured_lens_is_manifold(mode, seed):
    params = SignParams.model_validate(
        {"texture": {"mode": mode, "cell_mm": 2.0, "height_mm": 0.6, "seed": seed}}
    )
    b = band([Stroke(pts=[(0, 0), (60, 0), (60, 30)])], 22.0)
    z_top = 21.0
    flat = prism(b, z_top - 1.2, z_top)
    tex = textured_lens_top(b, z_top, params, seed, fuse=0.1)
    lens = flat + tex
    v, t = mesh_of(lens)
    gv, gt, notes = gated_mesh(v, t, f"lens-{mode}-{seed}")
    vol_flat = flat.volume()
    assert lens.volume() > vol_flat
    assert lens.volume() < vol_flat + b.area * (0.6 + 0.1 + 0.02)
    bb = lens.bounding_box()
    assert bb[5] <= z_top + 0.6 + 0.13   # peaks ≈ hmax + fuse + standoff above top
