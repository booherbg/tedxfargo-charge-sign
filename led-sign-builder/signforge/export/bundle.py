"""BOM/print-card generation and the final zip bundle."""

from __future__ import annotations

import zipfile
from pathlib import Path

from ..model import LedPlan
from ..params import SignParams

PSU_SIZES = [60, 100, 150, 200, 350, 500]


def psu_pick(watts: float, headroom: float) -> int:
    need = watts / headroom if headroom > 0 else watts
    for size in PSU_SIZES:
        if size >= need:
            return size
    return PSU_SIZES[-1]


def render_bom(
    params: SignParams, stats: dict, ledplan: LedPlan | None, warnings: list[str]
) -> str:
    lines: list[str] = [
        f"# {params.name} — build sheet",
        "",
        f"- Style: **{params.style.kind}**, backer: {params.style.backer}",
        f"- Sign size: **{stats['sign_mm'][0]:.0f} × {stats['sign_mm'][1]:.0f} mm**",
        f"- Printer envelope: {params.printer.preset} "
        f"({params.printer.bed[0]:.0f}×{params.printer.bed[1]:.0f} mm)",
        "",
        "## Printed bodies",
        "",
        "| body | filament slot | volume mm³ | grams (PETG) |",
        "|---|---|---|---|",
    ]
    for name, b in stats.get("bodies", {}).items():
        lines.append(
            f"| {name} | {b['extruder']} | {b['volume_mm3']:,.0f} | {b['grams_petg']:.1f} |"
        )
    lines += [
        f"| **total** | | | **{stats.get('total_grams_petg', 0):.1f}** |",
        "",
        "Suggested filaments: slot 1 = opaque (black), slot 2 = white, slot 3 = clear/natural.",
        "White interiors recycle light — never a dark interior facing the LEDs.",
    ]

    if ledplan and ledplan.power.count == 0 and ledplan.power.watts > 0:
        p = ledplan.power
        lines += [
            "",
            "## Electrical (LED strip)",
            "",
            f"- Load: {p.watts:.0f} W ({p.amps:.1f} A @ {params.leds.volts:.0f} V) → "
            f"**{p.psu_watts} W PSU** (kept ≤{params.leds.psu_headroom:.0%})",
        ] + [f"- {a}" for a in ledplan.audits]

    if ledplan and ledplan.power.count:
        from ..leds import chain_hops, chain_length_mm

        p = ledplan.power
        hops = chain_hops(ledplan.pixels, ledplan.per_stroke)
        jumpers = [h for h in hops if h[2]]
        chain_m = chain_length_mm(ledplan.pixels, ledplan.per_stroke) / 1000
        lines += [
            "",
            "## Electrical",
            "",
            f"- Pixels: **{p.count}** × 12 mm bullet ({params.leds.volts:.0f} V, "
            f"{params.leds.watts_per_px} W each)"
            + (f" — budget {p.budget_px} " + ("**OVER**" if p.over_budget else "OK") if p.budget_px else ""),
            f"- Load: {p.watts:.0f} W ({p.amps:.1f} A) → **{p.psu_watts} W PSU** "
            f"(kept ≤{params.leds.psu_headroom:.0%})",
            f"- Strings of 50: {p.strings} (spares = last string's tail)",
            f"- One data chain, {chain_m:.1f} m point-to-point (plan ~{chain_m * 1.25:.1f} m "
            f"with slack); **{len(jumpers)} extension jumper(s)** needed"
            + (
                " at: "
                + "; ".join(f"({a[0]:.0f},{a[1]:.0f})→({b[0]:.0f},{b[1]:.0f})" for a, b, _ in jumpers)
                if jumpers
                else ""
            ),
            "- Wiring order is drawn on the preview (green chain, orange dashed jumpers,",
            "  DATA IN ring at the first pixel).",
        ]
        if ledplan.audits:
            lines += ["", "### Spacing audits", ""] + [f"- ⚠ {a}" for a in ledplan.audits]

    lines += [
        "",
        "## Print card",
        "",
        "- Print **lens-up / plate-down, no supports**. Parts are emitted in print",
        "  orientation; flip-to-use parts are already mirrored.",
        "- 0.16–0.20 mm layers · 2 walls · 10% gyroid · 6 top / 6 bottom · brim on big plates.",
        "- Bambu: load 3MFs with **File→Import** (Open resets project settings).",
        "- Multi-color pieces must sit fully inside the multi-nozzle zone on dual-head machines.",
    ]
    if params.texture.mode != "none":
        lines += [
            "- Textured lens: set **bottom shell layers +1** (or lens infill 100%) to avoid",
            "  harmless mid-lens island artifacts; top surface pattern **Concentric**.",
        ]
    if warnings:
        lines += ["", "## Build warnings", ""] + [f"- {w}" for w in warnings]
    lines += ["", "---", "Reproduce this kit: `signforge build --params params.json -o out/`", ""]
    return "\n".join(lines)


def zip_bundle(outdir: str | Path, name: str, files: list[str]) -> str:
    out = Path(outdir)
    zpath = out / f"{name}-kit.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=4) as z:
        for f in files:
            fp = Path(f)
            z.write(fp, fp.relative_to(out))
    return str(zpath)
