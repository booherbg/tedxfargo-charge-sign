#!/usr/bin/env python3
"""Regenerate docs/sign-preview/full-sign.html: full-sign composition (element-6
bolt board + CHARGE word, to scale) + board plate detail + production table.
Reads: src/parts/bolt_el6.json, src/parts/board_layout.scad,
       src/parts/word_cuts.json, src/parts/bolt_pixmap.json,
       stl/board_stats.txt (optional, from build_board.sh, for grams).
"""
import json, math, re, os

def grab(txt, key):
    return json.loads(re.search(key + r"\s*=\s*(.*?);", txt, re.S).group(1))

D = json.load(open("src/parts/bolt_el6.json"))
FW, FH = D["face"]
SY, SXT, SXB = D["seam_y"], D["seam_x_top"], D["seam_x_bot"]
C = D["c1"]
lay = open("src/parts/board_layout.scad").read()
bb_px = grab(lay, "bb_px")
bb_scr = grab(lay, "bb_scr")
bb_tie = grab(lay, "bb_tie")
plates = grab(lay, "bb_plates")
wc_all = json.load(open("src/parts/word_cuts.json"))
wp = wc_all["paths"]              # bridged + auto-kerned (continuous letters)
pixmap = json.load(open("src/parts/bolt_pixmap.json"))
n_yellow = len(C["yellow"])

GAP = 60.0
WORD_W, WORD_H = 1597.0, 295.0
word_x = FW + GAP
word_y = (FH - WORD_H) / 2          # word band centered on board height
total_w = word_x + WORD_W

stats = {}
if os.path.exists("stl/board_stats.txt"):
    for ln in open("stl/board_stats.txt"):
        m = re.match(r"\s*(board\d_\w+)\.stl\s+[\d.]+\s+cm3\s+([\d.]+)\s+g", ln)
        if m:
            stats[m.group(1)] = float(m.group(2))

def path_d(p, fy, ox=0.0, oy=0.0):
    return "M " + " L ".join("%.1f %.1f" % (q[0] + ox, fy(q[1] + oy)) for q in p)

def board_svg(px_r=3.2, detail=False):
    fy = lambda y: FH - y
    s = []
    s.append('<rect x="0" y="0" width="%.0f" height="%.0f" fill="#16191f"/>' % (FW, FH))
    if detail:
        for i, (x0, x1, y0, y1) in enumerate(plates):
            s.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                     'fill="none" stroke="#39424e" stroke-width="1.5"/>'
                     % (x0, fy(y1), x1 - x0, y1 - y0))
            s.append('<text x="%.1f" y="%.1f" fill="#5b6672" font-size="15" '
                     'font-family="ui-monospace,Menlo,monospace">B%d</text>'
                     % (x0 + 8, fy(y0) - 8, i + 1))
    else:
        for x0, y0, x1, y1 in ((0, SY, FW, SY),):
            s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                     'stroke="#4a5460" stroke-width="2" stroke-dasharray="6 5"/>'
                     % (x0, fy(SY), x1, fy(SY)))
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#4a5460" '
                 'stroke-width="2" stroke-dasharray="6 5"/>' % (SXT, fy(FH), SXT, fy(SY)))
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#4a5460" '
                 'stroke-width="2" stroke-dasharray="6 5"/>' % (SXB, fy(SY), SXB, fy(0)))
    for grp, col in (("yellow", "#e8c34a"), ("red", "#e04b3e")):
        for p in C[grp]:
            s.append('<path d="%s" fill="none" stroke="%s" stroke-width="22" '
                     'stroke-linecap="round" stroke-linejoin="round" opacity="0.92"/>'
                     % (path_d(p, fy), col))
    if detail:
        for p in C["yellow"] + C["red"]:
            s.append('<path d="%s" fill="none" stroke="#111" stroke-width="18" '
                     'stroke-linecap="round" stroke-linejoin="round" opacity="0.25"/>'
                     % (path_d(p, fy)))
        for p in pixmap["pixels"]:
            col = "#ffe98a" if p["color"] == "yellow" else "#ff9d8a"
            s.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>'
                     % (p["x"], fy(p["y"]), px_r, col))
        for x, y in bb_scr:
            s.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="none" '
                     'stroke="#8fa2b8" stroke-width="1.4"/>' % (x, fy(y)))
        for x, y in bb_tie:
            s.append('<circle cx="%.1f" cy="%.1f" r="1.8" fill="#4d5763"/>' % (x, fy(y)))
    return "\n".join(s)

