"""signforge CLI: build sign kits, run the web UI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .params import PRESET_PARAMS, SignParams, preset_params
from .pipeline import build
from .verify import BuildError


def _params_from_args(args: argparse.Namespace) -> SignParams:
    if args.params:
        p = SignParams.from_json(Path(args.params).read_text())
    elif args.preset:
        p = preset_params(args.preset)
    else:
        p = SignParams()
    if args.text:
        p.content.mode = "text"
        p.content.text = args.text
    if args.font:
        p.content.font_path = args.font
    if args.art:
        p.content.mode = "art"
        p.content.art_path = args.art
    if args.style:
        p.style.kind = args.style
    if args.backer:
        p.style.backer = args.backer
    if args.cap_height:
        p.content.cap_height_mm = args.cap_height
        p.content.art_target_height_mm = args.cap_height
    if args.printer:
        p.printer.preset = args.printer
    if args.name:
        p.name = args.name
    return p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="signforge", description="LED Sign Builder")
    ap.add_argument("--version", action="version", version=f"signforge {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build a sign kit")
    b.add_argument("--params", help="params.json (reproducible build)")
    b.add_argument("--preset", choices=sorted(PRESET_PARAMS), help="start from a preset")
    b.add_argument("--text", help="sign text (use \\n for multi-line)")
    b.add_argument("--font", help="TTF/OTF/WOFF/WOFF2 path (default: bundled Bungee)")
    b.add_argument("--art", help="SVG/DXF/PNG artwork path instead of text")
    b.add_argument("--style", choices=["neon", "channel"])
    b.add_argument("--backer", choices=["tile", "contour", "none"])
    b.add_argument("--cap-height", type=float, dest="cap_height", help="letter height, mm")
    b.add_argument("--printer", help="printer preset (see docs)")
    b.add_argument("--name", help="output base name")
    b.add_argument("-o", "--out", required=True, help="output directory")

    s = sub.add_parser("serve", help="run the local web UI")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8763)

    c = sub.add_parser("coupon", help="print a fit-ladder before committing to a fit")
    c.add_argument("--values", default="0.1,0.0,-0.1,-0.2,-0.3",
                   help="comma-separated lip clearances (negative = interference)")
    c.add_argument("-o", "--out", required=True)

    args = ap.parse_args(argv)

    if args.cmd == "build":
        params = _params_from_args(args)
        try:
            result = build(params, args.out, progress=lambda m: print(f"  · {m}"))
        except BuildError as e:
            print(f"BUILD FAILED: {e}", file=sys.stderr)
            return 1
        print(json.dumps(result.stats, indent=2))
        for w in result.warnings:
            print(f"  ! {w}")
        print(f"wrote {len(result.files)} file(s) to {result.outdir}")
        return 0

    if args.cmd == "serve":
        import uvicorn

        from .web.app import app

        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    if args.cmd == "coupon":
        from pathlib import Path

        from .coupons import fit_ladder
        from .export.stl import stl_bytes
        from .export.threemf import write_3mf
        from .solids import mesh_of
        from .verify import gated_mesh

        outdir = Path(args.out)
        outdir.mkdir(parents=True, exist_ok=True)
        values = [float(v) for v in args.values.split(",")]
        bodies, notes = fit_ladder(SignParams(), values)
        parts = []
        for b in bodies:
            v, t = mesh_of(b.man)
            v, t, _ = gated_mesh(v, t, f"coupon_{b.name}")
            (outdir / f"fit_ladder_{b.name}.stl").write_bytes(stl_bytes(v, t))
            parts.append((b.name, v, t, b.extruder))
        write_3mf(outdir / "fit_ladder.3mf", parts)
        for n in notes:
            print(f"  · {n}")
        print(f"wrote fit ladder ({len(values)} rungs) to {outdir}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
