"""Shared kit verification: everything checked FROM THE FILES of a built kit.
Used by qa_gold.py (direct engine build) and qa_upload.py (web upload path)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def verify_kit(outdir: Path, bed: tuple[float, float], expect_pixels: int | None = None,
               log=print) -> list[str]:
    import numpy as np

    from signforge.export.stl import read_stl
    from signforge.verify import edge_report

    fails: list[str] = []

    def check(ok: bool, msg: str) -> None:
        log(f"  {'ok ' if ok else 'FAIL'} {msg}")
        if not ok:
            fails.append(msg)

    stls = sorted(Path(outdir, "stl").glob("*.stl"))
    check(len(stls) > 0, f"{len(stls)} STL(s) present")
    total_g = 0.0
    for f in stls:
        v, t = read_stl(f)
        rep = edge_report(v, t)
        check(rep["boundary"] == 0 and rep["pinch"] == 0 and rep["degenerate"] == 0,
              f"{f.name}: 2-manifold as-written ({rep['tris']} tris)")
        w = v[:, 0].max() - v[:, 0].min()
        h = v[:, 1].max() - v[:, 1].min()
        check(w <= bed[0] + 0.6 and h <= bed[1] + 0.6, f"{f.name}: fits bed ({w:.0f}×{h:.0f})")
        p0, p1, p2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
        total_g += float(np.einsum("ij,ij->i", p0, np.cross(p1, p2)).sum() / 6.0) / 1000 * 1.27

    for f in sorted(Path(outdir, "3mf").glob("*.3mf")):
        with zipfile.ZipFile(f) as z:
            names = set(z.namelist())
            ok = {"3D/3dmodel.model", "Metadata/model_settings.config"} <= names
            if ok:
                ET.fromstring(z.read("3D/3dmodel.model"))
                ok = 'key="extruder"' in z.read("Metadata/model_settings.config").decode()
            check(ok, f"{f.name}: parseable, extruder-mapped")

    for rel in ["BOM.md", "params.json", "preview/index.html", "preview/preview.png"]:
        check((outdir / rel).exists(), f"{rel} present")

    wled_path = outdir / "wled_ledmap.json"
    if expect_pixels:
        check(wled_path.exists(), "wled_ledmap.json present")
        if wled_path.exists():
            wled = json.loads(wled_path.read_text())
            leds = sorted(v for v in wled["map"] if v >= 0)
            check(leds == list(range(wled["n"])), f"WLED map: {wled['n']} LEDs each exactly once")
            check(wled["n"] == expect_pixels, f"WLED n == pixels ({expect_pixels})")

    bom = (outdir / "BOM.md").read_text() if (outdir / "BOM.md").exists() else ""
    for token in (["PSU", "data chain", "Import"] if expect_pixels else ["Import"]):
        check(token in bom, f"BOM mentions {token}")
    log(f"  ·  total filament {total_g:.0f} g")
    return fails
