#!/usr/bin/env python3
"""Combined cut preview for the FULL SIGN (bolt board + CHARGE) —
docs/sign-preview/sign-cut-preview.html. Cut-preview visual language:
amber dashed = seams/plate joints, red dots = screws, pixel dots in-tube.
Reads word_cuts.json, bolt_el6.json, board_layout.scad, bolt_pixmap.json,
stl/piece_stats.txt + stl/board_stats.txt.
"""
import json, os, re

def grab(txt, key):
    return json.loads(re.search(key + r"\s*=\s*(.*?);", txt, re.S).group(1))

# ---- inputs ----
wc = json.load(open("src/parts/word_cuts.json"))
D = json.load(open("src/parts/bolt_el6.json"))
FW, FH = D["face"]
C = D["c1"]
lay = open("src/parts/board_layout.scad").read()
plates = grab(lay, "bb_plates")
bb_scr = grab(lay, "bb_scr")
pixmap = json.load(open("src/parts/bolt_pixmap.json"))

def load_stats(path, prefix):
    out = {}
    if os.path.exists(path):
        for ln in open(path):
            m = re.match(r"\s*(%s\d)_(\w+)\.stl\s+[\d.]+\s+cm3\s+([\d.]+)\s+g" % prefix, ln)
            if m:
                out.setdefault(m.group(1), {})[m.group(2)] = float(m.group(3))
    return out
pstats = load_stats("stl/piece_stats.txt", "piece")
bstats = load_stats("stl/board_stats.txt", "board")

GAP = 60.0
WORD_W, WORD_H = 1597.0, 295.0
word_x = FW + GAP
word_y = (FH - WORD_H) / 2
TOTW = word_x + WORD_W
fy = lambda y: FH - y

wpaths, wcuts, wpieces, wpx = wc["paths"], wc["cuts"], wc["pieces"], wc["pixels"]
wxs = [q[0] for p in wpaths for q in p]
ox = word_x + (WORD_W - (max(wxs) - min(wxs))) / 2 - min(wxs)
oy = word_y + (WORD_H - 251.2) / 2

def pd(p, o_x=0.0, o_y=0.0):
    return "M " + " L ".join("%.1f %.1f" % (q[0] + o_x, fy(q[1] + o_y)) for q in p)

svg = ['<svg viewBox="-6 -6 %.0f %.0f">' % (TOTW + 12, FH + 12)]
# faces
svg.append('<rect x="0" y="0" width="%.0f" height="%.0f" fill="#16191f"/>' % (FW, FH))
svg.append('<rect x="%.1f" y="%.1f" width="%.0f" height="%.0f" fill="#16191f"/>'
           % (word_x, fy(word_y + WORD_H), WORD_W, WORD_H))
# board plate joints (piecewise, amber dashed) + plate outlines
SY, SXT, SXB = D["seam_y"], D["seam_x_top"], D["seam_x_bot"]
for x1, y1, x2, y2 in ((0, SY, FW, SY), (SXT, SY, SXT, FH), (SXB, 0, SXB, SY)):
    svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#f0be46" '
               'stroke-width="2.5" stroke-dasharray="7 5"/>' % (x1, fy(y1), x2, fy(y2)))
# board tubes + pixels + screws
for grp, col, dot in (("yellow", "#e8c34a", "#7a6215"), ("red", "#e04b3e", "#6e1a12")):
    for p in C[grp]:
        svg.append('<path d="%s" fill="none" stroke="%s" stroke-width="22" '
                   'stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>'
                   % (pd(p), col))
for q in pixmap["pixels"]:
    dot = "#7a6215" if q["color"] == "yellow" else "#6e1a12"
    svg.append('<circle cx="%.1f" cy="%.1f" r="3.2" fill="%s"/>' % (q["x"], fy(q["y"]), dot))
for x, y in bb_scr:
    svg.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="#f08878"/>' % (x, fy(y)))
for i, (px0, px1, py0, py1) in enumerate(plates):
    svg.append('<text x="%.1f" y="%.1f" fill="#98a2ae" font-size="17" '
               'font-family="ui-monospace,Menlo,monospace">B%d</text>'
               % (px0 + 8, fy(py0) - 8, i + 1))
# word tubes + cuts + pixels + screws + numbers
for p in wpaths:
    svg.append('<path d="%s" fill="none" stroke="#5fdef6" stroke-width="22" '
               'stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>'
               % (pd(p, ox, oy)))
for c in wcuts:
    svg.append('<path d="%s" fill="none" stroke="#f0be46" stroke-width="2.5" '
               'stroke-dasharray="7 5"/>' % (pd(c, ox, oy)))
for q in wpx:
    svg.append('<circle cx="%.1f" cy="%.1f" r="3.2" fill="#0e6e80"/>'
               % (q[0] + ox, fy(q[1] + oy)))
