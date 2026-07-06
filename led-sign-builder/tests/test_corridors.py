import pytest
from shapely.geometry import LineString, Point

from signforge.corridors import route_corridor
from signforge.geom2d import band, heal
from signforge.model import Stroke


def test_route_threads_between_two_blobs():
    # two fat tubes with a 40mm dark gap at x≈150
    left = band([Stroke(pts=[(20, 20), (130, 180)])], 22)
    right = band([Stroke(pts=[(170, 20), (280, 180)])], 22)
    obstacle = heal(left.union(right))
    pts = route_corridor((0, 0, 300, 200), obstacle, axis="x", window=(60, 240))
    assert pts is not None
    seam = LineString(pts)
    assert seam.distance(obstacle) >= 5.0 - 0.01     # never grazes a channel
    assert pts[0][1] < 0 and pts[-1][1] > 200        # fully separates the region


def test_route_dodges_a_diagonal():
    # a diagonal bar forces the seam to weave around its ends? No — blocked
    # full-width diagonal → no vertical corridor at all
    bar = band([Stroke(pts=[(0, 100), (300, 100)])], 22)
    pts = route_corridor((0, 0, 300, 200), heal(bar), axis="x", window=(40, 260))
    assert pts is None                                # honest failure, no graze


def test_route_open_field_prefers_window():
    from shapely.geometry import MultiPolygon

    pts = route_corridor((0, 0, 300, 200), MultiPolygon([]), axis="x", window=(100, 200))
    assert pts is not None
    xs = [p[0] for p in pts[1:-1]]
    assert all(100 <= x <= 200 for x in xs)


def test_panelize_falls_back_to_corridor_on_staggered_tubes():
    """Every straight lane crosses a tube; the seam must snake between them."""
    from signforge.geom2d import bbox_polygon
    from signforge.panelize import panelize
    from signforge.params import SignParams

    a = Stroke(pts=[(0, 60), (380, 60)])
    b = Stroke(pts=[(320, 140), (700, 140)])
    strokes = [a, b]
    obstacle = band(strokes, 22)
    foot = bbox_polygon(0, 0, 700, 200)
    p = SignParams.model_validate({"printer": {"preset": "bambu-h2d-dual"}})
    pieces, seams, warns = panelize(foot, strokes, [], p, avoid=obstacle)
    assert len(pieces) >= 2 and seams
    assert any("corridor" in w for w in warns)
    wiggly = [s for s in seams if len({round(x, 1) for x, _ in s.coords}) > 3]
    assert wiggly, "expected at least one non-straight seam"
    for s in wiggly:
        assert s.distance(obstacle) >= 5.0 - 0.01   # never grazes a channel
