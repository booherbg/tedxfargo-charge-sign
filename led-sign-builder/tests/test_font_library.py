from pathlib import Path

import pytest

from signforge.ingest.fonts import (
    BUNDLED_FONTS,
    _fonts_dir,
    bundled_fonts,
    resolve_font,
    text_to_artwork,
)
from signforge.verify import BuildError


def test_registry_files_and_licenses_exist():
    d = _fonts_dir()
    assert len(BUNDLED_FONTS) >= 14
    for name, info in BUNDLED_FONTS.items():
        assert (d / info["file"]).exists(), f"missing font file for {name}"
    licenses = list(d.glob("OFL-*.txt"))
    assert len(licenses) >= 13                       # one per family


@pytest.mark.parametrize("name", sorted(BUNDLED_FONTS))
def test_every_bundled_font_produces_letterforms(name):
    art = text_to_artwork(name, "Ag24", cap_height_mm=80)
    assert art.fills is not None and not art.fills.is_empty
    assert art.fills.is_valid
    assert len(art.glyphs) == 4
    _, y0, _, y1 = art.bbox()
    assert (y1 - y0) > 40                            # scaled sanely


def test_resolve_font_semantics(bungee):
    assert str(resolve_font("monoton")).endswith("Monoton-Regular.ttf")
    assert resolve_font(bungee) == bungee            # path passthrough
    assert str(resolve_font(None)).endswith("Bungee-Regular.ttf")
    with pytest.raises(BuildError, match="bundled"):
        resolve_font("comic-sans")


def test_web_fonts_endpoint_and_bundled_build(tmp_path):
    from fastapi.testclient import TestClient

    from signforge.web.app import create_app

    client = TestClient(create_app(open_mode=True, db_path=str(tmp_path / "d.sqlite"),
                                   workdir=str(tmp_path / "w"), workers=0))
    fonts = client.get("/api/fonts").json()["fonts"]
    names = {f["name"] for f in fonts}
    assert "monoton" not in names and "great-vibes" not in names   # v1-hidden
    assert len(fonts) >= 12
    everything = client.get("/api/fonts?all=1").json()["fonts"]
    assert len(everything) > len(fonts)                            # still reachable
    limelight = next(f for f in fonts if f["name"] == "limelight")
    r = client.get(limelight["url"])
    assert r.status_code == 200 and len(r.content) > 20000

    r = client.post(
        "/api/preview2d",
        json={"font": "limelight",
              "params": {"content": {"text": "CLUB", "cap_height_mm": 80},
                         "style": {"kind": "channel", "backer": "none"},
                         "leds": {"kind": "none"}}},
    )
    assert r.status_code == 200 and r.json()["pieces"] == 1
    assert client.post(
        "/api/preview2d", json={"font": "nope", "params": {}}
    ).status_code == 400


def test_cli_accepts_bundled_name(tmp_path):
    from signforge.cli import main

    rc = main(["build", "--text", "Hi", "--font", "righteous", "--style", "channel",
               "--backer", "none", "--cap-height", "50", "-o", str(tmp_path)])
    assert rc == 0
