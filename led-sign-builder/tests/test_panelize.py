import zipfile

from shapely.geometry import Point

from signforge.geom2d import band, bbox_polygon
from signforge.model import Stroke
from signforge.panelize import assign_pixels, panelize
from signforge.params import SignParams


def _params(**over):
    cfg = {"printer": {"preset": "bambu-h2d-dual"}}
    cfg.update(over)
    return SignParams.model_validate(cfg)


def test_small_sign_single_piece():
    pieces, cuts, warn = panelize(bbox_polygon(0, 0, 200, 100), [], [], _params())
    assert len(pieces) == 1 and not pieces[0].rotated and warn == [] and cuts == []


def test_rotate_to_fit():
    # 280 wide × 310 tall: fits H2D (316×295) only rotated
    pieces, _, _ = panelize(bbox_polygon(0, 0, 280, 310), [], [], _params())
    assert len(pieces) == 1 and pieces[0].rotated


def test_long_word_splits_and_pixels_dodge_seams():
    from shapely.geometry import Point

    from signforge.leds import place_pixels

    foot = bbox_polygon(0, 0, 700, 200)
    strokes = [Stroke(pts=[(20, 100), (680, 100)])]
    p = _params()
    pieces, cuts, warn = panelize(foot, strokes, [], p)
    assert len(pieces) >= 2 and len(cuts) >= 1
    for pc in pieces:
        x0, y0, x1, y1 = pc.mask.bounds
        w, h = x1 - x0, y1 - y0
        assert (w <= 316.5 and h <= 295.5) or (h <= 316.5 and w <= 295.5)

    plan = place_pixels(strokes, p, seams=cuts)
    keep = p.leds.seam_keepout_mm
    for px in plan.pixels:
        for seam in cuts:
            assert seam.distance(Point(px)) >= keep - 0.3   # densify quantum

    assign_pixels(pieces, plan.pixels)
    assigned = sorted(i for pc in pieces for i in pc.pixel_idx)
    assert assigned == list(range(len(plan.pixels)))


def test_screws_avoid_lit_channels():
    foot = bbox_polygon(0, 0, 200, 100)
    # tube passes exactly through the default corner-screw position
    strokes = [Stroke(pts=[(12, 12), (188, 12)])]
    avoid = band(strokes, 28.0)
    pieces, _, _ = panelize(foot, strokes, [], _params(), avoid=avoid)
    assert pieces[0].screws                      # top corners survive
    for sx, sy in pieces[0].screws:
        assert avoid.distance(Point((sx, sy))) >= 3.0


def test_e2e_multi_piece_build(tmp_path, bungee):
    from signforge.pipeline import build

    params = SignParams.model_validate(
        {
            "name": "big",
            "content": {"text": "HELLO", "cap_height_mm": 200.0, "font_path": bungee},
            "style": {"kind": "neon", "backer": "tile"},
            "texture": {"mode": "none"},
            "printer": {"preset": "bambu-a1-mini"},   # small bed forces cuts
        }
    )
    result = build(params, tmp_path / "out")
    assert result.stats["pieces"] >= 4
    names = [f.split("/")[-1] for f in result.files]
    assert any("piece1_shell" in n for n in names)
    assert any("piece2_shell" in n for n in names)
    assert sum(d["pixels"] for d in result.stats["pieces_detail"]) == result.stats["pixels"]
    with zipfile.ZipFile(tmp_path / "out" / "big-kit.zip") as z:
        stls = [m for m in z.namelist() if m.endswith(".stl")]
        shells = [m for m in stls if "_shell" in m]
        # every piece has a shell; empty clipped bodies (cornerpieces without
        # tube content) are correctly skipped, so total is >= pieces + extras
        assert len(shells) == result.stats["pieces"]
        assert len(stls) > result.stats["pieces"]
