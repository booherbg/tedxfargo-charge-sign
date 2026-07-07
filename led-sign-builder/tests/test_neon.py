import pytest

from signforge.geom2d import band
from signforge.ingest.fonts import text_to_artwork
from signforge.layout import build_layout
from signforge.model import Stroke
from signforge.params import SignParams
from signforge.verify import clearance_audit, coverage_qa


def _neon_params(**content):
    c = {"cap_height_mm": 120.0}
    c.update(content)
    return SignParams.model_validate(
        {"content": c, "style": {"kind": "neon", "backer": "tile"}}
    )


def test_plan_tubes_from_text(bungee):
    from signforge.tubes import plan_tubes

    p = _neon_params()
    art = text_to_artwork(bungee, "SO", cap_height_mm=120)
    lay = build_layout(art, p)
    strokes, lay2, meta, warnings = plan_tubes(lay, p)
    # per-glyph auto at 120mm: spines (possibly with a retry-added ring)
    assert 2 <= len(strokes) <= 4
    assert any(not s.closed for s in strokes)      # the S spine is open
    assert meta["tube_w"] > 8


def test_coverage_qa_catches_amputation():
    from signforge.geom2d import bbox_polygon, heal

    bar1 = heal(bbox_polygon(0, 0, 100, 12))
    bar2 = heal(bbox_polygon(0, 40, 100, 52))
    fills = heal(bar1.union(bar2))
    only_bar1 = band([Stroke(pts=[(0, 6), (100, 6)])], 14)
    fails, notes = coverage_qa(fills, only_bar1)
    assert fails and "uncovered" in fails[0]      # bar2 went missing → FAIL


def test_clearance_audit_mush_vs_crossing():
    mush, worst = clearance_audit(
        [Stroke(pts=[(0, 0), (100, 0)]), Stroke(pts=[(0, 20), (100, 20)])], min_gap=26
    )
    assert len(mush) == 1 and "parallel mush" in mush[0]
    assert worst == pytest.approx(20.0, abs=0.5)

    crossing, worst2 = clearance_audit(
        [Stroke(pts=[(-50, 0), (50, 0)]), Stroke(pts=[(0, -50), (0, 50)])], min_gap=26
    )
    assert crossing == [] and worst2 is None       # crisp 90° crossing is legal


def test_neon_bodies_gated(bungee):
    from signforge.leds import place_pixels
    from signforge.parts.neon import build_neon_bodies
    from signforge.solids import mesh_of
    from signforge.tubes import plan_tubes
    from signforge.verify import gated_mesh

    p = _neon_params()
    art = text_to_artwork(bungee, "S", cap_height_mm=120)
    lay = build_layout(art, p)
    strokes, lay, meta, _ = plan_tubes(lay, p)
    plan = place_pixels(strokes, p)
    bodies, footprint = build_neon_bodies(lay, strokes, plan.pixels, p)
    assert not footprint.is_empty
    assert [b.name for b in bodies] == ["shell", "liner", "lens"]
    for b in bodies:
        v, t = mesh_of(b.man)
        gated_mesh(v, t, b.name)


def test_script_font_terminal_rescue(pacifico):
    """Pacifico terminals (the w's teardrop, o's connector tail) prune as
    spurs; terminal rescue must recover them or the strict gate fails."""
    from signforge.tubes import plan_tubes

    p = _neon_params(text="glow")
    art = text_to_artwork(pacifico, "glow", cap_height_mm=140)
    lay = build_layout(art, p)
    strokes, lay2, meta, warnings = plan_tubes(lay, p)   # raises without rescue
    assert any("terminal rescue" in w for w in warnings)
    assert len(strokes) >= 7                              # base tubes + rescued bits


def test_e2e_neon_kit(tmp_path, bungee):
    from signforge.pipeline import build

    params = SignParams.model_validate(
        {
            "name": "neon-so",
            "content": {"text": "SO", "cap_height_mm": 120.0, "font_path": bungee},
            "style": {"kind": "neon", "backer": "tile"},
            "texture": {"mode": "none"},
        }
    )
    result = build(params, tmp_path / "out")
    names = sorted(p.split("/")[-1] for p in result.files)
    assert "neon-so_shell.stl" in names and "neon-so_liner.stl" in names
    assert "neon-so_lens.stl" in names and "neon-so_main.3mf" in names
    assert "debug_tubes.png" in names
    assert result.stats["pixels"] > 10

    import zipfile

    with zipfile.ZipFile(tmp_path / "out" / "neon-so-kit.zip") as z:
        assert "preview/debug_tubes.png" in z.namelist()

    bom = (tmp_path / "out" / "BOM.md").read_text()
    assert "Electrical" in bom and "PSU" in bom
