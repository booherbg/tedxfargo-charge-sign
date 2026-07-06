import pytest
from shapely.geometry import box

from signforge.params import PALETTES, SignParams
from signforge.plaques import SHAPES, plaque


BOUNDS = (0.0, 0.0, 200.0, 90.0)


@pytest.mark.parametrize("shape", SHAPES)
def test_plaque_contains_content(shape):
    p = plaque(shape, BOUNDS, margin=12)
    assert p.is_valid and p.area > 0
    assert p.covers(box(*BOUNDS))


def test_plaque_shapes_differ():
    areas = {s: plaque(s, BOUNDS, 12).area for s in SHAPES}
    assert len({round(a) for a in areas.values()}) >= 5


def test_palette_applies_to_preview():
    p = SignParams.model_validate({"colors": {"palette": "gas-station"}})
    assert p.colors.preview == PALETTES["gas-station"]
    with pytest.raises(Exception):
        SignParams.model_validate({"colors": {"palette": "nope"}})


def test_bridging_profile():
    good = SignParams.model_validate({"printer": {"preset": "bambu-h2d-dual"}})
    weak = SignParams.model_validate({"printer": {"preset": "ender-3"}})
    assert good.printer.bridging == "good" and weak.printer.bridging == "weak"


def test_support_ribs_geometry():
    from signforge.geom2d import band
    from signforge.model import Stroke
    from signforge.parts.ribs import support_ribs

    s = Stroke(pts=[(0, 0), (200, 0)])
    b_in = band([s], 18.0)
    pixels = [(x, 0.0) for x in range(0, 201, 17)]   # production pitch
    ribs = support_ribs([s], b_in, pixels, spacing=28, rib_t=0.9, span=19.6)
    assert len(ribs) >= 4
    import math

    for r in ribs:
        assert b_in.covers(r.buffer(-0.01))          # ribs stay inside the channel
        c = r.centroid
        assert min(math.dist((c.x, c.y), q) for q in pixels) >= 7.0 - 0.2


def test_e2e_catalog_build(tmp_path, bungee):
    """Shield plaque + backer fuzz + forced ribs + palette, all gates green."""
    from signforge.pipeline import build

    params = SignParams.model_validate(
        {
            "name": "cat",
            "content": {"text": "OK", "cap_height_mm": 110, "font_path": bungee},
            "style": {"kind": "neon", "backer": "tile", "backer_shape": "shield",
                      "support_ribs": "on"},
            "texture": {"mode": "pyramid_jitter", "targets": ["lens", "backer"]},
            "colors": {"palette": "atomic-lounge"},
        }
    )
    result = build(params, tmp_path / "out")
    assert result.stats["total_grams_petg"] > 10


def test_ribs_auto_follows_printer(tmp_path, bungee):
    from signforge.ingest.fonts import text_to_artwork
    from signforge.layout import build_layout
    from signforge.leds import place_pixels
    from signforge.parts.neon import build_neon_bodies
    from signforge.tubes import plan_tubes

    def liner_volume(preset):
        p = SignParams.model_validate(
            {
                "content": {"cap_height_mm": 110.0},
                "style": {"kind": "neon", "backer": "none"},
                "texture": {"mode": "none"},
                "printer": {"preset": preset},
            }
        )
        art = text_to_artwork(bungee, "S", cap_height_mm=110)
        lay = build_layout(art, p)
        strokes, lay, _, _ = plan_tubes(lay, p)
        plan = place_pixels(strokes, p)
        bodies, _ = build_neon_bodies(lay, strokes, plan.pixels, p)
        return next(b for b in bodies if b.name == "liner").man.volume()

    assert liner_volume("ender-3") > liner_volume("bambu-h2d-dual") * 1.02
