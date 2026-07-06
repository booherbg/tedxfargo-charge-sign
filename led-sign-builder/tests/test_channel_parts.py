import pytest

from signforge.ingest.fonts import text_to_artwork
from signforge.layout import build_layout
from signforge.params import SignParams
from signforge.parts.channel import build_channel_bodies
from signforge.solids import mesh_of
from signforge.verify import gated_mesh


def _bodies(bungee, text="HI", overrides=None, pixels=()):
    cfg = {"content": {"cap_height_mm": 60.0}, "style": {"kind": "channel", "backer": "none"}}
    if overrides:
        for k, v in overrides.items():
            cfg.setdefault(k, {}).update(v) if isinstance(v, dict) else cfg.__setitem__(k, v)
    p = SignParams.model_validate(cfg)
    art = text_to_artwork(bungee, text, cap_height_mm=p.content.cap_height_mm)
    lay = build_layout(art, p)
    bodies, _footprint = build_channel_bodies(lay, list(pixels), p)
    return bodies, lay, p


def test_bodies_exist_and_pass_gates(bungee):
    bodies, _, _ = _bodies(bungee)
    names = [b.name for b in bodies]
    assert names == ["shell", "lens"]        # no pixels -> no liner
    for b in bodies:
        v, t = mesh_of(b.man)
        gated_mesh(v, t, b.name)             # raises on failure


def test_counter_walls_and_open_vs_glow(bungee):
    glow, _, _ = _bodies(bungee, text="O")
    openb, _, _ = _bodies(bungee, text="O", overrides={"style": {"channel": {"counter_mode": "open"}}})
    lens_glow = next(b for b in glow if b.name == "lens")
    lens_open = next(b for b in openb if b.name == "lens")
    assert lens_open.man.volume() < lens_glow.man.volume()   # open counter removes area


def test_tile_backer_extends_shell(bungee):
    plain, _, _ = _bodies(bungee)
    tiled, lay, p = _bodies(bungee, overrides={"style": {"kind": "channel", "backer": "tile"}})
    shell_plain = next(b for b in plain if b.name == "shell")
    shell_tiled = next(b for b in tiled if b.name == "shell")
    assert shell_tiled.man.volume() > shell_plain.man.volume() * 1.2
    bb = shell_tiled.man.bounding_box()
    lo, hi = bb[:3], bb[3:]
    m = p.style.tile_margin_mm
    ax0, ay0, ax1, ay1 = lay.fills.bounds
    assert lo[0] == pytest.approx(ax0 - m, abs=0.01) and hi[0] == pytest.approx(ax1 + m, abs=0.01)
    assert lo[1] == pytest.approx(ay0 - m, abs=0.01) and hi[1] == pytest.approx(ay1 + m, abs=0.01)


def test_pixels_add_liner_and_bores(bungee):
    without, _, _ = _bodies(bungee, text="O")
    with_px, lay, p = _bodies(bungee, text="O", pixels=[(30.0, 30.0)])
    assert [b.name for b in with_px] == ["shell", "liner", "lens"]
    s0 = next(b for b in without if b.name == "shell").man.volume()
    s1 = next(b for b in with_px if b.name == "shell").man.volume()
    assert s1 < s0                            # collar bore removed material
    for b in with_px:
        v, t = mesh_of(b.man)
        gated_mesh(v, t, b.name)


def test_too_thick_walls_raise(bungee):
    from signforge.verify import BuildError

    with pytest.raises(BuildError, match="cavity"):
        _bodies(bungee, text="I", overrides={"content": {"cap_height_mm": 20.0},
                                             "style": {"kind": "channel", "backer": "none",
                                                       "channel": {"wall_t": 6.0}}})
