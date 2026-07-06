import math

import pytest
from shapely.geometry import Polygon

from signforge.geom2d import band, bbox_polygon, heal, ring_offset, rings
from signforge.model import Stroke


def test_heal_bowtie_self_intersection():
    bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2)])
    assert not bowtie.is_valid
    fixed = heal(bowtie)
    assert fixed.is_valid and fixed.area == pytest.approx(2.0)  # two unit triangles


def test_heal_drops_slivers():
    big = bbox_polygon(0, 0, 10, 10)
    sliver = Polygon([(20, 0), (20.004, 0), (20.004, 1), (20, 1)])  # 0.004 mm2
    healed = heal(big.union(sliver))
    assert len(healed.geoms) == 1


def test_band_straight_stroke_area():
    s = Stroke(pts=[(0.0, 0.0), (100.0, 0.0)], closed=False)
    b = band([s], width=10.0)
    expect = 100 * 10 + math.pi * 5**2  # rect + two round caps
    assert b.area == pytest.approx(expect, rel=0.015)


def test_band_closed_ring_has_hole():
    sq = Stroke(pts=[(0, 0), (100, 0), (100, 100), (0, 100)], closed=True)
    b = band([sq], width=10.0)
    assert len(b.geoms) == 1 and len(b.geoms[0].interiors) == 1


def test_ring_offset_shrink_exact_for_square():
    sq = heal(bbox_polygon(0, 0, 20, 20))
    small = ring_offset(sq, -2.0)
    assert small.area == pytest.approx(16 * 16, rel=1e-6)


def test_rings_orientation_convention():
    donut = heal(bbox_polygon(0, 0, 20, 20).difference(bbox_polygon(5, 5, 15, 15)))
    rs = rings(donut)
    assert len(rs) == 2

    def signed_area(r):
        x, y = r[:, 0], r[:, 1]
        return 0.5 * float((x * (list(y[1:]) + [y[0]]) - y * (list(x[1:]) + [x[0]])).sum())

    assert signed_area(rs[0]) > 0   # shell CCW
    assert signed_area(rs[1]) < 0   # hole CW
