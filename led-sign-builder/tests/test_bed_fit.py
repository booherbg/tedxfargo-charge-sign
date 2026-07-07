"""Every exported STL must fit the printer bed AS-IS (the 'respects height
but not width' report: unpanelized flat plates shipped at full sign width)."""

from pathlib import Path

import pytest

from signforge.export.stl import read_stl
from signforge.params import SignParams
from signforge.pipeline import build


def _assert_all_fit(outdir: Path, bed, tol=0.6):
    checked = 0
    for f in sorted(Path(outdir, "stl").glob("*.stl")):
        v, _ = read_stl(f)
        w = v[:, 0].max() - v[:, 0].min()
        h = v[:, 1].max() - v[:, 1].min()
        assert w <= bed[0] + tol and h <= bed[1] + tol, f"{f.name}: {w:.0f}×{h:.0f} vs bed {bed}"
        checked += 1
    assert checked > 0
    return checked


@pytest.mark.parametrize(
    "name,cfg",
    [
        ("channel-wide-lens", {"content": {"text": "BAKERY", "cap_height_mm": 180},
                               "style": {"kind": "channel"}, "leds": {"kind": "none"},
                               "texture": {"mode": "none"}}),
        ("halo-wide-plaque", {"content": {"text": "HI", "cap_height_mm": 200},
                              "style": {"kind": "halo", "backer": "tile"},
                              "texture": {"mode": "none"}}),
        ("neon-small-bed", {"content": {"text": "GLOW", "cap_height_mm": 200},
                            "style": {"kind": "neon"}, "texture": {"mode": "none"},
                            "printer": {"preset": "bambu-a1-mini"}}),
    ],
)
def test_every_exported_stl_fits_the_bed(tmp_path, name, cfg):
    cfg = dict(cfg)
    cfg["name"] = name
    p = SignParams.model_validate(cfg)
    result = build(p, tmp_path / name)
    n = _assert_all_fit(tmp_path / name, p.printer.bed)
    assert n >= result.stats["pieces"]


def test_flat_plate_splitter_unit():
    import manifold3d as m3d

    from signforge.export.pieces import fit_flat_plate

    plate = m3d.Manifold.cube([1000.0, 180.0, 2.0])
    parts, rotated, cuts = fit_flat_plate(plate, (316.0, 295.0))
    assert len(parts) == 4 and cuts == 3
    for part in parts:
        b = part.bounding_box()
        assert b[3] - b[0] <= 316.6 and b[4] - b[1] <= 295.6

    tall = m3d.Manifold.cube([280.0, 310.0, 2.0])
    parts2, rotated2, cuts2 = fit_flat_plate(tall, (316.0, 295.0))
    assert len(parts2) == 1 and rotated2 and cuts2 == 0
    b = parts2[0].bounding_box()
    assert b[3] - b[0] <= 316.6 and b[4] - b[1] <= 295.6
