#!/usr/bin/env python3
"""Generate docs/sign-preview/bracket-preview.html — seam-bracket review card:
lit-board before/after (seam gap fix), strap overlay + legend, per-strap part
drawings, hardware/print/assembly card.
Reads: bolt_el6.json, board_layout.scad, bracket_layout.scad, bolt_pixmap.json.
Optional: --before <old_pixmap.json> (e.g. from git history) for the BEFORE sim.
"""
import json, math, re, subprocess, sys

def arg(f, d):
    return sys.argv[sys.argv.index(f)+1] if f in sys.argv else d

def grab(txt, key):
    return json.loads(re.search(key + r"\s*=\s*(\[.*?\]);", txt, re.S).group(1))

D = json.load(open("src/parts/bolt_el6.json"))
FW, FH = D["face"]
SY, SXT, SXB = D["seam_y"], D["seam_x_top"], D["seam_x_bot"]
C = D["c1"]
paths = [[tuple(q) for q in p] for p in C["yellow"]] + \
        [[tuple(q) for q in p] for p in C["red"]]
n_yellow = len(C["yellow"])
SEAMS = [(1, SY, 0.0, FW), (0, SXT, SY, FH), (0, SXB, 0.0, SY)]
lay = open("src/parts/board_layout.scad").read()
plates = grab(lay, "bb_plates")
scr = grab(lay, "bb_scr")
bites = grab(lay, "bb_bite")
bk = open("src/parts/bracket_layout.scad").read()
bk_w = float(re.search(r"bk_strap_w = ([\d.]+);", bk).group(1))
bk_span = grab(bk, "bk_span")
bk_names = json.loads(re.search(r"bk_names = (\[.*?\]);", bk).group(1).replace('"', '"'))
bk_pass, bk_collar = grab(bk, "bk_pass"), grab(bk, "bk_collar")
bk_nut, bk_socket = grab(bk, "bk_nut"), grab(bk, "bk_socket")
pixmap = json.load(open("src/parts/bolt_pixmap.json"))
new_px = [(p["x"], p["y"], p["color"], p.get("mount", "plate")) for p in pixmap["pixels"]]
before = arg("--before", None)
old_px = None
if before:
    old = json.load(open(before))
    old_px = [(p["x"], p["y"], p["color"], "plate") for p in old["pixels"]]

STRAP_AX = {"S1": (1, SY), "S2": (1, SY), "S3": (0, SXT), "S4": (0, SXB)}
def unlocal(name, q):                 # printed local -> board (v baked
    axis, coord = STRAP_AX[name]      # -v on y-straps, +v on x-straps)
    u, v = q[0], -q[1] if axis == 1 else q[1]
    return (u, coord + v) if axis == 1 else (coord + v, u)

# ---- gap analysis at each channel/seam crossing ----
def plen(p): return sum(math.dist(p[i], p[i+1]) for i in range(len(p)-1))
def point_at(p, t):
    acc = 0.0
    for i in range(len(p)-1):
        d = math.dist(p[i], p[i+1])
        if acc + d >= t:
            f = (t-acc)/d if d else 0
            return (p[i][0]+(p[i+1][0]-p[i][0])*f, p[i][1]+(p[i+1][1]-p[i][1])*f)
        acc += d
    return p[-1]
def t_of(path, q):
    best, acc = (1e9, 0), 0.0
    for i in range(len(path)-1):
        a, b = path[i], path[i+1]
        d = math.dist(a, b)
        if d:
            t = max(0, min(1, ((q[0]-a[0])*(b[0]-a[0])+(q[1]-a[1])*(b[1]-a[1]))/d**2))
            c = (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))
            dd = math.dist(q, c)
            if dd < best[0]:
                best = (dd, acc + t*d)
        acc += d
    return best
def cross_pts():
    out = []
    for si, p in enumerate(paths):
        acc = 0.0
        for i in range(len(p)-1):
            a, b = p[i], p[i+1]
            d = math.dist(a, b)
            if d:
                for axis, coord, b0, b1 in SEAMS:
                    if (a[axis]-coord)*(b[axis]-coord) <= 0 and a[axis] != b[axis]:
                        f = (coord - a[axis]) / (b[axis] - a[axis])
                        if 0 <= f <= 1:
                            q = (a[0]+f*(b[0]-a[0]), a[1]+f*(b[1]-a[1]))
                            if b0 - 2 <= q[1-axis] <= b1 + 2:
                                out.append((si, acc + f*d, q))
            acc += d
    return out
