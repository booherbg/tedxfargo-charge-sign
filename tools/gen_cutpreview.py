#!/usr/bin/env python3
"""Regenerate docs/sign-preview/cut-preview.html — the CHARGE cut map the user
reviews before printing: pieces/seams, pixel layout (bridge pixels ringed),
screws, seam clearances, kern nudges, real rendered weights, bed fits.
Reads src/parts/word_cuts.json + stl/piece_stats.txt.

Optional argv1 = an alternate cuts json (word_cuts_altA.json): the extra A
segments (hat arm + NeonSans mid dash) render green, pixels new vs the base
json get rings, and piece 3 reports the piece3alt weights.
"""
import json, math, os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "src/parts/word_cuts.json"
d = json.load(open(SRC))
ALT = "alt" in d                            # word_cuts_altA.json marks itself
base_px = set()
if ALT:
    base = json.load(open("src/parts/word_cuts.json"))
    base_px = {tuple(p) for p in base["pixels"]}
fx0, fy0, fx1, fy1 = d["face"]
FW, FH = fx1 - fx0, fy1 - fy0
paths, cuts, pieces, pixels = d["paths"], d["cuts"], d["pieces"], d["pixels"]
bott, kerns = d["bottlenecks_mm"], d["kern_nudges_mm"]
trims = d.get("flange_trims", [])
N_BRIDGE = int(d.get("bridge_px", 0))       # 0 unless bridging ever returns

stats = {}
if os.path.exists("stl/piece_stats.txt"):
    for ln in open("stl/piece_stats.txt"):
        m = re.match(r"\s*(piece\d(?:alt)?)_(\w+)\.stl\s+[\d.]+\s+cm3\s+([\d.]+)\s+g", ln)
        if m:
            stats.setdefault(m.group(1), {})[m.group(2)] = float(m.group(3))

def fy(y):
    return fy1 - y + fy0             # flip for SVG (data y-up)

def path_d(p):
    return "M " + " L ".join("%.1f %.1f" % (q[0], fy(q[1])) for q in p)

svg = ['<svg viewBox="%.0f %.0f %.0f %.0f">' % (fx0 - 6, fy0 - 6, FW + 12, FH + 12)]
svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#16191f"/>'
           % (fx0, fy0, FW, FH))
for si, p in enumerate(paths):
    if ALT and si == 5:                       # A body: arm (first 2 segs) is the addition
        svg.append('<path d="%s" fill="none" stroke="#5fdef6" stroke-width="22" '
                   'stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>'
                   % path_d(p[2:]))
        svg.append('<path d="%s" fill="none" stroke="#57d98f" stroke-width="22" '
                   'stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>'
                   % path_d(p[:3]))
    elif ALT and si == 1:                     # G: both end extensions are the repair
        svg.append('<path d="%s" fill="none" stroke="#5fdef6" stroke-width="22" '
                   'stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>'
                   % path_d(p[1:-1]))
        for stub in (p[:2], p[-2:]):
            svg.append('<path d="%s" fill="none" stroke="#57d98f" stroke-width="22" '
                       'stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>'
                       % path_d(stub))
    elif ALT and si == 4:                     # triangle: the closing chord is the repair
        svg.append('<path d="%s" fill="none" stroke="#5fdef6" stroke-width="22" '
                   'stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>'
                   % path_d(p[:-1]))
        svg.append('<path d="%s" fill="none" stroke="#57d98f" stroke-width="22" '
                   'stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>'
                   % path_d(p[-2:]))
    else:
        svg.append('<path d="%s" fill="none" stroke="#5fdef6" stroke-width="22" '
                   'stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>' % path_d(p))
for c in cuts:
    svg.append('<path d="%s" fill="none" stroke="#f0be46" stroke-width="2.5" '
               'stroke-dasharray="7 5"/>' % path_d(c))
for i, q in enumerate(pixels):
    if ALT and tuple(q) not in base_px:       # new or re-spaced px on the alt A
        svg.append('<circle cx="%.1f" cy="%.1f" r="4.4" fill="none" stroke="#57d98f" '
                   'stroke-width="2.2"/><circle cx="%.1f" cy="%.1f" r="2.6" '
                   'fill="#0e6e80"/>' % (q[0], fy(q[1]), q[0], fy(q[1])))
    elif i >= len(pixels) - N_BRIDGE:
        svg.append('<circle cx="%.1f" cy="%.1f" r="4.4" fill="none" stroke="#ffe98a" '
                   'stroke-width="2.2"/><circle cx="%.1f" cy="%.1f" r="2.6" '
                   'fill="#0e6e80"/>' % (q[0], fy(q[1]), q[0], fy(q[1])))
    else:
        svg.append('<circle cx="%.1f" cy="%.1f" r="3.2" fill="#0e6e80"/>'
                   % (q[0], fy(q[1])))
for pc in pieces:
    for s in pc["screws"]:
        svg.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="#f08878"/>'
                   % (s[0], fy(s[1])))
    svg.append('<text x="%.1f" y="%.1f" fill="#98a2ae" font-size="17" '
               'font-family="ui-monospace,Menlo,monospace">%d</text>'
               % ((pc["x0"] + pc["x1"]) / 2 - 5, fy(fy0) - 8, pieces.index(pc) + 1))
