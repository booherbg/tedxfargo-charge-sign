#!/usr/bin/env python3
"""Generate docs/sign-preview/system-preview.html — the ENTIRE sign system:
lit full-sign composition to scale (CHARGE word + bolt board), annotated
system map (pieces, cuts, plates, straps, screws, wood-frame concept),
production inventory, power/wiring, status.
Reads: word_cuts_repairs.json (459-px printed truth; falls back to
word_cuts.json), bolt_el6.json, board_layout.scad, bracket_layout.scad,
bolt_pixmap.json, board_qa.json, stl/board_stats.txt (optional).
"""
import json, math, os, re

def grab(txt, key):
    return json.loads(re.search(key + r"\s*=\s*(\[.*?\]);", txt, re.S).group(1))

# ---- load board ----
D = json.load(open("src/parts/bolt_el6.json"))
FW, FH = D["face"]
SY, SXT, SXB = D["seam_y"], D["seam_x_top"], D["seam_x_bot"]
bpaths = [[tuple(q) for q in p] for p in D["c1"]["yellow"]] + \
         [[tuple(q) for q in p] for p in D["c1"]["red"]]
lay = open("src/parts/board_layout.scad").read()
plates = grab(lay, "bb_plates")
bscr = grab(lay, "bb_scr")
bk = open("src/parts/bracket_layout.scad").read()
bk_w = float(re.search(r"bk_strap_w = ([\d.]+);", bk).group(1))
bk_span = grab(bk, "bk_span")
STRAP_AX = [(1, SY), (1, SY), (0, SXT), (0, SXB)]
pixmap = json.load(open("src/parts/bolt_pixmap.json"))
bpx = [(p["x"], p["y"], p["color"]) for p in pixmap["pixels"]]

# ---- load word (printed truth = repairs file) ----
wf = "src/parts/word_cuts_repairs.json"
if not os.path.exists(wf):
    wf = "src/parts/word_cuts.json"
W = json.load(open(wf))
wx0, wy0, wx1, wy1 = W["face"]
WORD_W, WORD_H = wx1 - wx0, W["face_h"]
wband = W.get("band_out", 22.0)
GAP = 60.0
word_ox = FW + GAP - wx0            # word-local -> composition
word_oy = (FH - WORD_H) / 2 - wy0
TOT_W = FW + GAP + WORD_W

qa = None
if os.path.exists("src/parts/board_qa.json"):
    qa = json.load(open("src/parts/board_qa.json"))
stats = {}
if os.path.exists("stl/board_stats.txt"):
    for ln in open("stl/board_stats.txt"):
        m = re.match(r"\s*(\S+)\.stl\s+[\d.]+\s+cm3\s+([\d.]+)\s+g", ln)
        if m:
            stats[m.group(1)] = float(m.group(2))

def fy(y): return FH - y
def pd(p, ox=0.0, oy=0.0):
    return "M " + " L ".join("%.1f %.1f" % (q[0]+ox, fy(q[1]+oy)) for q in p)

WORD_GLOW, WORD_CORE = "#9fd8ff", "#eef9ff"
BCOL = {"yellow": "#ffc93c", "red": "#ff5340"}