for pc in wpieces:
    for s in pc["screws"]:
        svg.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="#f08878"/>'
                   % (s[0] + ox, fy(s[1] + oy)))
    svg.append('<text x="%.1f" y="%.1f" fill="#98a2ae" font-size="17" '
               'font-family="ui-monospace,Menlo,monospace">%d</text>'
               % ((pc["x0"] + pc["x1"]) / 2 + ox - 5, fy(word_y) - 8,
                  wpieces.index(pc) + 1))
svg.append("</svg>")

def _g(st, k):
    return ("%.0f" % st[k]) if k in st else "&mdash;"
def wrow(i, pc):
    st = pstats.get("piece%d" % (i + 1), {})
    tot = sum(st.values()) if st else None
    return ("<tr><td>%d — %s</td><td>%.0f × %.0f</td><td>%d</td>"
            "<td>%s</td><td>%s</td><td>%s</td><td><b>%s</b></td><td>%s</td></tr>"
            % (i + 1, pc["letter"], pc["w"], pc["h"], pc["pixels"],
               _g(st, "black"), _g(st, "white"), _g(st, "clear"),
               ("%.0f" % tot) if tot else "&mdash;", "✓" if pc["fits"] else "✗"))
def brow(i):
    x0, x1, y0, y1 = plates[i]
    st = bstats.get("board%d" % (i + 1), {})
    tot = sum(st.values()) if st else None
    n = sum(1 for q in pixmap["pixels"] if q["plate"] == i + 1)
    return ("<tr><td>B%d</td><td>%.0f × %.0f</td><td>%d</td>"
            "<td>%s</td><td>%s</td><td>%s</td><td><b>%s</b></td><td>✓</td></tr>"
            % (i + 1, x1 - x0, y1 - y0, n,
               _g(st, "black"), _g(st, "white"), _g(st, "clear"),
               ("%.0f" % tot) if tot else "&mdash;"))
def totals_row(stats, label, npx):
    cols = {k: sum(v.get(k, 0) for v in stats.values()) for k in ("black", "white", "clear")}
    tot = sum(cols.values())
    return ("<tr><td><b>%s</b></td><td></td><td><b>%d</b></td><td><b>%.0f</b></td>"
            "<td><b>%.0f</b></td><td><b>%.0f</b></td><td><b>%.0f g</b></td><td></td></tr>"
            % (label, npx, cols["black"], cols["white"], cols["clear"], tot))

word_px_n = sum(pc["pixels"] for pc in wpieces)
board_px_n = len(pixmap["pixels"])
wg = sum(sum(v.values()) for v in pstats.values())
bg = sum(sum(v.values()) for v in bstats.values())