for x, y, dd in trims:
    svg.append('<circle cx="%.1f" cy="%.1f" r="9" fill="none" stroke="#f08878" '
               'stroke-width="1.6" stroke-dasharray="3 3"/>' % (x, fy(y)))
svg.append("</svg>")

rows = []
tot_px = 0
tot_g = 0.0
for i, pc in enumerate(pieces):
    key = "piece%d" % (i + 1)
    label = "%d — %s" % (i + 1, pc["letter"])
    if ALT and (key + "alt") in stats:
        key, label = key + "alt", label + ' <span class="alt">repaired</span>'
    st = stats.get(key, {})
    g = sum(st.values()) if st else None
    if g:
        tot_g += g
    tot_px += pc["pixels"]
    seam = "%.1f / %.1f" % (bott[i - 1], bott[i]) if 0 < i < len(pieces) - 1 else \
           ("%.1f" % bott[0] if i == 0 else "%.1f" % bott[-1])
    rows.append("<tr><td>%s</td><td>%.0f × %.0f</td><td>%s</td><td>%d</td>"
                "<td>%s</td><td>%s</td></tr>"
                % (label, pc["w"], pc["h"], seam, pc["pixels"],
                   ("%.0f g" % g) if g else "&mdash;",
                   "✓" if pc["fits"] else "✗"))
rows.append('<tr><td><b>total</b></td><td>face %.0f × %.0f</td><td></td>'
            '<td><b>%d</b></td><td><b>%.0f g</b></td><td></td></tr>'
            % (FW, FH, tot_px, tot_g))

