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
    assert "hi-sign_main.3mf" in stems and "hi-sign_lens.3mf" in stems
    assert "index.html" in stems and "BOM.md" in stems and "params.json" in stems
    assert "hi-sign-kit.zip" in stems

    replay = SignParams.from_json((tmp_path / "out" / "params.json").read_text())
    assert replay == params                      # reproducible

    stats = result.stats
    assert stats["total_grams_petg"] > 5
    assert stats["bodies"]["shell"]["tris"] > 100
    assert stats["sign_mm"][0] > stats["sign_mm"][1] > 0

    import zipfile

    with zipfile.ZipFile(tmp_path / "out" / "hi-sign-kit.zip") as z:
        members = z.namelist()
        assert "BOM.md" in members and "preview/index.html" in members
        assert any(m.startswith("stl/") for m in members)
        assert any(m.startswith("3mf/") for m in members)

    html = (tmp_path / "out" / "preview" / "index.html").read_text()
    assert "<svg" in html and "hi-sign" in html
    bom = (tmp_path / "out" / "BOM.md").read_text()
    assert "Print card" in bom and "grams" in bom