def gaps_at_crossings(px):
    assign = {}
    for q in px:
        best = (1e9, None, 0)
        for si, p in enumerate(paths):
            dd, t = t_of(p, q[:2])
            if dd < best[0]:
                best = (dd, si, t)
        assign.setdefault(best[1], []).append(best[2])
    out = []
    for si, c, q in cross_pts():
        ts = sorted(assign.get(si, []))
        lo = max((t for t in ts if t <= c), default=None)
        hi = min((t for t in ts if t >= c), default=None)
        g = (hi - lo) if lo is not None and hi is not None else None
        out.append((q, g))
    return out
new_gaps = gaps_at_crossings(new_px)
old_gaps = gaps_at_crossings(old_px) if old_px else None

# ---- svg builders ----
COL = {"yellow": "#ffc93c", "red": "#ff5340"}
def fy(y): return FH - y
def path_d(p):
    return "M " + " L ".join("%.1f %.1f" % (q[0], fy(q[1])) for q in p)

def lit_board(px, gaps, gid, callouts=True):
    s = ['<svg viewBox="-8 -8 %d %d" xmlns="http://www.w3.org/2000/svg">'
         % (FW + 16, FH + 16)]
    s.append('<defs><filter id="gl%s" x="-120%%" y="-120%%" width="340%%" height="340%%">'
             '<feGaussianBlur stdDeviation="7"/></filter></defs>' % gid)
    s.append('<rect x="-8" y="-8" width="%d" height="%d" rx="6" fill="#0b0d10"/>'
             % (FW + 16, FH + 16))
    for axis, coord, b0, b1 in SEAMS:
        x1, y1 = (b0, coord) if axis == 1 else (coord, b0)
        x2, y2 = (b1, coord) if axis == 1 else (coord, b1)
        s.append('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="#2a3038" '
                 'stroke-width="1.6" stroke-dasharray="7 6"/>' % (x1, fy(y1), x2, fy(y2)))
    for p in paths:                       # channel + lens hint
        s.append('<path d="%s" fill="none" stroke="#20242b" stroke-width="22" '
                 'stroke-linecap="round" stroke-linejoin="round"/>' % path_d(p))
    for x, y, col, mount in px:           # glow layer then cores
        s.append('<circle cx="%.1f" cy="%.1f" r="8.5" fill="%s" opacity="0.85" '
                 'filter="url(#gl%s)"/>' % (x, fy(y), COL[col], gid))
    for p in paths:                       # faint lens over the glow
        s.append('<path d="%s" fill="none" stroke="#ffffff" stroke-opacity="0.05" '
                 'stroke-width="19" stroke-linecap="round" stroke-linejoin="round"/>'
                 % path_d(p))
    for x, y, col, mount in px:
        s.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="#fff" opacity="0.95"/>'
                 % (x, fy(y)))
    if callouts and gaps:
        for q, g in gaps:
            if g is None:
                continue
            bad = g > 26
            c = "#ff5340" if bad else "#7ad48a"
            s.append('<circle cx="%.1f" cy="%.1f" r="17" fill="none" stroke="%s" '
                     'stroke-width="2" stroke-dasharray="4 4"/>' % (q[0], fy(q[1]), c))
            ly = fy(q[1]) - 22 if q[1] < FH - 40 else fy(q[1]) + 30
            s.append('<text x="%.1f" y="%.1f" fill="%s" font-size="15" '
                     'font-weight="700" text-anchor="middle" '
                     'font-family="ui-monospace,Menlo,monospace">%.0f</text>'
                     % (q[0], ly, c, g))
    s.append('</svg>')
    return "\n".join(s)

