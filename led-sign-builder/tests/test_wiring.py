import math

import pytest

from signforge.leds import chain_hops, chain_length_mm, place_pixels
from signforge.model import Stroke
from signforge.params import SignParams


def _params(**leds):
    base = {"pitch_mm": 17.0}
    base.update(leds)
    return SignParams.model_validate({"leds": base})


def test_seam_split_places_evenly_per_segment():
    s = Stroke(pts=[(0, 0), (170, 0)])
    plan = place_pixels([s], _params(), seams=[("x", 85.0)])
    xs = sorted(p[0] for p in plan.pixels)
    assert all(abs(x - 85.0) >= 12.49 for x in xs)         # keepout by construction
    left = [x for x in xs if x < 85]
    right = [x for x in xs if x > 85]
    assert left and right
    for side in (left, right):
        gaps = [b - a for a, b in zip(side, side[1:])]
        # uniform per segment (within the 0.25mm densify quantum per hop)
        assert not gaps or max(gaps) - min(gaps) <= 0.75
        assert all(g >= 14.8 for g in gaps)
    assert not any("dropped" in a for a in plan.audits)


def test_closed_loop_seam_split_wraps():
    n = 96
    r = 60
    pts = [
        (85 + r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]
    s = Stroke(pts=pts, closed=True)
    plan = place_pixels([s], _params(), seams=[("x", 85.0)])
    assert plan.power.count >= 10
    assert all(abs(p[0] - 85.0) >= 12.4 for p in plan.pixels)


def test_chain_order_and_jumpers():
    a = Stroke(pts=[(0, 0), (100, 0)])
    b = Stroke(pts=[(250, 0), (350, 0)])   # 150mm hop between strokes
    plan = place_pixels([a, b], _params())
    hops = chain_hops(plan.pixels, plan.per_stroke)
    assert len(hops) == plan.power.count - 1
    jumpers = [h for h in hops if h[2]]
    assert len(jumpers) == 1
    assert any("jumper" in m for m in plan.audits)
    total = chain_length_mm(plan.pixels, plan.per_stroke)
    assert total == pytest.approx(100 + 150 + 100, rel=0.02)


def test_wiring_in_preview_and_bom(tmp_path, bungee):
    from signforge.params import SignParams
    from signforge.pipeline import build

    params = SignParams.model_validate(
        {
            "name": "wire",
            "content": {"text": "SO", "cap_height_mm": 120.0, "font_path": bungee},
            "style": {"kind": "neon", "backer": "tile"},
            "texture": {"mode": "none"},
        }
    )
    build(params, tmp_path / "out")
    html = (tmp_path / "out" / "preview" / "index.html").read_text()
    assert "DATA IN" in html and "#66d19e" in html
    bom = (tmp_path / "out" / "BOM.md").read_text()
    assert "data chain" in bom and "jumper" in bom
