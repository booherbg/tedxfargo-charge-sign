import json

from signforge.leds import place_pixels, wled_ledmap
from signforge.model import Stroke
from signforge.params import SignParams


def _plan(strokes, pitch=17.0):
    return place_pixels(strokes, SignParams.model_validate({"leds": {"pitch_mm": pitch}}))


def test_ledmap_covers_every_led_exactly_once():
    plan = _plan([Stroke(pts=[(0, 0), (170, 0)]), Stroke(pts=[(0, 40), (170, 40)])])
    m = wled_ledmap(plan.pixels, plan.per_stroke)
    leds = [v for v in m["map"] if v >= 0]
    assert sorted(leds) == list(range(m["n"]))
    assert m["n"] == plan.power.count
    assert len(m["map"]) == m["width"] * m["height"]


def test_ledmap_geometry_roundtrip():
    """Grid position of each LED lands within ~a cell of its physical spot."""
    plan = _plan([Stroke(pts=[(0, 0), (200, 0), (200, 100)])])
    m = wled_ledmap(plan.pixels, plan.per_stroke)
    order = [i for run in plan.per_stroke for i in run]
    x0 = min(plan.pixels[i][0] for i in order)
    y1 = max(plan.pixels[i][1] for i in order)
    for cell_idx, led in enumerate(m["map"]):
        if led < 0:
            continue
        cy, cx = divmod(cell_idx, m["width"])
        px = plan.pixels[order[led]]
        gx = x0 + cx * m["cell_mm"]
        gy = y1 - cy * m["cell_mm"]
        assert abs(gx - px[0]) <= 2.2 * m["cell_mm"]
        assert abs(gy - px[1]) <= 2.2 * m["cell_mm"]


def test_kit_ships_wled_map(tmp_path, bungee):
    from signforge.pipeline import build

    params = SignParams.model_validate(
        {
            "name": "wled",
            "content": {"text": "S", "cap_height_mm": 120, "font_path": bungee},
            "style": {"kind": "neon", "backer": "none"},
            "texture": {"mode": "none"},
        }
    )
    result = build(params, tmp_path / "out")
    wf = tmp_path / "out" / "wled_ledmap.json"
    assert wf.exists() and str(wf) in result.files
    data = json.loads(wf.read_text())
    assert data["n"] == result.stats["pixels"]
    # WLED 16.x streams the map with a byte-exact '"map":[' search; a space
    # after the colon silently loads zero entries — keep the file compact
    assert '"map":[' in wf.read_text()
    bom = (tmp_path / "out" / "BOM.md").read_text()
    assert "wled_ledmap.json" in bom


def test_outline_text_mode(bungee):
    """style.neon.source='outline' on TEXT = open-tube channel letters."""
    from signforge.ingest.fonts import text_to_artwork
    from signforge.layout import build_layout
    from signforge.tubes import plan_tubes

    p = SignParams.model_validate(
        {"style": {"kind": "neon", "neon": {"source": "outline"}},
         "texture": {"mode": "none"}}
    )
    art = text_to_artwork(bungee, "BO", cap_height_mm=250)
    lay = build_layout(art, p)
    strokes, lay2, meta, warns = plan_tubes(lay, p)
    assert meta["source"].startswith("outline")
    closed = [s for s in strokes if s.closed]
    assert len(closed) >= 4          # B: outer+2 counters; O: outer+counter
