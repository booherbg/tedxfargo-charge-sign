import json
from pathlib import Path

from signforge.params import SignParams
from signforge.pipeline import build


def test_text_to_channel_kit(tmp_path, bungee):
    params = SignParams.model_validate(
        {
            "name": "hi-sign",
            "content": {"text": "HI", "cap_height_mm": 60.0, "font_path": bungee},
            "style": {"kind": "channel", "backer": "tile"},
            "leds": {"kind": "none"},
            "texture": {"mode": "none"},
        }
    )
    result = build(params, tmp_path / "out")
    stems = sorted(Path(f).name for f in result.files)
    assert "hi-sign_shell.stl" in stems and "hi-sign_lens.stl" in stems
    assert "params.json" in stems

    replay = SignParams.from_json((tmp_path / "out" / "params.json").read_text())
    assert replay == params                      # reproducible

    stats = result.stats
    assert stats["total_grams_petg"] > 5
    assert stats["bodies"]["shell"]["tris"] > 100
    assert stats["sign_mm"][0] > stats["sign_mm"][1] > 0
