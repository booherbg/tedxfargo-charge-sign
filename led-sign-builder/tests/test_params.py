import pytest
from pydantic import ValidationError

from signforge.params import PRINTER_PRESETS, SignParams, preset_params


def test_defaults_are_valid_and_charge_calibrated():
    p = SignParams()
    assert p.style.neon.band_outer == pytest.approx(22.0)   # 18 + 2*(0.8+1.2)
    assert p.leds.bore_mm == 12.3
    assert p.style.channel.lip_clear == -0.2
    assert p.printer.bed == PRINTER_PRESETS["bambu-h2d-dual"]["bed"]


def test_json_round_trip():
    p = SignParams()
    p2 = SignParams.from_json(p.to_json())
    assert p2 == p


def test_presets():
    assert preset_params("mini-desk").leds.kind == "none"
    with pytest.raises(KeyError):
        preset_params("nope")


def test_bed_override_beats_preset():
    p = SignParams.model_validate(
        {"printer": {"preset": "bambu-x1c", "bed_x_mm": 300, "bed_y_mm": 200}}
    )
    assert p.printer.bed == (300, 200)


def test_unknown_printer_without_bed_rejected():
    with pytest.raises(ValidationError):
        SignParams.model_validate({"printer": {"preset": "not-a-printer"}})


def test_art_mode_requires_path():
    with pytest.raises(ValidationError):
        SignParams.model_validate({"content": {"mode": "art"}})
