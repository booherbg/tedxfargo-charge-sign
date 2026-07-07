import pytest

from signforge.ingest.fonts import text_to_artwork
from signforge.layout import build_layout
from signforge.leds import place_pixels
from signforge.params import SignParams
from signforge.parts.halo import build_halo_bodies, halo_pixel_strokes
from signforge.solids import mesh_of
from signforge.verify import gated_mesh


def _halo_params(**over):
    cfg = {
        "content": {"cap_height_mm": 120.0},
        "style": {"kind": "halo", "backer": "none"},
        "texture": {"mode": "none"},
    }
    for k, v in over.items():
        cfg.setdefault(k, {}).update(v) if isinstance(v, dict) else cfg.__setitem__(k, v)
    return SignParams.model_validate(cfg)


def test_halo_bodies_gate_and_extents(bungee):
    p = _halo_params()
    art = text_to_artwork(bungee, "O", cap_height_mm=120)
    lay = build_layout(art, p)
    strokes = halo_pixel_strokes(lay, p)
    assert strokes and all(s.closed for s in strokes)
    plan = place_pixels(strokes, p)
    assert plan.power.count >= 8
    bodies, foot = build_halo_bodies(lay, plan.pixels, p)
    names = [b.name for b in bodies]
    assert names == ["shell", "liner"]
    st = p.style.halo
    top = st.face_t + st.depth
    for b in bodies:
        v, t = mesh_of(b.man)
        gated_mesh(v, t, f"halo-{b.name}")
    sb = bodies[0].man.bounding_box()
    assert sb[2] == pytest.approx(0.0, abs=1e-6)                  # face on the bed
    assert sb[5] == pytest.approx(top + st.standoff_len, abs=0.2) # bosses on top
    lb = bodies[1].man.bounding_box()
    assert lb[5] == pytest.approx(top, abs=1e-6)


def test_halo_plaque_backer(bungee):
    """halo + tile: a mounting plaque body with standoff-matched anchor bores."""
    from signforge.parts.halo import _standoff_points

    p = _halo_params(style={"kind": "halo", "backer": "tile", "backer_shape": "oval"})
    art = text_to_artwork(bungee, "B", cap_height_mm=140)
    lay = build_layout(art, p)
    bodies, _ = build_halo_bodies(lay, [], p)
    names = [b.name for b in bodies]
    assert "plaque" in names
    plaque = next(b for b in bodies if b.name == "plaque")
    assert plaque.plate == "plaque"
    v, t = mesh_of(plaque.man)
    gated_mesh(v, t, "halo-plaque")
    # anchor bores actually removed material at every standoff
    solid_vol = plaque.man.bounding_box()
    standoffs = _standoff_points(lay, p)
    assert standoffs
    import manifold3d as m3d

    for sx, sy in standoffs:
        probe = m3d.Manifold.cylinder(3.0, 1.0, 1.0, 16).translate([sx, sy, 0.5])
        assert (plaque.man ^ probe).volume() < probe.volume() * 0.2   # hole is open


def test_halo_diffuser_is_separate_part(bungee):
    p = _halo_params(style={"kind": "halo", "halo": {"back_mode": "diffuser"}})
    art = text_to_artwork(bungee, "O", cap_height_mm=120)
    lay = build_layout(art, p)
    bodies, _ = build_halo_bodies(lay, [], p)
    lens = [b for b in bodies if b.name == "lens"]
    assert len(lens) == 1 and lens[0].plate == "lens"


def test_narrow_letters_collapse_racetrack_to_skeleton(bungee):
    """At small caps the flange fills the cavity — opposing racetrack sides
    would violate the pixel floor. Strokes must collapse to centerlines."""
    p = _halo_params(content={"cap_height_mm": 100.0})
    art = text_to_artwork(bungee, "L", cap_height_mm=100)
    lay = build_layout(art, p)
    strokes = halo_pixel_strokes(lay, p)
    assert strokes
    # a racetrack would be one closed ring; the narrow 'L' gives open skeleton run(s)
    assert any(not s.closed for s in strokes)


def test_multiline_neon_quickplan(bungee):
    from signforge.pipeline import quick_plan
    from signforge.params import SignParams

    p = SignParams.model_validate(
        {
            "content": {"text": "TWO\nLINES", "cap_height_mm": 90, "font_path": bungee},
            "style": {"kind": "neon"},
            "texture": {"mode": "none"},
        }
    )
    layout, ledplan, pieces, warns = quick_plan(p)
    assert ledplan.power.count > 30 and len(pieces) >= 1


def test_e2e_halo_kit(tmp_path, bungee):
    from signforge.pipeline import build

    params = SignParams.model_validate(
        {
            "name": "halo-b",
            "content": {"text": "B", "cap_height_mm": 130.0, "font_path": bungee},
            "style": {"kind": "halo"},
            "texture": {"mode": "none"},
        }
    )
    result = build(params, tmp_path / "out")
    assert result.stats["pixels"] >= 10
    names = [f.split("/")[-1] for f in result.files]
    assert "halo-b_shell.stl" in names and "halo-b_liner.stl" in names


def test_e2e_neon_strip_mode(tmp_path, bungee):
    from signforge.pipeline import build

    params = SignParams.model_validate(
        {
            "name": "strip",
            "content": {"text": "S", "cap_height_mm": 120.0, "font_path": bungee},
            "style": {"kind": "neon", "backer": "contour"},
            "texture": {"mode": "none"},
            "leds": {"kind": "strip"},
        }
    )
    result = build(params, tmp_path / "out")
    assert result.stats["pixels"] == 0
    bom = (tmp_path / "out" / "BOM.md").read_text()
    assert "LED strip" in bom and "W PSU" in bom and "voltage droop" in bom