html = """<title>CHARGE + bolt — full sign cut preview</title>
<style>
:root{--bg:#14171c;--panel:#1a1e25;--line:#262c35;--text:#e6e9ed;--muted:#98a2ae;--bolt:#ff5f4f;--mono:ui-monospace,"SF Mono",Menlo,monospace}
body{background:var(--bg);color:var(--text);font:16px/1.55 -apple-system,"Helvetica Neue",Arial,sans-serif;margin:0;padding:40px 24px 72px}
.wrap{max-width:1280px;margin:0 auto;display:flex;flex-direction:column;gap:26px}
.eyebrow{font:600 12px/1 var(--mono);letter-spacing:.18em;text-transform:uppercase;color:var(--bolt)}
h1{font-size:29px;margin:10px 0 6px}.dek{color:var(--muted);max-width:76ch;margin:0}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:20px}
.panel h2{font-size:17px;margin:0 0 12px}
.figbox{overflow-x:auto}.figbox svg{display:block;min-width:1200px;width:100%;height:auto}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.chip{font:500 12.5px/1 var(--mono);color:var(--text);border:1px solid var(--line);border-radius:999px;padding:6px 11px}
.chip.good{color:#7fd99a;border-color:#2c4436}
.cap{color:var(--muted);font-size:13.5px;margin:10px 0 0;max-width:78ch}
.duo{display:flex;gap:26px;flex-wrap:wrap}.duo>div{flex:1;min-width:340px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th{font:600 12px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);text-align:left;padding:8px 14px 8px 0;border-bottom:1px solid var(--line)}
td{padding:8px 14px 8px 0;border-bottom:1px solid var(--line);font-size:14px;font-family:var(--mono)}
</style>
<div class="wrap">
<header><div class="eyebrow">TEDxFargo CHARGE &middot; full sign cut preview</div>
<h1>Bolt board + CHARGE — every piece, every cut</h1>
<p class="dek">To scale in mm (&asymp;2.07 m wide as hung). Amber dashed = cuts and plate
joints. Red dots = wood-rail screws. Word seams thread the black field only (never a tube);
the board&rsquo;s channels CROSS its plate joints by design (continuous neon, 7 hairline lens
joints). CHARGE is the approved original &mdash; open strokes are the font. Word band centered
on board height; final hang alignment is a frame decision.</p></header>

<section class="panel"><h2>Cut map — 10 printed pieces</h2>
<div class="chips">
<span class="chip good">word %WPX% px</span><span class="chip good">board %BPX% px</span>
<span class="chip">sign %TOTPX% of 600 owned</span>
<span class="chip">word %WG% g &middot; board %BG% g</span>
<span class="chip good">all pieces fit 316&times;295</span>
</div>
<div class="figbox">%SVG%</div>
<p class="cap">Board pixel dots are colored by zone (yellow outline / red inner &mdash; one
137-px data chain in practice, zones are software). Word pixels @17 mm, board @20 mm.</p></section>

<section class="panel"><h2>Piece notes</h2>
<div class="duo">
<div><h2 style="font-size:14px;color:#98a2ae">CHARGE — 6 pieces (PETG grams)</h2>
<table><tr><th>Piece</th><th>Size (mm)</th><th>Px</th><th>Black</th><th>White</th><th>Clear</th><th>Total</th><th>Bed</th></tr>
%WROWS%</table></div>
<div><h2 style="font-size:14px;color:#98a2ae">Bolt board — 4 plates (PETG grams)</h2>
<table><tr><th>Plate</th><th>Size (mm)</th><th>Px</th><th>Black</th><th>White</th><th>Clear</th><th>Total</th><th>Bed</th></tr>
%BROWS%</table>
<p class="cap">Plate joints: y=255 full width; top row splits at x=126, bottom at x=153.
Butt plates snug &mdash; the shared fuzz field makes the lens texture continuous across
joints. Extension jumpers at chain 87 and 108.</p></div>
</div></section>

<section class="panel"><h2>Grand totals — filament &amp; power</h2>
<table style="max-width:760px">
<tr><th></th><th>Pixels</th><th>Black</th><th>White</th><th>Clear</th><th>Total PETG</th></tr>
%GRAND%
</table>
<p class="cap">Power at 0.25 W/pixel: <b>%W100% W @ 100%</b> brightness &middot;
<b>%W66% W @ 66%</b>. The 150 W/24 V PSU covers 66% with ~35% headroom; 100% full-white
sits right at its nameplate &mdash; cap brightness or add the second PSU for sustained
full-white. Colors-only scenes draw well under these figures.</p></section>
</div>
"""
tot_px = word_px_n + board_px_n
def col_sum(stats, k):
    return sum(v.get(k, 0) for v in stats.values())
grand = []
grand.append(totals_row(pstats, "CHARGE", word_px_n))
grand.append(totals_row(bstats, "Bolt board", board_px_n))
gb = col_sum(pstats, "black") + col_sum(bstats, "black")
gw = col_sum(pstats, "white") + col_sum(bstats, "white")
gc = col_sum(pstats, "clear") + col_sum(bstats, "clear")
grand.append("<tr><td><b>SIGN</b></td><td><b>%d</b></td><td><b>%.0f</b></td>"
             "<td><b>%.0f</b></td><td><b>%.0f</b></td><td><b>%.0f g</b></td></tr>"
             % (tot_px, gb, gw, gc, gb + gw + gc))
# grand table has no Size/Bed columns: strip them from totals_row output
grand = [g.replace("<td></td><td><b>", "<td><b>", 1).replace("</b></td><td></td></tr>", "</b></td></tr>", 1)
         for g in grand]

html = (html.replace("%SVG%", "\n".join(svg))
            .replace("%WROWS%", "\n".join([wrow(i, pc) for i, pc in enumerate(wpieces)]
                                           + [totals_row(pstats, "total", word_px_n)]))
            .replace("%BROWS%", "\n".join([brow(i) for i in range(4)]
                                           + [totals_row(bstats, "total", board_px_n)]))
            .replace("%GRAND%", "\n".join(grand))
            .replace("%W100%", "%.0f" % (tot_px * 0.25))
            .replace("%W66%", "%.0f" % (tot_px * 0.25 * 0.66))
            .replace("%WPX%", str(word_px_n)).replace("%BPX%", str(board_px_n))
            .replace("%TOTPX%", str(tot_px))
            .replace("%WG%", "%.0f" % wg).replace("%BG%", "%.0f" % bg))
open("docs/sign-preview/sign-cut-preview.html", "w").write(html)
print("wrote docs/sign-preview/sign-cut-preview.html (%d + %d = %d px)"
      % (word_px_n, board_px_n, word_px_n + board_px_n))