def word_svg():
    fy = lambda y: FH - y
    oy = word_y + (WORD_H - 251.2) / 2      # center word band vertically in face
    s = ['<rect x="%.1f" y="%.1f" width="%.0f" height="%.0f" fill="#16191f"/>'
         % (word_x, fy(word_y + WORD_H), WORD_W, WORD_H)]
    wxs = [q[0] for p in wp for q in p]
    ox = word_x + (WORD_W - (max(wxs) - min(wxs))) / 2 - min(wxs)
    for p in wp:
        s.append('<path d="%s" fill="none" stroke="#57d7e6" stroke-width="22" '
                 'stroke-linecap="round" stroke-linejoin="round" opacity="0.92"/>'
                 % (path_d(p, fy, ox, oy)))
    return "\n".join(s)

board_px = len(pixmap["pixels"])
by_plate = [sum(1 for p in pixmap["pixels"] if p["plate"] == i) for i in (1, 2, 3, 4)]
red_px = sum(1 for p in pixmap["pixels"] if p["color"] == "red")
wc = json.load(open("src/parts/word_cuts.json"))
word_px = sum(p["pixels"] for p in wc["pieces"])   # authoritative: 454
grams_rows = []
for i in range(1, 5):
    g = [stats.get("board%d_%s" % (i, c)) for c in ("black", "white", "clear")]
    tot = sum(v for v in g if v)
    grams_rows.append((i, g, tot if all(v is not None for v in g) else None))

html = []
html.append('<title>CHARGE — full sign with element-6 bolt board</title>')
html.append('''<style>
:root{--bg:#14171c;--panel:#1a1e25;--line:#262c35;--text:#e6e9ed;--muted:#98a2ae;--bolt:#ff5f4f;--mono:ui-monospace,"SF Mono",Menlo,monospace}
body{background:var(--bg);color:var(--text);font:16px/1.55 -apple-system,"Helvetica Neue",Arial,sans-serif;margin:0;padding:40px 24px 72px}
.wrap{max-width:1280px;margin:0 auto;display:flex;flex-direction:column;gap:26px}
.eyebrow{font:600 12px/1 var(--mono);letter-spacing:.18em;text-transform:uppercase;color:var(--bolt)}
h1{font-size:29px;margin:10px 0 6px}.dek{color:var(--muted);max-width:72ch;margin:0}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:20px}
.panel h2{font-size:17px;margin:0 0 12px}
.figbox{overflow-x:auto}.figbox svg{display:block;min-width:1000px;width:100%;height:auto}
.duo{display:flex;gap:22px;align-items:flex-start;flex-wrap:wrap}.duo .b svg{height:600px;width:auto;display:block}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.chip{font:500 12.5px/1 var(--mono);color:var(--text);border:1px solid var(--line);border-radius:999px;padding:6px 11px}
.chip.good{color:#7fd99a;border-color:#2c4436}
.cap{color:var(--muted);font-size:13.5px;margin:10px 0 0;max-width:76ch}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th{font:600 12px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);text-align:left;padding:8px 14px 8px 0;border-bottom:1px solid var(--line)}
td{padding:8px 14px 8px 0;border-bottom:1px solid var(--line);font-size:14px;font-family:var(--mono)}
</style>''')
html.append('<div class="wrap">')
html.append('<header><div class="eyebrow">TEDxFargo CHARGE &middot; full sign</div>')
html.append('<h1>The sign, complete: element-6 bolt board + CHARGE</h1>')
html.append('<p class="dek">To scale in mm, production geometry. The board is the logo&rsquo;s'
            ' actual left panel: the flat-top bolt and X are ONE fused yellow outline'
            ' (element 6), with the billboard&rsquo;s red zigzag inside. Dashed = plate'
            ' seams (piecewise: each row splits at its own x). Word band centered on'
            ' board height &mdash; final hang alignment is a frame decision.</p></header>')
