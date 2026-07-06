import math

import pytest
from shapely.geometry import LineString, Point

from signforge.geom2d import heal
from signforge.model import Stroke
from signforge.skeleton import extract_centerlines


def test_annulus_gives_one_closed_loop():
    ring = heal(Point(0, 0).buffer(30, quad_segs=48).difference(Point(0, 0).buffer(22, quad_segs=48)))
    strokes, meta = extract_centerlines(ring)
    assert len(strokes) == 1 and strokes[0].closed
    L = strokes[0].length()
    assert L == pytest.approx(2 * math.pi * 26, rel=0.06)
    assert meta["tube_w"] == pytest.approx(8.0, abs=1.5)


def test_s_curve_gives_one_open_stroke():
    pts = [(t * 8, 25 * math.sin(t / 2.2)) for t in range(26)]
    tube = heal(LineString(pts).buffer(5, quad_segs=16))
    strokes, meta = extract_centerlines(tube)
    assert len(strokes) == 1 and not strokes[0].closed
    true_len = LineString(pts).length
    assert strokes[0].length() == pytest.approx(true_len, rel=0.08)


def test_crossing_bars_pass_through_junction():
    h = heal(LineString([(-60, 0), (60, 0)]).buffer(5))
    v = heal(LineString([(0, -60), (0, 60)]).buffer(5))
    strokes, _ = extract_centerlines(heal(h.union(v)))
    # straightest-continuation pairing: two full bars, not four stubs
    assert len(strokes) == 2
    lengths = sorted(s.length() for s in strokes)
    assert lengths[0] == pytest.approx(120, rel=0.06)
    assert lengths[1] == pytest.approx(120, rel=0.06)


def test_short_spur_is_pruned():
    bar = LineString([(0, 0), (100, 0)]).buffer(5)
    spur = LineString([(50, 5), (50, 11)]).buffer(4)  # 6mm stub off the side
    strokes, _ = extract_centerlines(heal(bar.union(spur)))
    assert len(strokes) == 1
    assert strokes[0].length() == pytest.approx(100, rel=0.08)


def test_font_glyphs_neonize(bungee):
    from signforge.ingest.fonts import text_to_artwork

    art = text_to_artwork(bungee, "S", cap_height_mm=120)
    strokes, meta = extract_centerlines(art.fills)
    assert len(strokes) == 1 and not strokes[0].closed
    assert meta["tube_w"] > 10  # Bungee is chunky

    art_o = text_to_artwork(bungee, "O", cap_height_mm=120)
    strokes_o, _ = extract_centerlines(art_o.fills)
    assert len(strokes_o) == 1 and strokes_o[0].closed
