"""CHARGE.svg through the generic pipeline must match the original production
treatment: centerline tubes (never outline-of-a-tube), original-scale piece
and pixel counts. Skips when the parent repo asset isn't present."""

from pathlib import Path

import pytest

CHARGE = Path(__file__).resolve().parents[2] / "assets" / "svg" / "CHARGE.svg"


@pytest.mark.slow
@pytest.mark.skipif(not CHARGE.exists(), reason="parent CHARGE.svg not present")
def test_charge_replica_matches_production_treatment(tmp_path):
    from signforge.params import SignParams
    from signforge.pipeline import build

    params = SignParams.model_validate(
        {
            "name": "charge",
            "content": {"mode": "art", "art_path": str(CHARGE),
                        "art_target_height_mm": 250},
            "style": {"kind": "neon", "backer": "tile", "tile_margin_mm": 22.5},
            "texture": {"mode": "none"},
            "leds": {"pitch_mm": 17},
            "printer": {"preset": "bambu-h2d-dual"},
        }
    )
    r = build(params, tmp_path / "out")
    # tube-art detection: skeleton treatment, no outline-of-a-tube artifacts
    assert not any("outline:" in w for w in r.warnings)
    # original production: 1597mm face, 6 pieces, 454 px (after hand repairs)
    assert 1400 <= r.stats["sign_mm"][0] <= 1650
    assert 4 <= r.stats["pieces"] <= 7
    assert 380 <= r.stats["pixels"] <= 480