html.append('<section class="panel"><h2>Composition — as it hangs (&asymp;%.2f m wide)</h2>'
            % (total_w / 1000))
html.append('<div class="figbox"><svg viewBox="0 0 %.0f %.0f">' % (total_w, FH))
html.append(board_svg())
html.append(word_svg())
html.append('</svg></div>')
html.append('<p class="cap">Board %.0fx%.0f mm; word face %.0fx%.0f. The bolt panel '
            'stands %.1fx the letter cap height, matching the deployed logo proportion.'
            '</p></section>' % (FW, FH, WORD_W, WORD_H, (FH - 35) / 250))
html.append('<section class="panel"><h2>Bolt board detail — plates B1&ndash;B4, pixels, hardware</h2>')
html.append('<div class="chips"><span class="chip good">%d px board (%d yellow / %d red)</span>'
            '<span class="chip">B1/B2/B3/B4 = %d/%d/%d/%d px</span>'
            '<span class="chip">%d lens joints</span><span class="chip">tube %.0f mm</span>'
            '<span class="chip good">sign total %d px</span></div>'
            % (board_px, board_px - red_px, red_px, *by_plate,
               C["crossings"], C["tube"], word_px + board_px))
html.append('<div class="duo"><div class="b"><svg viewBox="-6 -6 %.0f %.0f">'
            % (FW + 12, FH + 12))
html.append(board_svg(detail=True))
html.append('</svg></div><div style="flex:1;min-width:340px">')
html.append('<table><tr><th>plate</th><th>size mm</th><th>px</th><th>black g</th>'
            '<th>white g</th><th>clear g</th><th>total g</th></tr>')
for i, (x0, x1, y0, y1) in enumerate(plates):
    g = grams_rows[i][1]
    fmt_g = lambda v: ("%.0f" % v) if v else "&mdash;"
    tot = grams_rows[i][2]
    html.append('<tr><td>B%d</td><td>%.0fx%.0f</td><td>%d</td><td>%s</td><td>%s</td>'
                '<td>%s</td><td>%s</td></tr>'
                % (i + 1, x1 - x0, y1 - y0, by_plate[i], fmt_g(g[0]), fmt_g(g[1]),
                   fmt_g(g[2]), ("%.0f" % tot) if tot else "&mdash;"))
html.append('</table>')
html.append('<p class="cap">All plates fit the validated 316x295 both-nozzle zone. '
            'CONTINUOUS MODE: the outline is one bridged loop and channels cross the plate '
            'joints (hairline lens joint at each crossing; one global fuzz field keeps the '
            'texture continuous). Pixels and collars are kept &ge;12.5 mm off the seams. '
            'Pixels relax to a 14.5 mm flange floor; snug pairs 13&ndash;14.5 seat with a '
            'flange snip. <b>bolt_pixmap.json</b> carries every pixel&rsquo;s color zone, '
            'plate, and chain position for the controller.</p>')
html.append('</div></div></section>')
html.append('<section class="panel"><h2>Pixels &amp; power</h2><p class="cap" style="margin-top:0">'
            'Board: %d px @22 mm. Sign total <b>%d px</b> vs the ~600 bullets OWNED (the hard '
            'inventory cap &mdash; pitch was set to respect it). Power coincidentally lands at the '
            '150 W PSU&rsquo;s full-white edge too: cap brightness ~80%% or add a second PSU. '
            'Colors-only scenes draw far less than full white.'
            '</p></section>' % (board_px, word_px + board_px))
html.append('</div>')
open("docs/sign-preview/full-sign.html", "w").write("\n".join(html))
print("wrote docs/sign-preview/full-sign.html (%d px board, %d total)"
      % (board_px, word_px + board_px))