def hero_svg():
    s = ['<svg viewBox="-12 -12 %d %d" xmlns="http://www.w3.org/2000/svg">'
         % (TOT_W + 24, FH + 24)]
    s.append('<defs><filter id="ghero" x="-150%" y="-150%" width="400%" height="400%">'
             '<feGaussianBlur stdDeviation="7"/></filter></defs>')
    s.append('<rect x="-12" y="-12" width="%d" height="%d" rx="8" fill="#0b0d10"/>'
             % (TOT_W + 24, FH + 24))
    for p in bpaths:
        s.append('<path d="%s" fill="none" stroke="#20242b" stroke-width="22" '
                 'stroke-linecap="round" stroke-linejoin="round"/>' % pd(p))
    for p in W["paths"]:
        s.append('<path d="%s" fill="none" stroke="#20242b" stroke-width="%.0f" '
                 'stroke-linecap="round" stroke-linejoin="round"/>'
                 % (pd(p, word_ox, word_oy), wband))
    for x, y, col in bpx:
        s.append('<circle cx="%.1f" cy="%.1f" r="8.5" fill="%s" opacity="0.85" '
                 'filter="url(#ghero)"/>' % (x, fy(y), BCOL[col]))
    for x, y in W["pixels"]:
        s.append('<circle cx="%.1f" cy="%.1f" r="8" fill="%s" opacity="0.8" '
                 'filter="url(#ghero)"/>' % (x + word_ox, fy(y + word_oy), WORD_GLOW))
    for p in bpaths:
        s.append('<path d="%s" fill="none" stroke="#fff" stroke-opacity="0.05" '
                 'stroke-width="19" stroke-linecap="round" stroke-linejoin="round"/>' % pd(p))
    for p in W["paths"]:
        s.append('<path d="%s" fill="none" stroke="#fff" stroke-opacity="0.06" '
                 'stroke-width="%.0f" stroke-linecap="round" stroke-linejoin="round"/>'
                 % (pd(p, word_ox, word_oy), wband - 3))
    for x, y, col in bpx:
        s.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="#fff" opacity="0.95"/>'
                 % (x, fy(y)))
    for x, y in W["pixels"]:
        s.append('<circle cx="%.1f" cy="%.1f" r="2.4" fill="%s" opacity="0.95"/>'
                 % (x + word_ox, fy(y + word_oy), WORD_CORE))
    s.append('</svg>')
    return "\n".join(s)

def map_svg():
    s = ['<svg viewBox="-12 -46 %d %d" xmlns="http://www.w3.org/2000/svg">'
         % (TOT_W + 24, FH + 92)]
    s.append('<rect x="-12" y="-46" width="%d" height="%d" rx="8" fill="#101318"/>'
             % (TOT_W + 24, FH + 92))
    # wood-frame concept (behind everything)
    wood = []
    scr_rows = sorted(set(round(q[1], 1) for pc in W["pieces"] for q in pc["screws"]))
    lo_row, hi_row = scr_rows[0], scr_rows[-1]
    wood.append((FW + GAP - 20, fy(lo_row + word_oy) - 19, WORD_W + 40, 38))   # word bottom rail
    wood.append((FW + GAP - 20, fy(hi_row + word_oy) - 19, WORD_W + 40, 38))   # word top rail
    wood.append((-8, fy(6) - 19, FW + 16, 38))                                 # board bottom
    wood.append((-8, fy(FH - 6) - 19, FW + 16, 38))                            # board top
    wood.append((-8 - 19, fy(FH) - 8, 38, FH + 16))                            # board L stile
    wood.append((FW + GAP/2 - 19, fy(FH) - 8, 38, FH + 16))                    # shared stile
    wood.append((TOT_W - 19, fy(hi_row + word_oy),
                 38, fy(lo_row + word_oy) - fy(hi_row + word_oy)))             # word R stile
    for x, y, w, h in wood:
        s.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="4" '
                 'fill="#8a6a45" fill-opacity="0.22" stroke="#8a6a45" '
                 'stroke-opacity="0.5" stroke-width="1.2"/>' % (x, y, w, h))
    # word pieces + cuts + tubes + screws
    for i, pc in enumerate(W["pieces"]):
        cx = (pc["x0"] + pc["x1"]) / 2 + word_ox
        s.append('<text x="%.1f" y="%.1f" fill="#57616e" font-size="20" font-weight="700" '
                 'text-anchor="middle" font-family="ui-monospace,Menlo,monospace">'
                 '%d·%s</text>' % (cx, fy(WORD_H + wy0 + word_oy) - 16, i + 1, pc["letter"]))
    for p in W["paths"]:
        s.append('<path d="%s" fill="none" stroke="#2c333d" stroke-width="%.0f" '
                 'stroke-linecap="round" stroke-linejoin="round"/>'
                 % (pd(p, word_ox, word_oy), wband))
    for c in W["cuts"]:
        s.append('<path d="%s" fill="none" stroke="#5b8dbb" stroke-width="2" '
                 'stroke-dasharray="7 5"/>' % pd(c, word_ox, word_oy))
    for x, y in W["pixels"]:
        s.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="%s" opacity="0.6"/>'
                 % (x + word_ox, fy(y + word_oy), WORD_GLOW))
    for pc in W["pieces"]:
        for q in pc["screws"]:
            s.append('<rect x="%.1f" y="%.1f" width="7" height="7" fill="#707a87"/>'
                     % (q[0] + word_ox - 3.5, fy(q[1] + word_oy) - 3.5))
    # board plates, tubes, straps, screws
    for i, (x0, x1, y0, y1) in enumerate(plates):
        s.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#171b21" '
                 'stroke="#333b46" stroke-width="1.4"/>' % (x0, fy(y1), x1-x0, y1-y0))
        s.append('<text x="%.1f" y="%.1f" fill="#57616e" font-size="17" font-weight="700" '
                 'font-family="ui-monospace,Menlo,monospace">B%d</text>'
                 % (x0 + 10, fy(y0) - 10, i + 1))
    for p in bpaths:
        s.append('<path d="%s" fill="none" stroke="#2c333d" stroke-width="22" '
                 'stroke-linecap="round" stroke-linejoin="round"/>' % pd(p))
    for x, y, col in bpx:
        s.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s" opacity="0.65"/>'
                 % (x, fy(y), BCOL[col]))
    for i, (axis, coord) in enumerate(STRAP_AX):
        u0, u1 = bk_span[i]
        rect = (u0, fy(coord + bk_w/2), u1 - u0, bk_w) if axis == 1 \
               else (coord - bk_w/2, fy(u1), bk_w, u1 - u0)
        s.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="5" '
                 'fill="#e9e5db" fill-opacity="0.13" stroke="#e9e5db" '
                 'stroke-opacity="0.5" stroke-width="1.5"/>' % rect)
    for q in bscr:
        if q[2] == 1:
            s.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="#ffc93c"/>' % (q[0], fy(q[1])))
        else:
            s.append('<rect x="%.1f" y="%.1f" width="7" height="7" fill="#707a87"/>'
                     % (q[0] - 3.5, fy(q[1]) - 3.5))
    s.append('</svg>')
    return "\n".join(s)

