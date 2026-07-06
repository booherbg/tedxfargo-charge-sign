"""Self-contained HTML preview: mm-accurate 2D SVG + production tables.

Follows the CHARGE dashboard visual language (gen_cutpreview.py): tubes as
round-capped strokes, fills as paths, pixels as circles, piece seams dashed,
per-piece production table with totals. Zero JS, zero network — inline SVG+CSS.
"""

from __future__ import annotations

from ..geom2d import as_multipolygon
from ..model import Layout, LedPlan, Piece
from ..params import SignParams

CSS = """
body{font:14px/1.45 -apple-system,system-ui,Segoe UI,Roboto,sans-serif;margin:24px;
     background:#101014;color:#e8e8ee}
h1{font-size:20px;margin:0 0 4px} h2{font-size:15px;margin:24px 0 8px;color:#9aa}
.sub{color:#889;margin:0 0 16px}
figure{margin:0;padding:12px;background:#16161c;border:1px solid #26262e;border-radius:10px}
svg{display:block;width:100%;height:auto}
table{border-collapse:collapse;margin-top:8px;width:100%}
td,th{border:1px solid #2a2a33;padding:5px 9px;text-align:right;font-variant-numeric:tabular-nums}
th{background:#1b1b22;color:#aab} td:first-child,th:first-child{text-align:left}
.tot td{font-weight:600;background:#191922}
.warn{color:#ffb0c0} .ok{color:#9fdcaa}
footer{margin-top:18px;color:#667;font-size:12px}
"""


