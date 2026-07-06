"""Torture sweep (slow): every nasty config builds clean or gates with a clear
message — NEVER a traceback. Run with: uv run pytest -m slow"""

import tempfile
from pathlib import Path

import pytest

from signforge.params import SignParams
from signforge.pipeline import build
from signforge.verify import BuildError

ASSETS = Path(__file__).parent / "assets"
FONTS = ASSETS / "fonts"

CASES = {
    "multiline-neon": {"content": {"text": "TWO\nLINES", "cap_height_mm": 90}, "style": {"kind": "neon"}, "texture": {"mode": "none"}},
    "single-char": {"content": {"text": "&", "cap_height_mm": 100}, "style": {"kind": "neon"}, "texture": {"mode": "none"}},
    "tiny-cap-neon": {"content": {"text": "hi", "cap_height_mm": 25}, "style": {"kind": "neon", "backer": "contour"}, "texture": {"mode": "none"}},
    "huge-cap": {"content": {"text": "M", "cap_height_mm": 500}, "style": {"kind": "neon"}, "texture": {"mode": "none"}},
    "oswald-thin": {"content": {"text": "SLIM", "cap_height_mm": 120, "font_path": str(FONTS / "Oswald-Variable.ttf")}, "style": {"kind": "neon"}, "texture": {"mode": "none"}},
    "punctuation": {"content": {"text": "24/7!", "cap_height_mm": 100}, "style": {"kind": "neon"}, "texture": {"mode": "none"}},
    "descenders": {"content": {"text": "juggle", "cap_height_mm": 80, "font_path": str(FONTS / "Pacifico-Regular.ttf")}, "style": {"kind": "channel"}, "leds": {"kind": "none"}, "texture": {"mode": "none"}},
    "halo-word": {"content": {"text": "HALO", "cap_height_mm": 100}, "style": {"kind": "halo"}, "texture": {"mode": "none"}},
    "budget-tiny": {"content": {"text": "A B", "cap_height_mm": 120}, "style": {"kind": "neon"}, "leds": {"budget_px": 5}, "texture": {"mode": "none"}},
    "counter-open": {"content": {"text": "B", "cap_height_mm": 90}, "style": {"kind": "channel", "channel": {"counter_mode": "open"}}, "leds": {"kind": "none"}, "texture": {"mode": "none"}},
    "textured-big": {"content": {"text": "OK", "cap_height_mm": 300}, "style": {"kind": "neon"}, "texture": {"mode": "pyramid_jitter"}},
    "empty-text": {"content": {"text": "   ", "cap_height_mm": 100}, "style": {"kind": "neon"}},
    "dxf-strip": {"content": {"mode": "art", "art_path": str(ASSETS / "dxf" / "logo.dxf"), "art_target_height_mm": 100}, "style": {"kind": "neon"}, "leds": {"kind": "strip"}, "texture": {"mode": "none"}},
}


@pytest.mark.slow
@pytest.mark.parametrize("name", sorted(CASES))
def test_torture_case_never_crashes(name):
    cfg = dict(CASES[name])
    cfg["name"] = name
    params = SignParams.model_validate(cfg)
    try:
        with tempfile.TemporaryDirectory() as td:
            result = build(params, td)
        assert result.stats["total_grams_petg"] > 0
    except BuildError as e:
        assert len(str(e)) > 20      # gates must explain themselves