def overlay_board():
    s = ['<svg viewBox="-10 -10 %d %d" xmlns="http://www.w3.org/2000/svg">'
         % (FW + 20, FH + 20)]
    s.append('<rect x="-10" y="-10" width="%d" height="%d" rx="6" fill="#101318"/>'
             % (FW + 20, FH + 20))
    for i, (x0, x1, y0, y1) in enumerate(plates):
        s.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#171b21" '
                 'stroke="#333b46" stroke-width="1.4"/>' % (x0, fy(y1), x1-x0, y1-y0))
        s.append('<text x="%.1f" y="%.1f" fill="#57616e" font-size="17" font-weight="700" '
                 'font-family="ui-monospace,Menlo,monospace">B%d</text>'
                 % (x0 + 10, fy(y0) - 10, i + 1))
    for p in paths:
        s.append('<path d="%s" fill="none" stroke="#2c333d" stroke-width="22" '
                 'stroke-linecap="round" stroke-linejoin="round"/>' % path_d(p))
    for x, y, col, mount in new_px:
        s.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="%s" opacity="0.65"/>'
                 % (x, fy(y), COL[col]))
    # straps (translucent white), butt joint tick
    for i, name in enumerate(bk_names):
        axis, coord = STRAP_AX[name]
        u0, u1 = bk_span[i]
        rect = (u0, fy(coord + bk_w/2), u1 - u0, bk_w) if axis == 1 \
               else (coord - bk_w/2, fy(u1), bk_w, u1 - u0)
        s.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="5" '
                 'fill="#e9e5db" fill-opacity="0.13" stroke="#e9e5db" '
                 'stroke-opacity="0.55" stroke-width="1.6"/>' % rect)
        lx, ly = ((u0 + u1)/2, coord + bk_w/2 + 6) if axis == 1 \
                 else (coord - bk_w/2 - 6, (u0 + u1)/2)
        s.append('<text x="%.1f" y="%.1f" fill="#cfc9bc" font-size="15" font-weight="700" '
                 'text-anchor="middle" font-family="ui-monospace,Menlo,monospace"%s>%s</text>'
                 % (lx, fy(ly), ' transform="rotate(-90 %.1f %.1f)"' % (lx, fy(ly))
                    if axis == 0 else '', name))
    # features (board coords via unlocal)
    for i, name in enumerate(bk_names):
        for q in bk_pass[i]:
            x, y = unlocal(name, q)
            s.append('<circle cx="%.1f" cy="%.1f" r="8.5" fill="none" stroke="#8b94a1" '
                     'stroke-width="1.3" stroke-dasharray="3 3"/>' % (x, fy(y)))
        for q in bk_collar[i]:
            x, y = unlocal(name, q)
            s.append('<circle cx="%.1f" cy="%.1f" r="8" fill="none" stroke="#ffc93c" '
                     'stroke-width="2.2"/><circle cx="%.1f" cy="%.1f" r="3.2" '
                     'fill="#ffc93c"/>' % (x, fy(y), x, fy(y)))
        for q in bk_socket[i]:
            x, y = unlocal(name, q)
            s.append('<circle cx="%.1f" cy="%.1f" r="8" fill="none" stroke="#7ad48a" '
                     'stroke-width="1.8"/><path d="M %.1f %.1f h 10 M %.1f %.1f v 10" '
                     'stroke="#7ad48a" stroke-width="1.6"/>'
                     % (x, fy(y), x - 5, fy(y), x, fy(y) - 5))
    for q in scr:
        if q[2] == 1:
            s.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="#ffc93c"/>'
                     % (q[0], fy(q[1])))
        else:
            s.append('<rect x="%.1f" y="%.1f" width="6" height="6" fill="#707a87"/>'
                     % (q[0] - 3, fy(q[1]) - 3))
    s.append('</svg>')
    return "\n".join(s)

