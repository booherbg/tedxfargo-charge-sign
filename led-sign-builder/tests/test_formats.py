from pathlib import Path

import pytest

from signforge.ingest.art import art_to_artwork
from signforge.params import SignParams
from signforge.pipeline import build
from signforge.verify import BuildError

ASSETS = Path(__file__).parent / "assets"


def test_svg_fill_star_selfintersecting():
    from shapely.geometry import Point

    art = art_to_artwork(str(ASSETS / "svg" / "star.svg"), 100)
    assert art.fills is not None and art.fills.is_valid
    x0, y0, x1, y1 = art.bbox()
    assert (y1 - y0) == pytest.approx(100, rel=0.01)
    # nonzero fill: the pentagram CORE is filled (evenodd would leave it open)
    assert art.fills.contains(Point((x0 + x1) / 2, (y0 + y1) / 2 + 5))
    assert sum(len(p.interiors) for p in art.fills.geoms) == 0


def test_svg_evenodd_nested_donut():
    art = art_to_artwork(str(ASSETS / "svg" / "donut.svg"), 100)
    holes = sum(len(p.interiors) for p in art.fills.geoms)
    assert holes == 1                      # outer ring has a hole
    assert len(art.fills.geoms) == 2       # ...and the innermost rect is solid again


def test_svg_stroked_paths_become_tubes():
    art = art_to_artwork(str(ASSETS / "svg" / "neon-path.svg"), 100)
    assert art.fills is None or art.fills.is_empty
    assert len(art.strokes) == 2
    open_s = [s for s in art.strokes if not s.closed]
    closed_s = [s for s in art.strokes if s.closed]
    assert len(open_s) == 1 and len(closed_s) == 1
    # widths scale with the art (12 source units), both strokes identically
    assert open_s[0].width == pytest.approx(closed_s[0].width, rel=1e-6)
    assert 5.0 < open_s[0].width < 10.0


def test_dxf_closed_and_open():
    art = art_to_artwork(str(ASSETS / "dxf" / "logo.dxf"), 100)
    assert art.fills is not None and not art.fills.is_empty
    assert sum(len(p.interiors) for p in art.fills.geoms) == 1   # circle hole
    assert len(art.strokes) == 1                                  # the spline


def test_png_trace_with_hole():
    art = art_to_artwork(str(ASSETS / "png" / "bolt.png"), 120)
    assert art.fills is not None
    assert sum(len(p.interiors) for p in art.fills.geoms) == 1
    _, y0, _, y1 = art.bbox()
    assert (y1 - y0) == pytest.approx(120, rel=0.02)


def test_unsupported_format_message(tmp_path):
    p = tmp_path / "art.eps"
    p.write_text("%!PS")
    with pytest.raises(BuildError, match="convert to SVG"):
        art_to_artwork(str(p), 100)


CASES = [
    ("text", None, "neon"),
    ("text", None, "channel"),
    ("art", "svg/star.svg", "neon"),
    ("art", "svg/star.svg", "channel"),
    ("art", "svg/neon-path.svg", "neon"),
    ("art", "dxf/logo.dxf", "neon"),
    ("art", "dxf/logo.dxf", "channel"),
    ("art", "png/bolt.png", "neon"),
    ("art", "png/bolt.png", "channel"),
]


@pytest.mark.parametrize("mode,art,style", CASES)
def test_matrix_every_format_builds(tmp_path, bungee, mode, art, style):
    content = {"cap_height_mm": 70.0, "art_target_height_mm": 70.0}
    if mode == "text":
        content.update(text="Hi", font_path=bungee)
    else:
        content.update(mode="art", art_path=str(ASSETS / art))
    params = SignParams.model_validate(
        {
            "name": "m",
            "content": content,
            "style": {"kind": style, "backer": "tile"},
            "texture": {"mode": "none"},
            "leds": {"kind": "bullet12" if style == "neon" else "none", "pitch_mm": 17},
        }
    )
    result = build(params, tmp_path / "out")
    assert any(f.endswith("-kit.zip") for f in result.files)
    assert result.stats["total_grams_petg"] > 1


def test_channel_needs_fills():
    params = SignParams.model_validate(
        {
            "content": {
                "mode": "art",
                "art_path": str(ASSETS / "svg" / "neon-path.svg"),
                "art_target_height_mm": 70,
            },
            "style": {"kind": "channel"},
        }
    )
    with pytest.raises(BuildError, match="filled artwork"):
        build(params, "/tmp/should-not-exist-sf")
