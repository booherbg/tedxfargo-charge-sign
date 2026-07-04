#!/usr/bin/env python3
"""Render the panelizer result (word_cuts.json) two ways:
  - a PPM raster (tubes, cuts, screws) for quick eyeballing
  - an HTML page with an mm-accurate SVG + fit table, ready to publish as the cut-preview
Usage: cutpreview.py src/parts/word_cuts.json out.ppm out.html
"""
import json, math, sys

data = json.load(open(sys.argv[1]))
ppm_out, html_out = sys.argv[2], sys.argv[3]
fx0, fy0, fx1, fy1 = data["face"]
paths, cuts, pieces = data["paths"], data["cuts"], data["pieces"]
R = data["band_out"] / 2.0

# ---------- PPM (for terminal-side eyeballing) ----------
S = 1.5                                        # px per mm
W = int((fx1 - fx0) * S) + 20
H = int((fy1 - fy0) * S) + 20
img = bytearray(bytes((24, 27, 33)) * (W * H))
def P(x, y):                                   # mm -> px (flip y)
    return int((x - fx0) * S) + 10, H - 10 - int((y - fy0) * S)
def dot(x, y, r, c):
    cx, cy = P(x, y)
    rr = int(r * S)
    for dy in range(-rr, rr + 1):
        for dx in range(-rr, rr + 1):
            if dx*dx + dy*dy <= rr*rr and 0 <= cx+dx < W and 0 <= cy+dy < H:
                i = ((cy+dy) * W + cx+dx) * 3
                img[i:i+3] = bytes(c)
def stroke(pts, r, c, step=2.0):
    for i in range(len(pts) - 1):
        d = math.dist(pts[i], pts[i+1])
        for t in range(int(d / step) + 1):
            f = t * step / d if d else 0
            dot(pts[i][0] + (pts[i+1][0]-pts[i][0])*f, pts[i][1] + (pts[i+1][1]-pts[i][1])*f, r, c)
for p in paths:
    stroke(p, R, (60, 160, 178))               # band outer
for p in paths:
    stroke(p, R - 2.0, (95, 222, 246))         # channel-ish inner
for c in cuts:
    stroke(c, 1.2, (240, 190, 70), 1.5)
for pc in pieces:
    for sx, sy in pc["screws"]:
        dot(sx, sy, 3.0, (240, 130, 110))
with open(ppm_out, "wb") as f:
    f.write(b"P6\n%d %d\n255\n" % (W, H) + bytes(img))

# ---------- HTML/SVG (for the user) ----------
def path_d(pts):
    return "M " + " L ".join("%.1f %.1f" % (x - fx0, fy1 - y) for x, y in pts)
tubes = "".join('<path d="%s" fill="none" stroke="#5fdef6" stroke-width="%.1f" '
                'stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>' % (path_d(p), 2*R)
                for p in paths)
cutsvg = "".join('<path d="%s" fill="none" stroke="#f0be46" stroke-width="3" '
                 'stroke-dasharray="7 5"/>' % path_d(c) for c in cuts)
screws = "".join('<circle cx="%.1f" cy="%.1f" r="3.4" fill="#f08878"/>' % (sx - fx0, fy1 - sy)
                 for pc in pieces for sx, sy in pc["screws"])
labels = "".join('<text x="%.1f" y="%.1f" font-size="26" font-weight="700" fill="#98a2ae" '
                 'text-anchor="middle" font-family="ui-monospace,monospace">%d</text>'
                 % ((pc["x0"] + pc["x1"]) / 2 - fx0, fy1 - fy0 - 12, i + 1)
                 for i, pc in enumerate(pieces))
fw, fh = fx1 - fx0, fy1 - fy0
rows = "".join(
    '<tr><td>%d &middot; %s</td><td class="num">%.0f &times; %.0f</td><td class="num">%s</td>'
    '<td class="num">%d</td><td class="num">~%d g</td><td>%s</td></tr>'
    % (i + 1, pc["letter"], pc["w"], pc["h"],
       "%.1f" % data["bottlenecks_mm"][i] if i < len(cuts) else "—",
       pc["pixels"], pc["grams"],
       '<span class="v fits">FITS</span>' if pc["fits"] else '<span class="v over">OVER</span>')
    for i, pc in enumerate(pieces))
