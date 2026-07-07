#!/usr/bin/env python3
"""Upload-path QA: CHARGE.svg through the ACTUAL web stack — multipart upload,
live preview, queued build, downloaded zip — verified file-by-file, plus
preview↔build consistency and pitch reconfiguration.

Run: uv run python scripts/qa_upload.py
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from qa_kit import verify_kit  # noqa: E402

CHARGE = Path(__file__).resolve().parents[2] / "assets" / "svg" / "CHARGE.svg"
FAILS: list[str] = []


def check(ok: bool, msg: str) -> None:
    print(f"  {'ok ' if ok else 'FAIL'} {msg}")
    if not ok:
        FAILS.append(msg)


def payload(art_token: str, pitch: float = 17.0) -> dict:
    return {
        "art_token": art_token,
        "params": {
            "name": "charge-web",
            "content": {"art_target_height_mm": 250, "cap_height_mm": 250},
            "style": {"kind": "neon", "backer": "tile", "tile_margin_mm": 22.5},
            "texture": {"mode": "pyramid_jitter"},
            "leds": {"kind": "bullet12", "pitch_mm": pitch, "budget_px": 600},
            "colors": {"palette": "charge-classic"},
            "printer": {"preset": "bambu-h2d-dual"},
        },
    }


def wait_done(client, job: str, timeout_s: float = 600) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        st = client.get(f"/api/jobs/{job}").json()
        if st["status"] in ("done", "error", "cancelled"):
            return st
        time.sleep(0.4)
    return {"status": "timeout"}


def main() -> int:
    if not CHARGE.exists():
        print("CHARGE.svg not found — cannot run upload QA")
        return 2

    from fastapi.testclient import TestClient

    from signforge.web.app import create_app

    app = create_app(open_mode=True, db_path=tempfile.mktemp(),
                     workdir=tempfile.mkdtemp(), workers=1)
    client = TestClient(app)

    print("== upload ==")
    r = client.post("/api/upload?kind=art",
                    files={"file": ("CHARGE.svg", CHARGE.read_bytes(), "image/svg+xml")})
    check(r.status_code == 200, f"upload accepted ({r.status_code})")
    token = r.json()["token"]

    print("\n== live preview (the console's fast path) ==")
    pv = client.post("/api/preview2d", json=payload(token)).json()
    check("error" not in pv, "preview computes")
    check(1400 <= pv["sign_mm"][0] <= 1650, f"preview width {pv['sign_mm'][0]:.0f}")
    check(380 <= pv["pixels"] <= 480, f"preview pixels {pv['pixels']}")
    check(pv["watts"] == round(pv["pixels"] * 0.25, 1), f"watts math {pv['watts']}")
    check(pv["psu"] >= pv["watts"] / 0.8, f"PSU {pv['psu']}W covers {pv['watts']}W at 80%")

    print("\n== queued build through the web ==")
    r = client.post("/api/build", json=payload(token))
    check(r.status_code == 200, "build accepted")
    st = wait_done(client, r.json()["job"])
    check(st["status"] == "done",
          f"job finished: {st['status']} {(st.get('error') or '')[:90]}")
    s = st["stats"]

    print("\n== preview ↔ build consistency ==")
    check(s["pixels"] == pv["pixels"], f"pixels: build {s['pixels']} == preview {pv['pixels']}")
    check(s["pieces"] == pv["pieces"], f"pieces: build {s['pieces']} == preview {pv['pieces']}")
    check(s["sign_mm"] == pv["sign_mm"], "sign dimensions identical")

    print("\n== downloaded kit verified file-by-file ==")
    job = r.json()["job"]
    dl = client.get(f"/api/jobs/{job}/download")
    check(dl.status_code == 200, "zip downloads")
    kit = Path(tempfile.mkdtemp())
    zipfile.ZipFile(io.BytesIO(dl.content)).extractall(kit)
    FAILS.extend(verify_kit(kit, (316.0, 295.0), expect_pixels=s["pixels"]))
    check(client.get(f"/api/jobs/{job}/thumb.png").status_code == 200, "thumbnail serves")
    check(client.get(f"/api/jobs/{job}/preview").status_code == 200, "dashboard serves")
    viewer = client.get(f"/api/jobs/{job}/viewer")
    check(viewer.status_code == 200 or any("too large" in w for w in st.get("warnings", [])),
          f"3D viewer serves or size-capped honestly ({viewer.status_code})")

    print("\n== pitch reconfiguration (the config knob, end to end) ==")
    pv25 = client.post("/api/preview2d", json=payload(token, pitch=25.0)).json()
    ratio = pv25["pixels"] / pv["pixels"]
    check(0.55 <= ratio <= 0.80, f"pitch 17→25: pixels {pv['pixels']}→{pv25['pixels']} (×{ratio:.2f})")
    r25 = client.post("/api/build", json=payload(token, pitch=25.0))
    st25 = wait_done(client, r25.json()["job"])
    check(st25["status"] == "done", "pitch-25 build finishes")
    check(st25["stats"]["pixels"] == pv25["pixels"], "pitch-25 preview == build")
    dl25 = client.get(f"/api/jobs/{r25.json()['job']}/download")
    kit25 = Path(tempfile.mkdtemp())
    zipfile.ZipFile(io.BytesIO(dl25.content)).extractall(kit25)
    wled25 = json.loads((kit25 / "wled_ledmap.json").read_text())
    check(wled25["n"] == pv25["pixels"], "pitch-25 WLED map matches")

    print(f"\n{'UPLOAD PATH HOLDS' if not FAILS else f'{len(FAILS)} FAILURES'}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
