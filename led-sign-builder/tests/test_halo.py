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


def test_halo_diffuser_is_separate_part(bungee):
    p = _halo_params(style={"kind": "halo", "halo": {"back_mode": "diffuser"}})
    art = text_to_artwork(bungee, "O", cap_height_mm=120)
    lay = build_layout(art, p)
    bodies, _ = build_halo_bodies(lay, [], p)
    lens = [b for b in bodies if b.name == "lens"]
    assert len(lens) == 1 and lens[0].plate == "lens"


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
