"""THE TEXT PLATING LAW: one letter per plate, cuts at kerning-gap midlines
(never through ink), left-to-right labels, and whole-sign auto-scale so every
letter plates on the user's bed."""

from shapely.geometry import LineString

from signforge.params import SignParams
from signforge.pipeline import quick_plan


def _p(text="GLOW", cap=250, kind="neon", printer="bambu-h2d-dual", **kw):
    cfg = {"content": {"text": text, "cap_height_mm": cap},
           "style": {"kind": kind}, "texture": {"mode": "none"},
           "printer": {"preset": printer}}
    for k, v in kw.items():
        cfg[k] = v
    return SignParams.model_validate(cfg)


def test_one_letter_per_plate_left_to_right():
    lay, plan, pieces, warns = quick_plan(_p())
    assert len(pieces) == 4                              # G L O W
    xs = [pc.mask.bounds[0] for pc in pieces]
    assert xs == sorted(xs)                              # P1..P4 read left→right
    assert [pc.label for pc in pieces] == ["P1", "P2", "P3", "P4"]


def test_cuts_never_touch_ink():
    lay, plan, pieces, warns = quick_plan(_p())
    band = 22.0
    tube_field = lay.fills.buffer(band / 2) if lay.fills else None
    for a, b in zip(pieces, pieces[1:]):
        cut_x = (a.mask.bounds[2] + b.mask.bounds[0]) / 2
        y0, y1 = a.mask.bounds[1], a.mask.bounds[3]
        cut = LineString([(cut_x, y0), (cut_x, y1)])
        assert not cut.intersects(tube_field), f"cut at {cut_x:.0f} crosses a tube"


def test_autoscale_fits_every_letter_on_small_bed():
    lay, plan, pieces, warns = quick_plan(_p(printer="bambu-a1-mini"))
    assert any("one letter per plate" in w and "scaled" in w for w in warns)
    bed = (180.0, 180.0)
    for pc in pieces:
        w = pc.mask.bounds[2] - pc.mask.bounds[0]
        h = pc.mask.bounds[3] - pc.mask.bounds[1]
        assert (w <= bed[0] + 1 and h <= bed[1] + 1) or (h <= bed[0] + 1 and w <= bed[1] + 1)


def test_channel_faces_are_lit_now():
    lay, plan, pieces, warns = quick_plan(_p(kind="channel"))
    assert plan is not None and plan.power.count > 50    # bullet pixels in cavity
    assert len(pieces) == 4                              # law applies to channel too


def test_shape_art_keeps_corridor_solver():
    p = SignParams.model_validate({
        "content": {"mode": "art",
                    "art_path": "signforge/assets/art/bolt.svg",
                    "art_target_height_mm": 400},
        "style": {"kind": "neon"}, "texture": {"mode": "none"},
    })
    lay, plan, pieces, warns = quick_plan(p)
    assert not any("one letter per plate" in w for w in warns)   # art unaffected


def test_tube_width_morphs_unlit_signs():
    """Slim tubes for strip/none; bullet12 clamps back to 22 with a warning."""
    from signforge.ingest.fonts import text_to_artwork
    from signforge.layout import build_layout
    from signforge.tubes import plan_tubes

    slim = SignParams.model_validate(
        {"style": {"kind": "neon", "neon": {"channel_interior": 6}},
         "leds": {"kind": "strip"}, "texture": {"mode": "none"}}
    )
    art = text_to_artwork("bungee", "GO", cap_height_mm=60)
    lay = build_layout(art, slim)
    strokes, _, meta, warns = plan_tubes(lay, slim)
    assert slim.style.neon.band_outer == 10.0             # honored (interior+walls)
    assert not any("raised to 22" in w for w in warns)

    clamped = SignParams.model_validate(
        {"style": {"kind": "neon", "neon": {"channel_interior": 6}},
         "leds": {"kind": "bullet12"}, "texture": {"mode": "none"}}
    )
    lay2 = build_layout(text_to_artwork("bungee", "GO", cap_height_mm=200), clamped)
    plan_tubes(lay2, clamped)
    assert clamped.style.neon.band_outer == 22.0          # physics wins


def test_negative_tracking_merges_letters():
    from signforge.ingest.fonts import text_to_artwork
    from signforge.layout import build_layout
    from signforge.tubes import plan_tubes

    p = SignParams.model_validate(
        {"content": {"letter_spacing_mm": -30.0},
         "style": {"kind": "neon"}, "texture": {"mode": "none"}}
    )
    art = text_to_artwork("bungee", "OO", cap_height_mm=150,
                          letter_spacing_mm=-30.0)
    lay = build_layout(art, p)
    strokes, _, meta, warns = plan_tubes(lay, p)
    assert meta["source"].startswith("merged:")
    assert any("merge mode" in w for w in warns)
    assert strokes
