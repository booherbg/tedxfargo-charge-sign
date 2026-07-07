import numpy as np
from PIL import Image

from signforge.params import SignParams
from signforge.pipeline import build


def test_kit_contains_lit_preview_png(tmp_path, bungee):
    params = SignParams.model_validate(
        {
            "name": "png",
            "content": {"text": "GO", "cap_height_mm": 90, "font_path": bungee},
            "style": {"kind": "neon", "backer_shape": "rounded"},
            "texture": {"mode": "none"},
            "colors": {"palette": "gas-station"},
        }
    )
    result = build(params, tmp_path / "out")
    png = tmp_path / "out" / "preview" / "preview.png"
    assert png.exists() and str(png) in result.files
    img = np.asarray(Image.open(png).convert("RGB"))
    assert img.shape[1] == 1100
    # the lens color must actually appear (lit tubes rendered)
    lens = np.array([0xFF, 0x5A, 0x4E])
    close = (np.abs(img.astype(int) - lens).sum(axis=2) < 90).mean()
    assert close > 0.01
    # and the shell/backer too
    assert img.reshape(-1, 3).std(axis=0).mean() > 20   # not a flat image


def test_bungee_k_keeps_its_leg():
    """Regression: glyph-relative pruning — the bold K's ~40mm lower leg
    survived only when min_path scales with glyph size, not tube width."""
    from signforge.ingest.fonts import text_to_artwork
    from signforge.layout import build_layout
    from signforge.tubes import plan_tubes

    p = SignParams.model_validate(
        {"style": {"kind": "neon", "neon": {"source": "skeleton"}},
         "texture": {"mode": "none"}}
    )
    art = text_to_artwork(None, "K", cap_height_mm=110)
    lay = build_layout(art, p)
    strokes, _, _, _ = plan_tubes(lay, p)
    assert len(strokes) >= 3          # stem + arm + LEG (spine treatment)
