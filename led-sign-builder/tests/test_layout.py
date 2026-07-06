import pytest

from signforge.ingest.fonts import text_to_artwork
from signforge.layout import build_layout
from signforge.params import SignParams


@pytest.fixture
def art(bungee):
    return text_to_artwork(bungee, "HI", cap_height_mm=80)


def test_layout_normalizes_to_origin(art):
    p = SignParams.model_validate({"style": {"backer": "none"}})
    lay = build_layout(art, p)
    assert lay.fills.bounds[0] == pytest.approx(0, abs=1e-6)
    assert lay.fills.bounds[1] == pytest.approx(0, abs=1e-6)


def test_tile_backer_bounds(art):
    p = SignParams.model_validate({"style": {"backer": "tile", "tile_margin_mm": 12}})
    lay = build_layout(art, p)
    x0, y0, x1, y1 = lay.backer.bounds
    ax0, ay0, ax1, ay1 = lay.fills.bounds
    assert (x0, y0) == pytest.approx((ax0 - 12, ay0 - 12))
    assert (x1, y1) == pytest.approx((ax1 + 12, ay1 + 12))


def test_contour_backer_contains_art(art):
    p = SignParams.model_validate({"style": {"backer": "contour"}})
    lay = build_layout(art, p)
    assert lay.backer is not None
    assert lay.backer.buffer(0.01).contains(lay.fills)