# ---- tables ----
plate_px = {}
for p in pixmap["pixels"]:
    plate_px[p["plate"]] = plate_px.get(p["plate"], 0) + 1
inv = []
for i, pc in enumerate(W["pieces"]):
    alt = " (repaired)" if pc["letter"] in ("A", "R", "G") else ""
    inv.append((("%d · %s%s") % (i+1, pc["letter"], alt),
                "%.0f × 295" % (pc["x1"] - pc["x0"]), "~%d g" % pc["grams"],
                str(pc["pixels"]), "PRINTED ✓"))
for k in (1, 2, 3, 4):
    g = sum(stats.get("board%d_%s" % (k, c), 0) for c in ("black", "white", "clear"))
    x0, x1, y0, y1 = plates[k-1]
    inv.append(("board B%d" % k, "%.0f × %.0f" % (x1-x0, y1-y0),
                "%.0f g" % g if g else "—", str(plate_px.get(k, 0)), "ready to slice"))
for k in (1, 2, 3, 4):
    g = stats.get("strap_s%d" % k, 0)
    L = bk_span[k-1][1] - bk_span[k-1][0]
    inv.append(("strap S%d (white)" % k, "%.0f × 48" % L,
                "%.0f g" % g if g else "—", "—", "ready to print"))
inv.append(("pixel pusher", "Ø14 × 60", "%.0f g" % stats.get("pusher", 6), "—",
            "ready to print"))
inv_rows = "\n".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                     % r for r in inv)
word_px = len(W["pixels"])
total_px = word_px + len(bpx)
word_g = sum(pc["grams"] for pc in W["pieces"])
board_g = sum(stats.get("board%d_%s" % (k, c), 0) for k in (1,2,3,4)
              for c in ("black", "white", "clear"))
strap_g = sum(stats.get("strap_s%d" % k, 0) for k in (1,2,3,4))
n_mach = sum(1 for s in bscr if s[2] == 1)
n_wood_b = sum(1 for s in bscr if s[2] == 0)
n_wood_w = sum(len(pc["screws"]) for pc in W["pieces"])
qa_line = ""
if qa:
    n_ok = sum(1 for c in qa["checks"] if c["ok"])
    qa_line = ('<div class="stat"><b class="ok">%d/%d</b><span>QA checks pass</span></div>'
               % (n_ok, len(qa["checks"])))