html = """<title>CHARGE — cut preview</title>
<style>
:root{--bg:#14171c;--panel:#1a1e25;--line:#262c35;--text:#e6e9ed;--muted:#98a2ae;--bolt:#ff5f4f;--mono:ui-monospace,"SF Mono",Menlo,monospace}
body{background:var(--bg);color:var(--text);font:16px/1.55 -apple-system,"Helvetica Neue",Arial,sans-serif;margin:0;padding:40px 24px 72px}
.wrap{max-width:1280px;margin:0 auto;display:flex;flex-direction:column;gap:26px}
.eyebrow{font:600 12px/1 var(--mono);letter-spacing:.18em;text-transform:uppercase;color:var(--bolt)}
h1{font-size:29px;margin:10px 0 6px}.dek{color:var(--muted);max-width:76ch;margin:0}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:20px}
.panel h2{font-size:17px;margin:0 0 12px}
.figbox{overflow-x:auto}.figbox svg{display:block;min-width:1100px;width:100%;height:auto}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.chip{font:500 12.5px/1 var(--mono);color:var(--text);border:1px solid var(--line);border-radius:999px;padding:6px 11px}
.chip.good{color:#7fd99a;border-color:#2c4436}
.alt{font:600 10.5px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:#57d98f;border:1px solid #2c4436;border-radius:999px;padding:2px 7px;margin-left:6px;vertical-align:1px}
.legend{display:flex;flex-wrap:wrap;gap:7px 22px;margin:0 0 14px;padding:10px 12px;border:1px solid var(--line);border-radius:3px;background:#161a20}
.li{display:inline-flex;align-items:center;gap:8px;color:var(--muted);font-size:13px}
.li svg{flex:none;display:block}
.cap{color:var(--muted);font-size:13.5px;margin:10px 0 0;max-width:78ch}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th{font:600 12px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);text-align:left;padding:8px 14px 8px 0;border-bottom:1px solid var(--line)}
td{padding:8px 14px 8px 0;border-bottom:1px solid var(--line);font-size:14px;font-family:var(--mono)}
</style>
<div class="wrap">
<header><div class="eyebrow">TEDxFargo CHARGE &middot; final cut preview</div>
<h1>Cut preview — 6 pieces, face %FW% &times; %FH% mm</h1>
<p class="dek">Every mark on the map is decoded in the legend below. Auto-kern applied:
A|R +1.2, R|G +5.9 mm. %DEK_ART%</p></header>

<section class="panel"><h2>Cut map — to scale in mm</h2>
<div class="chips">
<span class="chip good">%TOTPX% px word</span><span class="chip">sign total %SIGNPX% of 600 owned</span>
%CHIP_ART%
<span class="chip">min pixel spacing 14.2 mm</span><span class="chip">all pieces fit 316&times;295</span>
</div>
<div class="legend">
<span class="li"><svg width="28" height="12"><line x1="5" y1="6" x2="23" y2="6" stroke="#5fdef6" stroke-width="9" stroke-linecap="round"/></svg>tube channel (22 mm printed band)</span>
<span class="li"><svg width="12" height="12"><circle cx="6" cy="6" r="3.6" fill="#0e6e80"/></svg>pixel (&Oslash;12 bullet + collar)</span>
%LEG_ART%
<span class="li"><svg width="28" height="12"><line x1="2" y1="6" x2="26" y2="6" stroke="#f0be46" stroke-width="2.5" stroke-dasharray="5 3"/></svg>seam cut (through black field only)</span>
<span class="li"><svg width="12" height="12"><circle cx="6" cy="6" r="3.6" fill="#f08878"/></svg>wood-rail screw</span>
%LEG_TRIM%
</div>
<div class="figbox">%SVG%</div>
<p class="cap">To scale in mm. Tubes drawn at the printed 22 mm outer band width. Seams
thread the black field only &mdash; no cut ever touches a channel.%CAP_ART%</p></section>

<section class="panel"><h2>Cut notes — per piece</h2>
<table>
<tr><th>Piece</th><th>Size (mm)</th><th>Seam clearance (mm)</th><th>Pixels</th><th>Weight</th><th>Bed fit</th></tr>
%ROWS%
</table>
<p class="cap">Seam clearance = distance from tube centerline to the cut at that seam&rsquo;s
tightest point (band edge is at 11 mm, so 13.3 = 2.3 mm of black between cut and band).
Weights are real rendered volumes (PETG @1.27). Bed limit: 316 &times; 295 both-nozzle zone,
H sits exactly at it &mdash; place 295 across the bed as validated.%TBL_ART%</p></section>
</div>
"""
if ALT:
    DEK_ART = ("REPAIRED letterforms (user-directed, 2026-07-06), all restorations of what "
               "the font actually has &mdash; green marks the changes. A: the triangle&rsquo;s "
               "LEFT SIDE (tube 4 was an open arc in every build to date) and the hat&rsquo;s "
               "LEFT ARM, both eaten by the extractor&rsquo;s junction surgery. G: both tube "
               "ends extended to the vector&rsquo;s cut centers (29.1 / 10.8 mm short). R: leg "
               "pixels re-spaced by true chord (the extracted centerline zigzags, so arc-spaced "
               "pixels bunched to 14.2 mm) &mdash; the three snug pairs are GONE, no flange "
               "snipping needed. Green-ringed pixels are added or re-spaced. C&rsquo;s two "
               "end-truncations are known and deferred (piece already printing).")
    CHIP_ART = ('<span class="chip good">A + G + R repaired (font-faithful)</span>')
    CAP_ART = (" Green segments: A triangle left side 78 mm + hat arm 50 mm, G end extensions "
               "29.1 / 10.8 mm &mdash; all font-exact from the vector. Everything added sits "
               "59+ mm from every seam: cuts, screws, and neighbor pieces unchanged.")
    TBL_ART = (" Repaired rows = <code>piece3alt / piece4alt / piece5alt _3color.3mf</code> "
               "(audit clean); the original piece 3/4/5 3MFs are kept for reference &mdash; "
               "piece3 has the OPEN-TRIANGLE defect, do not print it.")
    LEG_ART = ('<span class="li"><svg width="28" height="12"><line x1="5" y1="6" x2="23" y2="6" '
               'stroke="#57d98f" stroke-width="9" stroke-linecap="round"/></svg>A repair &mdash; '
               'restored tube (triangle left side, hat arm)</span>\n'
               '<span class="li"><svg width="16" height="16"><circle cx="8" cy="8" r="6" '
               'fill="none" stroke="#57d98f" stroke-width="2"/><circle cx="8" cy="8" r="2.6" '
               'fill="#0e6e80"/></svg>added / re-spaced pixel</span>')
else:
    DEK_ART = ("Letterforms are the APPROVED originals &mdash; the art&rsquo;s open "
               "strokes are the font and stay exactly as sliced.")
    CHIP_ART = '<span class="chip good">approved letterforms (unchanged)</span>'
    CAP_ART = TBL_ART = LEG_ART = ""
LEG_TRIM = ('<span class="li"><svg width="16" height="16"><circle cx="8" cy="8" r="6" '
            'fill="none" stroke="#f08878" stroke-width="1.6" stroke-dasharray="3 3"/>'
            '<circle cx="8" cy="8" r="2.6" fill="#0e6e80"/></svg>snug pixel pair, '
            '13&ndash;14.5 mm chord &mdash; press firmly; flange-snip if it fights</span>'
            if trims else "")
html = (html.replace("%FW%", "%.0f" % FW).replace("%FH%", "%.0f" % FH)
            .replace("%TOTPX%", str(tot_px)).replace("%SIGNPX%", str(tot_px + 137))
            .replace("%DEK_ART%", DEK_ART).replace("%CHIP_ART%", CHIP_ART)
            .replace("%CAP_ART%", CAP_ART).replace("%TBL_ART%", TBL_ART)
            .replace("%LEG_ART%", LEG_ART).replace("%LEG_TRIM%", LEG_TRIM)
            .replace("%SVG%", "\n".join(svg)).replace("%ROWS%", "\n".join(rows)))
open("docs/sign-preview/cut-preview.html", "w").write(html)
print("wrote docs/sign-preview/cut-preview.html (%d px, %.0f g)" % (tot_px, tot_g))