def _path_d(mpoly) -> str:
    d = []
    for p in as_multipolygon(mpoly).geoms:
        for ring in [p.exterior, *p.interiors]:
            pts = list(ring.coords)
            d.append("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts[:-1]) + " Z")
    return " ".join(d)


def render_preview(
    layout: Layout,
    pieces: list[Piece],
    ledplan: LedPlan | None,
    stats: dict,
    params: SignParams,
    body_notes: list[str] | None = None,
) -> str:
    x0, y0, x1, y1 = layout.bbox
    pad = 25.0
    if layout.backer is not None:
        bx0, by0, bx1, by1 = layout.backer.bounds
        x0, y0, x1, y1 = min(x0, bx0), min(y0, by0), max(x1, bx1), max(y1, by1)
    vw, vh = (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad
    c = params.colors.preview

    el: list[str] = []
    if layout.backer is not None:
        el.append(
            f'<path d="{_path_d(as_multipolygon(layout.backer))}" fill="#1d1d25" '
            f'stroke="#3a3a46" stroke-width="1"/>'
        )
    if params.style.kind == "neon":
        w_out = params.style.neon.band_outer
        w_in = params.style.neon.channel_interior
        for s in layout.strokes:
            pts = s.pts + ([s.pts[0]] if s.closed else [])
            pl = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
            el.append(
                f'<polyline points="{pl}" fill="none" stroke="{c["shell"]}" '
                f'stroke-width="{w_out}" stroke-linecap="round" stroke-linejoin="round"/>'
            )
            el.append(
                f'<polyline points="{pl}" fill="none" stroke="{c["lens"]}" opacity="0.85" '
                f'stroke-width="{w_in}" stroke-linecap="round" stroke-linejoin="round"/>'
            )
    elif layout.fills is not None:
        el.append(
            f'<path d="{_path_d(layout.fills)}" fill="{c["lens"]}" fill-opacity="0.8" '
            f'fill-rule="evenodd" stroke="{c["shell"]}" stroke-width="1.2"/>'
        )
    for pc in pieces[1:]:
        el.append(
            f'<path d="{_path_d(as_multipolygon(pc.mask))}" fill="none" '
            f'stroke="{c["seam"]}" stroke-width="0.8" stroke-dasharray="4 3"/>'
        )
    if ledplan:
        r = params.leds.bore_mm / 2
        for px, py in ledplan.pixels:
            el.append(
                f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{r:.2f}" fill="{c["pixel"]}" '
                f'fill-opacity="0.9"/>'
            )

    labels = ""
    if len(pieces) > 1:
        for pc in pieces:
            lc = pc.mask.centroid
            labels += (
                f'<text x="{lc.x:.1f}" y="{-(pc.mask.bounds[1] + 8):.1f}" fill="{c["seam"]}" '
                f'font-size="14" text-anchor="middle" font-family="system-ui">{pc.label}'
                + (" ⟳" if pc.rotated else "")
                + "</text>"
            )
    svg = (
        f'<svg viewBox="{x0 - pad:.1f} {-(y1 + pad):.1f} {vw:.1f} {vh:.1f}" '
        f'xmlns="http://www.w3.org/2000/svg"><g transform="scale(1,-1)">'
        + "".join(el)
        + "</g>"
        + labels
        + "</svg>"
    )

    rows = []
    for name, b in stats.get("bodies", {}).items():
        rows.append(
            f"<tr><td>{name}</td><td>{b['extruder']}</td><td>{b['tris']:,}</td>"
            f"<td>{b['volume_mm3']:,.0f}</td><td>{b['grams_petg']:.1f}</td></tr>"
        )
    total = stats.get("total_grams_petg", 0)
    body_table = (
        "<table><tr><th>body</th><th>filament</th><th>triangles</th>"
        "<th>volume mm³</th><th>grams (PETG)</th></tr>"
        + "".join(rows)
        + f'<tr class="tot"><td>total</td><td></td><td></td><td></td><td>{total:.1f}</td></tr></table>'
    )

    power_html = ""
    if ledplan and ledplan.power.count:
        p = ledplan.power
        budget = (
            f' / <span class="{"warn" if p.over_budget else "ok"}">{p.budget_px} budget</span>'
            if p.budget_px
            else ""
        )
        power_html = (
            f"<h2>Power</h2><table><tr><th>pixels</th><th>watts</th><th>amps @ "
            f"{params.leds.volts:.0f}V</th><th>PSU</th><th>strings of 50</th></tr>"
            f"<tr><td>{p.count}{budget}</td><td>{p.watts:.0f}</td><td>{p.amps:.1f}</td>"
            f"<td>{p.psu_watts} W</td><td>{p.strings}</td></tr></table>"
        )
        if ledplan.audits:
            power_html += "<h2>Audits</h2><ul>" + "".join(
                f'<li class="warn">{a}</li>' for a in ledplan.audits
            ) + "</ul>"

    pieces_html = ""
    detail = stats.get("pieces_detail", [])
    if len(detail) > 1:
        rows = "".join(
            f"<tr><td>{d['label']}{' ⟳ rotate on bed' if d['rotated'] else ''}</td>"
            f"<td>{d['pixels']}</td><td>{d['grams']:.0f}</td></tr>"
            for d in detail
        )
        pieces_html = (
            "<h2>Pieces</h2><table><tr><th>piece</th><th>pixels</th>"
            f"<th>grams</th></tr>{rows}</table>"
        )

    notes_html = ""
    if body_notes:
        notes_html = "<h2>Build notes</h2><ul>" + "".join(
            f"<li>{n}</li>" for n in body_notes
        ) + "</ul>"

    w_mm, h_mm = stats.get("sign_mm", [0, 0])
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{params.name} — LED Sign Builder</title>
<style>{CSS}</style></head><body>
<h1>{params.name}</h1>
<p class="sub">{params.style.kind} style · {w_mm:.0f} × {h_mm:.0f} mm ·
{len(pieces) or 1} piece(s) · {stats.get("source", "")}</p>
<p><a href="viewer.html" style="color:#7ec8ff">open the 3D viewer →</a></p>
<figure>{svg}</figure>
{pieces_html}
<h2>Bodies</h2>{body_table}
{power_html}
{notes_html}
<footer>Generated by signforge — files in this kit are reproducible from params.json.
Bambu: load 3MFs with File→Import (Open resets project settings).</footer>
</body></html>"""