html = """<title>CHARGE sign — full system</title>
<style>
:root {
  --bg:#14161a; --panel:#1d222a; --panel2:#171b21; --line:#2c333d;
  --ink:#e9e5db; --mut:#8b94a1; --yel:#ffc93c; --red:#ff5340; --ok:#7ad48a;
  --cyan:#9fd8ff; --wood:#b08a5e;
}
html { background:var(--bg); }
body { margin:0; color:var(--ink); background:var(--bg);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.wrap { max-width:1120px; margin:0 auto; padding:36px 22px 80px; }
h1,h2,.stat b,.tag,th,.cap { font-family:ui-monospace,Menlo,Consolas,monospace; }
h1 { font-size:26px; letter-spacing:.02em; margin:0 0 4px; text-wrap:balance; }
h2 { font-size:15px; letter-spacing:.14em; text-transform:uppercase; color:var(--yel);
     margin:52px 0 14px; }
h2:after { content:""; display:block; height:1px; background:var(--line); margin-top:8px; }
.sub { color:var(--mut); margin:0 0 22px; max-width:70ch; }
.stats { display:flex; flex-wrap:wrap; gap:10px; margin:20px 0 6px; }
.stat { background:var(--panel); border:1px solid var(--line); border-radius:8px;
  padding:10px 16px; }
.stat b { display:block; font-size:21px; font-variant-numeric:tabular-nums; }
.stat span { color:var(--mut); font-size:12.5px; letter-spacing:.05em; text-transform:uppercase; }
.wide svg { width:100%; height:auto; display:block; border-radius:10px; }
.cap { font-size:12.5px; color:var(--mut); letter-spacing:.06em;
  text-transform:uppercase; margin:8px 0 0; }
.legend { display:flex; flex-wrap:wrap; gap:12px 24px; background:var(--panel);
  border:1px solid var(--line); border-radius:10px; padding:13px 18px; margin-top:14px;
  font-size:13.5px; color:var(--mut); }
.legend .it { display:flex; align-items:center; gap:8px; }
.legend svg { width:22px; height:22px; flex:none; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th { text-align:left; color:var(--mut); font-size:12px; letter-spacing:.1em;
  text-transform:uppercase; font-weight:600; padding:8px 14px 8px 0; }
td { padding:7px 14px 7px 0; border-top:1px solid var(--line);
  font-variant-numeric:tabular-nums; }
.ok { color:var(--ok); } .warn { color:var(--red); }
ol { margin:0; padding-left:22px; }
li { margin:7px 0; }
li::marker { color:var(--yel); font-family:ui-monospace,Menlo,monospace; font-weight:700; }
.note { background:var(--panel); border:1px solid var(--line);
  border-left:3px solid var(--yel); border-radius:8px; padding:12px 16px;
  color:var(--mut); font-size:14px; margin-top:16px; }
a { color:var(--cyan); }
</style>
<div class="wrap">
<h1>CHARGE — FULL SIGN SYSTEM</h1>
<p class="sub">TEDxFargo CHARGE 2026, 3D-printed and LED-lit: the 1.6&nbsp;m CHARGE word
(6 pieces, printed and working) + the 410×550 bolt board (4 plates + seam straps, ready
to print) on one wood frame. Everything to scale below; sign overall ≈
<b>{{TOTW}} × 550 mm</b>.</p>
<div class="stats">
  <div class="stat"><b>{{TOTPX}}/600</b><span>pixels ({{WORDPX}} word + {{BOARDPX}} board)</span></div>
  <div class="stat"><b>~{{KG}} kg</b><span>printed PETG</span></div>
  <div class="stat"><b>{{NWW}}+{{NWB}}</b><span>wood screws (word + board)</span></div>
  <div class="stat"><b>{{NM}}</b><span>M4 → strap nuts</span></div>
  {{QALINE}}
</div>

<h2>The sign, lit</h2>
<div class="wide">{{HERO}}</div>
<p class="cap">to scale — word band centered on the board's 550&nbsp;mm height, 60&nbsp;mm gap.
word = cool white zone, bolt = yellow + red zones (all addressable; colors are software).</p>

<h2>System map — pieces, plates, straps, frame</h2>
<div class="wide">{{MAP}}</div>
<div class="legend">
  <div class="it"><svg viewBox="0 0 22 22"><rect x="2" y="7" width="18" height="8" rx="2" fill="#8a6a45" fill-opacity="0.3" stroke="#8a6a45"/></svg> wood frame concept (rails + stiles, 50–75&nbsp;mm plenum, thin back skin)</div>
  <div class="it"><svg viewBox="0 0 22 22"><rect x="2" y="6" width="18" height="10" rx="3" fill="#e9e5db" fill-opacity="0.13" stroke="#e9e5db" stroke-opacity="0.5"/></svg> seam strap (behind plates)</div>
  <div class="it"><svg viewBox="0 0 22 22"><path d="M4 18 L18 4" stroke="#5b8dbb" stroke-width="2" stroke-dasharray="5 4" fill="none"/></svg> word corridor cut</div>
  <div class="it"><svg viewBox="0 0 22 22"><rect x="7" y="7" width="8" height="8" fill="#707a87"/></svg> wood screw (frame mount)</div>
  <div class="it"><svg viewBox="0 0 22 22"><circle cx="11" cy="11" r="4" fill="#ffc93c"/></svg> M4 → captive strap nut</div>
  <div class="it"><svg viewBox="0 0 22 22"><circle cx="11" cy="11" r="3" fill="#9fd8ff"/></svg> pixel</div>
</div>
<div class="note">Frame per <code>docs/assembly-charge.md</code>: word zone = top + bottom
rails catching each piece's 6 screws; board zone = perimeter only (no y-seam rail — the
straps replaced it); shared stiles at the 60&nbsp;mm gap; PSU/controller on a side board.
Rail positions here are the concept sketch — final lumber layout is yours.</div>

<h2>Production inventory</h2>
<div style="overflow-x:auto"><table>
<tr><th>part</th><th>footprint (mm)</th><th>mass</th><th>pixels</th><th>status</th></tr>
{{INV}}
</table></div>

<h2>Power &amp; wiring</h2>
<ol>
<li><b>{{TOTPX}} of exactly 600 owned pixels</b> ({{SPARE}} spare — the unused tail of the
last string stays attached, tucked in the plenum).</li>
<li>Word: chained per letter in path order, jumper slack across piece seams.
Board: ONE 137-px chain per <code>bolt_pixmap.json</code> — extension jumpers at links
86 and 107; the two <code>mount:&nbsp;bracket</code> pixels seat through the strap collars.</li>
<li>4-inch strings → ~85&nbsp;mm slack folds per node; wires route behind the seam straps
(brackets-first assembly), loose in the plenum.</li>
<li>Power: {{TOTPX}} px ≈ the 150&nbsp;W/24&nbsp;V PSU's full-white edge → cap brightness
~80% or add a second PSU; color scenes draw far less.</li>
</ol>

<h2>Status</h2>
<ol>
<li><span class="ok">DONE</span> — word pieces 1–6 printed and working (A/R/G are the
repaired versions: closed triangle, hat arm, G-end extensions, R re-spacing).</li>
<li><span class="ok">DONE</span> — board plates B1–B4 + 4 seam straps + pusher generated,
mesh-audited (0 bad edges), QA {{QAOK}} — see the
<a href="https://claude.ai/code/artifact/758534c5-1e14-42fa-afa7-ca9a555f5aa3">bolt
seam-bracket deep dive</a>.</li>
<li><b>NEXT</b> — slice &amp; print the board plates (same 0.20 process/filament layout as
the word) and the white straps; grab {{NM}}× M4×8 + nuts; build the frame
(perimeter rails/stiles per the map above).</li>
</ol>
</div>
"""
n_ok_s = ("%d/%d" % (sum(1 for c in qa["checks"] if c["ok"]), len(qa["checks"]))) if qa else "—"
for k, v in {
    "{{TOTW}}": "%.0f" % TOT_W, "{{TOTPX}}": str(total_px),
    "{{WORDPX}}": str(word_px), "{{BOARDPX}}": str(len(bpx)),
    "{{KG}}": "%.1f" % ((word_g + board_g + strap_g + stats.get("pusher", 6)) / 1000.0),
    "{{NWW}}": str(n_wood_w), "{{NWB}}": str(n_wood_b), "{{NM}}": str(n_mach),
    "{{QALINE}}": qa_line, "{{HERO}}": hero_svg(), "{{MAP}}": map_svg(),
    "{{INV}}": inv_rows, "{{SPARE}}": str(600 - total_px), "{{QAOK}}": n_ok_s,
}.items():
    html = html.replace(k, v)
open("docs/sign-preview/system-preview.html", "w").write(html)
print("wrote docs/sign-preview/system-preview.html (%d px total, word %d + board %d, ~%.1f kg)"
      % (total_px, word_px, len(bpx), (word_g + board_g + strap_g) / 1000.0))
