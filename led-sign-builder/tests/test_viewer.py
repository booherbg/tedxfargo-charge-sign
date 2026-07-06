import base64
import json
import re
import struct

from signforge.export.stl import stl_bytes
from signforge.geom2d import bbox_polygon, heal
from signforge.preview.viewer import render_viewer
from signforge.solids import mesh_of, prism


def _stl():
    man = prism(heal(bbox_polygon(0, 0, 10, 10)), 0, 5)
    v, t = mesh_of(man)
    return stl_bytes(v, t), len(t)


def test_viewer_embeds_valid_stl():
    data, ntri = _stl()
    html = render_viewer(
        "demo",
        [{"label": "P1", "center": (5.0, 5.0),
          "bodies": [{"name": "shell", "color": "#141414", "stl": data}]}],
    )
    assert html and "SIGN_DATA" in html and "webgl" in html
    m = re.search(r"const SIGN_DATA = (\{.*?\});\n?</script>", html, re.S)
    payload = json.loads(m.group(1))
    raw = base64.b64decode(payload["pieces"][0]["bodies"][0]["stl"])
    (n,) = struct.unpack_from("<I", raw, 80)
    assert n == ntri


def test_viewer_size_cap():
    data, _ = _stl()
    big = [{"label": "P1", "center": (0, 0),
            "bodies": [{"name": "shell", "color": "#111111", "stl": data * 100000}]}]
    assert render_viewer("demo", big, max_embed_mb=1.0) is None


def test_e2e_kit_includes_viewer(tmp_path, bungee):
    from signforge.params import SignParams
    from signforge.pipeline import build

    params = SignParams.model_validate(
        {
            "name": "v",
            "content": {"text": "S", "cap_height_mm": 80.0, "font_path": bungee},
            "style": {"kind": "neon", "backer": "contour"},
            "texture": {"mode": "none"},
        }
    )
    result = build(params, tmp_path / "out")
    viewer = tmp_path / "out" / "preview" / "viewer.html"
    assert viewer.exists()
    html = viewer.read_text()
    assert "explode" in html and "SIGN_DATA" in html
    index = (tmp_path / "out" / "preview" / "index.html").read_text()
    assert "viewer.html" in index