def strap_drawing(i, name):
    axis, coord = STRAP_AX[name]
    u0, u1 = bk_span[i]
    L = u1 - u0
    s = ['<svg viewBox="%.0f -34 %.0f 72" xmlns="http://www.w3.org/2000/svg">'
         % (u0 - 6, L + 12)]
    s.append('<rect x="%.1f" y="-24" width="%.1f" height="48" rx="4" fill="#242a33" '
             'stroke="#4a5462" stroke-width="1.2"/>' % (u0, L))
    for sgn in (-1, 1):                    # rails
        s.append('<rect x="%.1f" y="%.1f" width="%.1f" height="5" fill="#303845"/>'
                 % (u0 + 6, -24 if sgn < 0 else 19, L - 12))
    for q in bk_pass[i]:
        s.append('<circle cx="%.1f" cy="%.1f" r="8.5" fill="#12151a" stroke="#8b94a1" '
                 'stroke-width="1" stroke-dasharray="3 2"/>' % (q[0], q[1]))
    for q in bk_collar[i]:
        s.append('<circle cx="%.1f" cy="%.1f" r="7.9" fill="#12151a" stroke="#ffc93c" '
                 'stroke-width="2"/><circle cx="%.1f" cy="%.1f" r="6.1" fill="none" '
                 'stroke="#ffc93c" stroke-width="0.8"/>' % (q[0], q[1], q[0], q[1]))
    for q in bk_nut[i]:
        pts = " ".join("%.1f,%.1f" % (q[0] + 4.6*math.cos(math.radians(a)),
                                      q[1] + 4.6*math.sin(math.radians(a)))
                       for a in range(0, 360, 60))
        s.append('<polygon points="%s" fill="none" stroke="#e9e5db" stroke-width="1.3"/>'
                 '<circle cx="%.1f" cy="%.1f" r="2.2" fill="#e9e5db"/>'
                 % (pts, q[0], q[1]))
    for q in bk_socket[i]:
        s.append('<circle cx="%.1f" cy="%.1f" r="8" fill="none" stroke="#7ad48a" '
                 'stroke-width="1.6"/><circle cx="%.1f" cy="%.1f" r="5.1" fill="none" '
                 'stroke="#7ad48a" stroke-width="1" stroke-dasharray="2 2"/>'
                 % (q[0], q[1], q[0], q[1]))
    s.append('</svg>')
    return "\n".join(s), L

# QA audit results (tools/qa_board.py), if present
qa_html = ""
try:
    qa = json.load(open("src/parts/board_qa.json"))
    n_ok = sum(1 for c in qa["checks"] if c["ok"])
    rows_qa = "\n".join(
        '<tr><td><span class="%s">%s</span></td><td>%s</td><td>%s</td></tr>'
        % ("ok" if c["ok"] else "warn", "PASS" if c["ok"] else "FAIL",
           c["name"], c["detail"]) for c in qa["checks"])
    qa_html = ('<h2>QA audit — %d/%d checks pass</h2>'
               '<p class="sub">Independent audit (<code>tools/qa_board.py</code>): '
               'placement physics and screw legality re-measured from the emitted '
               'data, features probed at STL level (hole positions, collar bore '
               'profile, plate bites), and every mesh edge-audited.</p>'
               '<div style="overflow-x:auto"><table>'
               '<tr><th></th><th>check</th><th>measured</th></tr>%s</table></div>'
               % (n_ok, len(qa["checks"]), rows_qa))
except FileNotFoundError:
    pass

# frame-mounting holes (perimeter wood screws), per edge
wood = [s for s in scr if s[2] == 0]
edges = [("bottom edge (y≈6)", [s for s in wood if s[1] < 10]),
         ("top edge (y≈544)", [s for s in wood if s[1] > FH - 10]),
         ("left edge (x≈6)", [s for s in wood if s[0] < 10]),
         ("right edge (x≈404)", [s for s in wood if s[0] > FW - 10])]
frame_html = "".join(
    "<tr><td>%s</td><td>%d</td><td>%s</td></tr>"
    % (lab, len(pts), ", ".join("(%g, %g)" % (p[0], p[1]) for p in pts))
    for lab, pts in edges)

# grams (if strap STLs are built)
strap_g = {}
try:
    out = subprocess.run(["python3", "tools/stl_stats.py"] +
                         ["stl/strap_s%d.stl" % k for k in (1, 2, 3, 4)],
                         capture_output=True, text=True, timeout=120).stdout
    for m in re.finditer(r"strap_s(\d)\.stl\s+[\d.]+\s+cm3\s+([\d.]+)\s+g", out):
        strap_g[int(m.group(1))] = float(m.group(2))
except Exception:
    pass

n_mach = sum(1 for q in scr if q[2] == 1)
n_wood = len(scr) - n_mach
worst_old = max((g for q, g in old_gaps if g), default=0) if old_gaps else None
worst_new = max((g for q, g in new_gaps if g), default=0)