kern = ", ".join("%s|%s +%.1f" % ("CHARGE"[i], "CHARGE"[i+1], n)
                 for i, n in enumerate(data["kern_nudges_mm"]) if n > 0.2) or "none needed"

html = """<title>CHARGE — cut preview</title>
<style>
  :root { --bg:#14171c; --panel:#1a1e25; --line:#262c35; --text:#e6e9ed; --muted:#98a2ae;
          --neon:#5fdef6; --fit:#7fd99a; --over:#f08878; --mono:ui-monospace,"SF Mono",Menlo,monospace; }
  body { background:var(--bg); color:var(--text); font:16px/1.55 -apple-system,"Helvetica Neue",Arial,sans-serif;
         margin:0; padding:40px 24px 72px; }
  .wrap { max-width:1200px; margin:0 auto; display:flex; flex-direction:column; gap:26px; }
  .eyebrow { font:600 12px/1 var(--mono); letter-spacing:.18em; text-transform:uppercase; color:var(--neon); }
  h1 { font-size:29px; margin:10px 0 6px; letter-spacing:-.01em; }
  .dek { color:var(--muted); max-width:66ch; margin:0; }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:3px; padding:20px; }
  .figbox { overflow-x:auto; }
  svg { display:block; min-width:900px; width:100%%; height:auto; background:#101318; border-radius:2px; }
  table { border-collapse:collapse; width:100%%; font-variant-numeric:tabular-nums; }
  th { font:600 12px/1 var(--mono); letter-spacing:.12em; text-transform:uppercase; color:var(--muted);
       text-align:left; padding:8px 14px 8px 0; border-bottom:1px solid var(--line); }
  td { padding:9px 14px 9px 0; border-bottom:1px solid var(--line); font-size:14.5px; }
  td.num { font-family:var(--mono); font-size:14px; }
  .v { font:600 11.5px/1 var(--mono); padding:4px 9px; border-radius:999px; }
  .fits { color:#0e1512; background:var(--fit); } .over { color:#191008; background:var(--over); }
  .cap { color:var(--muted); font-size:13.5px; margin:8px 0 0; }
  .cap b { color:var(--text); }
</style>
<div class="wrap">
  <header>
    <div class="eyebrow">TEDxFargo CHARGE &middot; panelization</div>
    <h1>Cut preview — %(np)d pieces, face %(fw).0f &times; %(fh).0f mm</h1>
    <p class="dek">Amber dashed = seams (top-to-bottom through black field only; never through a
    tube). Red dots = wood-rail screw positions. Auto-kern applied: %(kern)s mm.</p>
  </header>
  <section class="panel">
    <div class="figbox">
    <svg viewBox="0 0 %(fw).0f %(fh).0f" role="img" aria-label="CHARGE face with cut lines">
      <rect x="0" y="0" width="%(fw).0f" height="%(fh).0f" fill="#16191f"/>
      %(tubes)s %(cutsvg)s %(screws)s %(labels)s
    </svg>
    </div>
    <p class="cap"><b>To scale in mm.</b> Tubes drawn at the printed 22 mm outer band width.</p>
  </section>
  <section class="panel">
    <table>
      <thead><tr><th>Piece</th><th>Size (mm)</th><th>Seam clearance (mm)</th><th>Pixels</th>
      <th>Est. weight</th><th>Bed fit</th></tr></thead>
      <tbody>%(rows)s</tbody>
    </table>
    <p class="cap">Seam clearance = distance from tube centerline to the cut at that seam's tightest
    point (band edge is at 11 mm). Bed limits: 316 &times; 296 mm with margins.</p>
  </section>
</div>
""" % {"np": len(pieces), "fw": fw, "fh": fh, "kern": kern,
       "tubes": tubes, "cutsvg": cutsvg, "screws": screws, "labels": labels, "rows": rows}
open(html_out, "w").write(html)
print("wrote %s (%dx%d) and %s" % (ppm_out, W, H, html_out))
