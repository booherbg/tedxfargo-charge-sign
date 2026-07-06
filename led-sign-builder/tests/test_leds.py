import math

import pytest

from signforge.leds import chord_chain, place_pixels
from signforge.model import Stroke
from signforge.params import SignParams


def _params(**leds):
    base = {"pitch_mm": 17.0}
    base.update(leds)
    return SignParams.model_validate({"leds": base})


def test_straight_run_equal_chords():
    s = Stroke(pts=[(0, 0), (170, 0)])
    plan = place_pixels([s], _params())
    assert plan.power.count == 11
    xs = sorted(p[0] for p in plan.pixels)
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    assert max(gaps) - min(gaps) < 0.2
    assert xs[0] == pytest.approx(0) and xs[-1] == pytest.approx(170)


def test_closed_loop_equal_arcs():
    n = 72
    r = 100
    pts = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    s = Stroke(pts=pts, closed=True)
    plan = place_pixels([s], _params())
    L = s.length()
    assert plan.power.count == round(L / 17)
    chords = [
        math.dist(plan.pixels[i], plan.pixels[(i + 1) % len(plan.pixels)])
        for i in range(len(plan.pixels))
    ]
    assert min(chords) > 14.8


def test_zigzag_respects_chord_floor():
    # raster-skeleton-like zigzag: arc length ≫ chord length (the R-leg lesson)
    pts = [(i * 4.0, 3.5 * (i % 2)) for i in range(40)]
    s = Stroke(pts=pts)
    plan = place_pixels([s], _params())
    chords = [math.dist(a, b) for a, b in zip(plan.pixels, plan.pixels[1:])]
    assert min(chords) >= 14.8


def test_parallel_strokes_too_close_get_audited():
    a = Stroke(pts=[(0, 0), (100, 0)])
    b = Stroke(pts=[(0, 10), (100, 10)])
    plan = place_pixels([a, b], _params())
    assert any("dropped" in m or "snug" in m for m in plan.audits)


def test_budget_overrun_flags():
    s = Stroke(pts=[(0, 0), (500, 0)])
    plan = place_pixels([s], _params(budget_px=10))
    assert plan.power.over_budget
    assert "BUDGET" in plan.audits[0]


def test_power_math():
    s = Stroke(pts=[(0, 0), (170, 0)])
    plan = place_pixels([s], _params())
    p = plan.power
    assert p.count == 11
    assert p.watts == pytest.approx(11 * 0.25)
    assert p.amps == pytest.approx(11 * 0.25 / 24, abs=0.01)
    assert p.psu_watts == 60
    assert p.strings == 1


def test_chord_chain_pins_ends():
    poly = [(0.0, 0.0), (50.0, 20.0), (100.0, 0.0)]
    pts = chord_chain(poly, 4)
    assert pts[0] == (0, 0) and pts[-1] == (100, 0)
    chords = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    assert max(chords) - min(chords) < 0.5
