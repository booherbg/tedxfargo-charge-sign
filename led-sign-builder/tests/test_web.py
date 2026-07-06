import time
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from signforge.web.app import app

client = TestClient(app)
ASSETS = Path(__file__).parent / "assets"


def test_index_and_presets():
    assert client.get("/").status_code == 200
    r = client.get("/api/presets")
    assert r.status_code == 200
    data = r.json()
    assert "neon-classic" in data["presets"]
    assert data["defaults"]["leds"]["bore_mm"] == 12.3
    assert "bambu-h2d-dual" in data["printers"]


def test_upload_validation():
    r = client.post(
        "/api/upload?kind=font",
        files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
    )
    assert r.status_code == 400


def test_preview2d_roundtrip():
    payload = {
        "params": {
            "content": {"text": "HI", "cap_height_mm": 60},
            "style": {"kind": "channel", "backer": "none"},
            "leds": {"kind": "none"},
        }
    }
    r = client.post("/api/preview2d", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["svg"].startswith("<svg") and data["pieces"] == 1


def test_upload_build_download_flow():
    font = (ASSETS / "fonts" / "Pacifico-Regular.ttf").read_bytes()
    r = client.post(
        "/api/upload?kind=font", files={"file": ("Pacifico.ttf", font, "font/ttf")}
    )
    assert r.status_code == 200
    token = r.json()["token"]

    payload = {
        "font_token": token,
        "params": {
            "name": "webkit",
            "content": {"text": "hi", "cap_height_mm": 50},
            "style": {"kind": "channel", "backer": "none"},
            "leds": {"kind": "none"},
            "texture": {"mode": "none"},
        },
    }
    r = client.post("/api/build", json=payload)
    assert r.status_code == 200
    job = r.json()["job"]

    for _ in range(120):
        st = client.get(f"/api/jobs/{job}").json()
        if st["status"] in ("done", "error"):
            break
        time.sleep(0.25)
    assert st["status"] == "done", st.get("error")
    assert st["stats"]["total_grams_petg"] > 0

    r = client.get(f"/api/jobs/{job}/download")
    assert r.status_code == 200
    zf = zipfile.ZipFile(BytesIO(r.content))
    assert any(n.endswith(".stl") for n in zf.namelist())
    assert client.get(f"/api/jobs/{job}/viewer").status_code == 200


def test_broken_font_rejected_at_upload():
    r = client.post(
        "/api/upload?kind=font", files={"file": ("fake.ttf", b"not a font", "font/ttf")}
    )
    assert r.status_code == 400 and "parse" in r.text


def test_fake_png_rejected():
    r = client.post(
        "/api/upload?kind=art", files={"file": ("x.png", b"<svg>", "image/png")}
    )
    assert r.status_code == 400


def test_rate_limit_and_upload_eviction():
    from signforge.web import app as webapp

    old_limit = webapp.RATE_LIMITS["upload"]
    old_max = webapp.MAX_UPLOADS
    webapp.RATE_LIMITS["upload"] = 3
    webapp.MAX_UPLOADS = 2
    webapp._rate.clear()
    try:
        font = (ASSETS / "fonts" / "Bungee-Regular.ttf").read_bytes()
        codes = [
            client.post(
                "/api/upload?kind=font", files={"file": (f"f{i}.ttf", font, "font/ttf")}
            ).status_code
            for i in range(4)
        ]
        assert codes[:3] == [200, 200, 200] and codes[3] == 429
        assert len(webapp.UPLOADS) <= 2                      # oldest evicted
    finally:
        webapp.RATE_LIMITS["upload"] = old_limit
        webapp.MAX_UPLOADS = old_max
        webapp._rate.clear()


def test_client_paths_are_ignored():
    payload = {
        "params": {
            "content": {"text": "A", "cap_height_mm": 40, "font_path": "/etc/passwd"},
            "style": {"kind": "channel", "backer": "none"},
            "leds": {"kind": "none"},
        }
    }
    r = client.post("/api/preview2d", json=payload)
    assert r.status_code == 200          # bundled font used, path discarded
