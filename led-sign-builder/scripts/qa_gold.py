#!/usr/bin/env python3
"""Gold-standard QA: build the CHARGE replica and verify EVERYTHING from the
exported files outward (not from in-memory state). Exit 0 = baseline holds.

Run: uv run python scripts/qa_gold.py [--keep OUTDIR]
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

CHARGE = Path(__file__).resolve().parents[2] / "assets" / "svg" / "CHARGE.svg"

FAILS: list[str] = []


def check(ok: bool, msg: str) -> None:
    tag = "ok " if ok else "FAIL"
    print(f"  {tag} {msg}")
    if not ok:
        FAILS.append(msg)


def main() -> int:
    if not CHARGE.exists():
        print("CHARGE.svg not found (needs the parent repo) — cannot run gold QA")
        return 2

    from signforge.export.stl import read_stl
    from signforge.params import SignParams
    from signforge.pipeline import build
    from signforge.verify import edge_report

    keep = "--keep" in sys.argv
    outdir = Path(sys.argv[sys.argv.index("--keep") + 1]) if keep else Path(tempfile.mkdtemp())

    params = SignParams.model_validate(
        {
            "name": "charge",
            "content": {"mode": "art", "art_path": str(CHARGE), "art_target_height_mm": 250},
            "style": {"kind": "neon", "backer": "tile", "tile_margin_mm": 22.5},
            "texture": {"mode": "pyramid_jitter"},
            "leds": {"kind": "bullet12", "pitch_mm": 17, "budget_px": 600},
            "colors": {"palette": "charge-classic"},
            "printer": {"preset": "bambu-h2d-dual"},
        }
    )
    print("== building the gold standard (textured, budgeted, H2D) ==")
    result = build(params, outdir, progress=lambda m: None)
    s = result.stats

    print("\n== production-constant comparison ==")
    check(1400 <= s["sign_mm"][0] <= 1650, f"sign width {s['sign_mm'][0]:.0f} (production face 1597)")
    check(abs(s["sign_mm"][1] - 250) < 2, f"cap height {s['sign_mm'][1]:.0f} (production 250)")
    check(4 <= s["pieces"] <= 7, f"pieces {s['pieces']} (production 6)")
    check(380 <= s["pixels"] <= 480, f"pixels {s['pixels']} (production 454 post-repairs)")
    check(s["pixels"] <= 600, f"budget respected: {s['pixels']} ≤ 600 purchased")
    check(not any("BUDGET" in w for w in result.warnings), "no budget overrun warning")

    print("\n== mesh QA from the exported files ==")
    bed = params.printer.bed
    stls = sorted(Path(outdir, "stl").glob("*.stl"))
    check(len(stls) >= s["pieces"] * 2, f"{len(stls)} STLs for {s['pieces']} pieces")
    total_g = 0.0
    for f in stls:
        v, t = read_stl(f)
        rep = edge_report(v, t)
        check(
            rep["boundary"] == 0 and rep["pinch"] == 0 and rep["degenerate"] == 0,
            f"{f.name}: 2-manifold ({rep['tris']} tris)",
        )
        w = v[:, 0].max() - v[:, 0].min()
        h = v[:, 1].max() - v[:, 1].min()
        check(w <= bed[0] + 0.6 and h <= bed[1] + 0.6, f"{f.name}: fits bed ({w:.0f}×{h:.0f})")
        p0, p1, p2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
        import numpy as np

        vol = float(np.einsum("ij,ij->i", p0, np.cross(p1, p2)).sum() / 6.0)
        total_g += vol / 1000 * 1.27
    check(1000 < total_g < 4000, f"total filament {total_g:.0f} g (production word ≈ 1.9–3.1 kg class)")

    print("\n== cross-section constants measured from meshes ==")
    shell = next((f for f in stls if "piece1_shell" in f.name or f.name.endswith("_shell.stl")), None)
    lens = next((f for f in stls if "lens" in f.name), None)
    if shell:
        v, _ = read_stl(shell)
        check(abs(v[:, 2].min() - 0.0) < 0.01 and abs(v[:, 2].max() - 21.0) < 0.2,
              f"shell z: 0..{v[:, 2].max():.1f} (plate 2.0 + wall 19)")
    if lens:
        v, _ = read_stl(lens)
        zmax = v[:, 2].max()
        check(21.5 <= zmax <= 23.2, f"lens z-top {zmax:.2f} (21+1.2 lens + ≤0.7 texture)")

    print("\n== 3MF structure (Bambu mapping) ==")
    for f in sorted(Path(outdir, "3mf").glob("*.3mf")):
        with zipfile.ZipFile(f) as z:
            names = set(z.namelist())
            ok = {"3D/3dmodel.model", "Metadata/model_settings.config"} <= names
            if ok:
                ET.fromstring(z.read("3D/3dmodel.model"))
                cfg = z.read("Metadata/model_settings.config").decode()
                ok = 'key="extruder"' in cfg
            check(ok, f"{f.name}: parseable, extruder-mapped")

    print("\n== kit artifacts ==")
    for rel in ["BOM.md", "params.json", "wled_ledmap.json", "preview/index.html",
                "preview/preview.png", "preview/debug_tubes.png"]:
        check((outdir / rel).exists(), f"{rel} present")
    zips = list(outdir.glob("*.zip"))
    check(len(zips) == 1, "kit zip present")
    wled = json.loads((outdir / "wled_ledmap.json").read_text())
    leds_in_map = sorted(v for v in wled["map"] if v >= 0)
    check(leds_in_map == list(range(wled["n"])), f"WLED map: {wled['n']} LEDs, each exactly once")
    check(wled["n"] == s["pixels"], "WLED n == pixel count")
    bom = (outdir / "BOM.md").read_text()
    for token in ["PSU", "data chain", "Import", "wled_ledmap.json"]:
        check(token in bom, f"BOM mentions {token}")
    replay = SignParams.from_json((outdir / "params.json").read_text())
    check(replay == params, "params.json reproduces the build")

    print("\n== treatment sanity ==")
    check(not any("outline:" in w for w in result.warnings), "tube-art → skeleton (no outline fallbacks)")
    check(not any("coverage QA FAILED" in w for w in result.warnings), "coverage clean")

    print(f"\n{'GOLD BASELINE HOLDS' if not FAILS else f'{len(FAILS)} FAILURES'}"
          + (f" — kit kept at {outdir}" if keep else ""))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