rows = []
for i, name in enumerate(bk_names):
    svg, L = strap_drawing(i, name)
    axis, coord = STRAP_AX[name]
    seam = ("y=255" if axis == 1 else ("x=126" if coord == SXT else "x=153"))
    g = (" · %.0f g" % strap_g[i+1]) if (i+1) in strap_g else ""
    rows.append(
        '<div class="strap"><div class="strap-head"><span class="tag">%s</span>'
        '<span>seam %s · %.0f × 48 × 12 mm%s · %d pass / %d collar / %d nut / %d socket</span>'
        '</div><div class="strap-svg">%s</div></div>'
        % (name, seam, L, g, len(bk_pass[i]), len(bk_collar[i]),
           len(bk_nut[i]), len(bk_socket[i]), svg))

before_html = ""
if old_px:
    before_html = """
<div class="board">
  <div class="board-cap">BEFORE — 12.5&nbsp;mm keepout, gaps to %.0f&nbsp;mm at the joints</div>
  %s
</div>""" % (worst_old, lit_board(old_px, old_gaps, "o"))

html = """<title>Bolt board — seam brackets</title>
<style>
:root {
  --bg:#14161a; --panel:#1d222a; --panel2:#171b21; --line:#2c333d;
  --ink:#e9e5db; --mut:#8b94a1; --yel:#ffc93c; --red:#ff5340; --ok:#7ad48a;
}
html { background:var(--bg); }
body { margin:0; color:var(--ink); background:var(--bg);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.wrap { max-width:1080px; margin:0 auto; padding:36px 22px 80px; }
h1,h2,.tag,.stat b,.board-cap,.strap-head,th { font-family:ui-monospace,Menlo,Consolas,monospace; }
h1 { font-size:26px; letter-spacing:.02em; margin:0 0 4px; text-wrap:balance; }
h2 { font-size:15px; letter-spacing:.14em; text-transform:uppercase; color:var(--yel);
     margin:52px 0 14px; }
h2:after { content:""; display:block; height:1px; background:var(--line); margin-top:8px; }
.sub { color:var(--mut); margin:0 0 24px; max-width:68ch; }
.stats { display:flex; flex-wrap:wrap; gap:10px; margin:20px 0 6px; }
.stat { background:var(--panel); border:1px solid var(--line); border-radius:8px;
  padding:10px 16px; }
.stat b { display:block; font-size:21px; font-variant-numeric:tabular-nums; }
.stat span { color:var(--mut); font-size:12.5px; letter-spacing:.05em; text-transform:uppercase; }
.boards { display:flex; flex-wrap:wrap; gap:18px; align-items:flex-start; }
.board { flex:1 1 320px; max-width:520px; }
.board svg { width:100%; height:auto; display:block; border-radius:10px; }
.board-cap { font-size:12.5px; color:var(--mut); letter-spacing:.06em; margin:0 0 8px;
  text-transform:uppercase; }
.overlay svg { width:100%; height:auto; display:block; border-radius:10px; }
.legend { display:flex; flex-wrap:wrap; gap:14px 26px; background:var(--panel);
  border:1px solid var(--line); border-radius:10px; padding:14px 18px; margin-top:14px;
  font-size:13.5px; color:var(--mut); }
.legend .it { display:flex; align-items:center; gap:8px; }
.legend svg { width:22px; height:22px; flex:none; }
.strap { background:var(--panel2); border:1px solid var(--line); border-radius:10px;
  padding:12px 16px 8px; margin:12px 0; }
.strap-head { display:flex; gap:12px; align-items:baseline; font-size:13px;
  color:var(--mut); margin-bottom:6px; }
.tag { background:var(--yel); color:#14161a; font-weight:700; border-radius:5px;
  padding:1px 8px; font-size:13px; }
.strap-svg { overflow-x:auto; }
.strap-svg svg { min-width:520px; width:100%; height:auto; display:block; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th { text-align:left; color:var(--mut); font-size:12px; letter-spacing:.1em;
  text-transform:uppercase; font-weight:600; padding:8px 14px 8px 0; }
td { padding:7px 14px 7px 0; border-top:1px solid var(--line);
  font-variant-numeric:tabular-nums; }
ol { margin:0; padding-left:22px; }
li { margin:7px 0; }
li::marker { color:var(--yel); font-family:ui-monospace,Menlo,monospace; font-weight:700; }
.note { background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--yel);
  border-radius:8px; padding:12px 16px; color:var(--mut); font-size:14px; margin-top:14px; }
.ok { color:var(--ok); } .warn { color:var(--red); }
@media (prefers-reduced-motion:no-preference) {
  .board svg circle[filter] { transition:opacity .3s; }
}
</style>
<div class="wrap">
<h1>BOLT BOARD — SEAM BRACKETS</h1>
<p class="sub">Continuous LEDs across all four plate joints. Pixels are pinned at every
channel/seam crossing (±9.5&nbsp;mm straddle; the two shallow crossings put the pixel ON
the seam with its collar embedded in a printed strap). White PETG splice straps replace
the y-seam wood rail — the plates screw into captive M4 nuts.</p>
<div class="stats">
  <div class="stat"><b>137</b><span>pixels (unchanged)</span></div>
  <div class="stat"><b>21.5&nbsp;mm</b><span>solved pitch</span></div>
  <div class="stat"><b class="ok">{{WORST_NEW}}&nbsp;mm</b><span>worst seam gap (was {{WORST_OLD}})</span></div>
  <div class="stat"><b>2</b><span>strap-mounted pixels</span></div>
  <div class="stat"><b>{{N_MACH}} + {{N_WOOD}}</b><span>M4×8 + wood screws</span></div>
</div>

<h2>Lit board — before / after</h2>
<div class="boards">
{{BEFORE}}
<div class="board">
  <div class="board-cap">AFTER — anchored straddle, every crossing ≤ {{WORST_NEW}}&nbsp;mm</div>
  {{AFTER}}
</div>
</div>
<p class="sub" style="margin-top:14px">Ring callouts = LED spacing (mm) across each of the
7 channel/seam crossings. <span class="warn">Red</span> reads as a visible dark spot;
<span class="ok">green</span> is within a pitch of uniform. Numbers are arc distance between
the two pixels flanking the joint.</p>

<h2>Strap layout on the board</h2>
<div class="overlay">{{OVERLAY}}</div>
<div class="legend">
  <div class="it"><svg viewBox="0 0 22 22"><rect x="2" y="6" width="18" height="10" rx="3" fill="#e9e5db" fill-opacity="0.13" stroke="#e9e5db" stroke-opacity="0.55"/></svg> seam strap (white PETG, behind the plates)</div>
  <div class="it"><svg viewBox="0 0 22 22"><circle cx="11" cy="11" r="4" fill="#ffc93c"/></svg> M4×8 machine screw → captive nut</div>
  <div class="it"><svg viewBox="0 0 22 22"><rect x="7" y="7" width="8" height="8" fill="#707a87"/></svg> wood screw → frame perimeter</div>
  <div class="it"><svg viewBox="0 0 22 22"><circle cx="11" cy="11" r="8" fill="none" stroke="#8b94a1" stroke-width="1.4" stroke-dasharray="3 3"/></svg> Ø17 pixel pass-through</div>
  <div class="it"><svg viewBox="0 0 22 22"><circle cx="11" cy="11" r="7.5" fill="none" stroke="#ffc93c" stroke-width="2"/><circle cx="11" cy="11" r="2.8" fill="#ffc93c"/></svg> embedded collar (on-seam pixel)</div>
  <div class="it"><svg viewBox="0 0 22 22"><circle cx="11" cy="11" r="8" fill="none" stroke="#7ad48a" stroke-width="1.6"/><path d="M6 11h10M11 6v10" stroke="#7ad48a" stroke-width="1.4"/></svg> leg socket (Ø10.2, legs optional)</div>
  <div class="it"><svg viewBox="0 0 22 22"><circle cx="11" cy="11" r="3.4" fill="#ffc93c" opacity="0.65"/></svg> pixel (yellow zone)</div>
  <div class="it"><svg viewBox="0 0 22 22"><circle cx="11" cy="11" r="3.4" fill="#ff5340" opacity="0.65"/></svg> pixel (red zone)</div>
</div>

<h2>Strap parts (printed front-face-down, as drawn)</h2>
{{STRAPS}}
<div class="note">Feature coords are pre-mirrored for the flip-to-install — what you see
here is the part as it lies on the bed. S1 and S2 butt at x=145.5 (mid-plate; the plates
themselves splice the joint, a screw pair flanks each side). Plus one <b>pixel pusher</b>
(Ø14 slotted tube) for seating pixels through the pass-holes.</div>

<h2>Frame mounting (wooden frame around the bolt)</h2>
<p class="sub">The strap-joined board mounts to its wood frame by the PERIMETER only —
{{N_WOOD}} pre-drilled Ø4.5 holes for the same black wood screws as the word pieces
(≤150&nbsp;mm spacing, all positions channel-checked). Bottom + top rails and two side
stiles; the old y-seam rail is gone. Shown as gray squares in the overlay above.</p>
<div style="overflow-x:auto"><table>
<tr><th>edge</th><th>holes</th><th>positions (board mm)</th></tr>
{{FRAME}}
</table></div>

{{QA}}

<h2>Hardware &amp; assembly</h2>
<table>
<tr><th>item</th><th>qty</th><th>spec</th></tr>
<tr><td>M4 button-head, black</td><td>{{N_MACH}} (+ spares)</td><td>M4×8 — through the face into strap nuts</td></tr>
<tr><td>M4 hex nut</td><td>{{N_MACH}}</td><td>drop into the open pockets on the strap backs</td></tr>
<tr><td>Wood screws Ø4.5</td><td>{{N_WOOD}}</td><td>perimeter only — bottom/top rails + side stiles</td></tr>
<tr><td>Straps S1–S4</td><td>4</td><td>white PETG, ~0.20 std, no supports{{STRAPG}}</td></tr>
<tr><td>Pixel pusher</td><td>1</td><td>any color, 5&nbsp;min print</td></tr>
</table>
<ol style="margin-top:18px">
<li>Plates face-down on a flat table, butted B1|B2, B3|B4, rows together.</li>
<li>Drop M4 nuts in the strap pockets, set straps on the seams, screw from the front.</li>
<li>Mount the joined panel to the frame by the perimeter wood screws (no y-seam rail).</li>
<li>Press pixels in from behind — near seams they pass through the strap holes
(use the pusher; the two on-seam pixels seat into the strap collars, 2&nbsp;mm deeper
by design).</li>
<li>Chain per <code>bolt_pixmap.json</code> (jumpers at links {{JUMP}}); wires always
route behind the straps — nothing gets pinched.</li>
</ol>
<div class="note">Leg sockets stay empty for now. If the mounted panel flexes against the
back skin, print Ø10 friction-fit legs at the measured plenum depth and press them into
the three sockets — the "pizza saver" upgrade path.</div>
</div>
"""
chain = sorted(pixmap["pixels"], key=lambda p: p["chain"])
longs = [k for k in range(len(chain) - 1)
         if math.dist((chain[k]["x"], chain[k]["y"]),
                      (chain[k+1]["x"], chain[k+1]["y"])) > 101.6]
jump = ", ".join(str(k) for k in longs) if longs else "none"
for k, v in {
    "{{WORST_NEW}}": "%.1f" % worst_new,
    "{{WORST_OLD}}": ("%.0f mm" % worst_old) if worst_old else "n/a",
    "{{N_MACH}}": str(n_mach), "{{N_WOOD}}": str(n_wood),
    "{{BEFORE}}": before_html,
    "{{AFTER}}": lit_board(new_px, new_gaps, "n"),
    "{{OVERLAY}}": overlay_board(),
    "{{STRAPS}}": "\n".join(rows),
    "{{STRAPG}}": (" · " + " / ".join("%.0f g" % strap_g[k] for k in sorted(strap_g)))
                  if strap_g else "",
    "{{JUMP}}": jump,
    "{{QA}}": qa_html,
    "{{FRAME}}": frame_html,
}.items():
    html = html.replace(k, v)
open("docs/sign-preview/bracket-preview.html", "w").write(html)
print("wrote docs/sign-preview/bracket-preview.html "
      "(worst seam gap: old %s -> new %.1f)"
      % (("%.1f" % worst_old) if worst_old else "n/a", worst_new))
