#!/usr/bin/env python3
"""Wiring + WLED mapping for the CHARGE sign.
- Defines the WORD's physical data chain (letters left->right, tube-run order
  within each letter, greedy end-to-end like the board) and persists it to
  src/parts/word_pixmap.json (the wiring truth — do not reorder after wiring).
- Reads the BOARD chain from src/parts/bolt_pixmap.json.
- Emits docs/sign-preview/wiring.html: per-sign back-view (as wired) + front
  view, chain gradient with direction arrows, extension cut list, WLED card.
- Emits wled/{word,board}-controller/: ledmap.json (2D grid, 10 mm cells,
  -1 = empty) + presets.json (2D rect segment scenes) — named ready to upload
  at /edit. NOTE: once the ledmap loads, WLED is a 2D matrix and segments are
  RECTANGLES (start/stop = columns, startY/stopY = rows, stops exclusive);
  chain-index segments would be reinterpreted as garbage rectangles.
4-inch strings: links over 101.6 mm need cutting + an extension splice.
"""
import json, math, os, re

LINK_MM = 101.6

# ---------- board ----------
BP = json.load(open("src/parts/bolt_pixmap.json"))["pixels"]
board = sorted(BP, key=lambda p: p["chain"])
D = json.load(open("src/parts/bolt_el6.json"))
FW, FH = D["face"]
bpaths = [[tuple(q) for q in p] for p in D["c1"]["yellow"]] + \
         [[tuple(q) for q in p] for p in D["c1"]["red"]]

# ---------- word chain ----------
W = json.load(open("src/parts/word_cuts_repairs.json"
                   if os.path.exists("src/parts/word_cuts_repairs.json")
                   else "src/parts/word_cuts.json"))
wpaths = [[tuple(q) for q in p] for p in W["paths"]]
wx0, wy0, wx1, wy1 = W["face"]

def t_of(path, q):
    best, acc = (1e9, 0), 0.0
    for i in range(len(path)-1):
        a, b = path[i], path[i+1]
        d = math.dist(a, b)
        if d:
            t = max(0, min(1, ((q[0]-a[0])*(b[0]-a[0])+(q[1]-a[1])*(b[1]-a[1]))/d**2))
            c = (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))
            if math.dist(q, c) < best[0]:
                best = (math.dist(q, c), acc + t*d)
        acc += d
    return best

# pixel -> (path, arc t)
runs = {}
for x, y in W["pixels"]:
    b = min(((t_of(p, (x, y))[0], si, t_of(p, (x, y))[1])
             for si, p in enumerate(wpaths)))
    runs.setdefault(b[1], []).append((b[2], x, y))
for si in runs:
    runs[si].sort()
# path -> letter (centroid x vs piece centers)
piece_ctr = [((pc["x0"] + pc["x1"]) / 2, pc["letter"], k + 1)
             for k, pc in enumerate(W["pieces"])]
path_letter = {}
for si, p in enumerate(wpaths):
    cx = sum(q[0] for q in p) / len(p)
    _, letter, piece = min(piece_ctr, key=lambda c: abs(c[0] - cx))
    path_letter[si] = (letter, piece)
letters = [pc["letter"] for pc in W["pieces"]]

word, tail = [], None
for L in letters:                       # left -> right, C first (data enters left)
    sis = [si for si in runs if path_letter[si][0] == L]
    done = set()
    while len(done) < len(sis):
        best = None
        for si in sis:
            if si in done:
                continue
            for fw in (True, False):
                seq = runs[si] if fw else runs[si][::-1]
                head = (seq[0][1], seq[0][2])
                d = math.dist(tail, head) if tail else head[0]  # first: leftmost end
                if best is None or d < best[0]:
                    best = (d, si, fw)
        _, si, fw = best
        seq = runs[si] if fw else runs[si][::-1]
        for t, x, y in seq:
            word.append({"x": round(x, 2), "y": round(y, 2),
                         "letter": path_letter[si][0], "piece": path_letter[si][1]})
        tail = (word[-1]["x"], word[-1]["y"])
        done.add(si)
# AS-BUILT OVERRIDE (2026-07-13, user-wired): in R, the planned 104.9 mm
# tube hop (bowl end -> y=197 row) was avoided by taking the row-start pixel
# EARLY: as-built 237 = plan-247's position, then down and around the bowl
# (as-built 238..247 = plan 237..246), then an 89.6 mm no-cut jump to 248.
# A rotate-by-one of the block; coordinates pinned so any upstream change fails.
def _near(p, xy):
    return math.dist((p["x"], p["y"]), xy) < 0.5
assert _near(word[247], (954.63, 197.58)) and _near(word[246], (859.04, 154.41)) \
    and _near(word[237], (959.14, 177.01)) and _near(word[248], (937.51, 197.71)), \
    "R as-built override no longer matches the computed chain — re-derive it"
word[237:248] = [word[247]] + word[237:247]

for i, p in enumerate(word):
    p["chain"] = i
json.dump({"chain_note": "physical data order — letters C->E, tube runs greedy; "
                         "links over %.1fmm need an extension splice. AS-BUILT: "
                         "R block 237-247 rotated (row-start taken early) to kill "
                         "the 104.9mm tube hop — matches the wired sign." % LINK_MM,
           "pixels": word}, open("src/parts/word_pixmap.json", "w"), indent=1)

def links_of(chain):
    return [math.dist((chain[k]["x"], chain[k]["y"]),
                      (chain[k+1]["x"], chain[k+1]["y"]))
            for k in range(len(chain) - 1)]

blinks, wlinks = links_of(board), links_of(word)
bext = [(k, blinks[k]) for k in range(len(blinks)) if blinks[k] > LINK_MM]
wext = [(k, wlinks[k]) for k in range(len(wlinks)) if wlinks[k] > LINK_MM]

# ---------- WLED ledmaps + presets ----------
os.makedirs("wled/word-controller", exist_ok=True)
os.makedirs("wled/board-controller", exist_ok=True)
CELL = 10.0
def grid_xy(p, w_mm, h_mm, ox=0.0, oy=0.0):
    W_, H_ = math.ceil(w_mm / CELL), math.ceil(h_mm / CELL)
    return (min(W_ - 1, int((p["x"] - ox) / CELL)),
            min(H_ - 1, int((h_mm - (p["y"] - oy) - 0.001) / CELL)))  # row 0 = top

def ledmap(chain, name, w_mm, h_mm, ox=0.0, oy=0.0):
    W_, H_ = math.ceil(w_mm / CELL), math.ceil(h_mm / CELL)
    grid = [-1] * (W_ * H_)
    for p in chain:
        gx, gy = grid_xy(p, w_mm, h_mm, ox, oy)
        idx = gy * W_ + gx
        assert grid[idx] == -1, "cell collision at %s" % ((p["x"], p["y"]),)
        grid[idx] = p["chain"]
    # WLED 16.x deserializeMap reads "width"/"height" (NOT "w"/"h"); extra keys
    # like "n" pass through its filter harmlessly. Array is grid-position-indexed
    # (row 0 = top), values = physical LED index, -1 = no LED in that cell.
    # Loading a default ledmap with width/height sets matrix dims + 2D mode at
    # boot — no 2D Configuration needed, and 2d-gaps.json is ignored entirely.
    return {"n": name, "width": W_, "height": H_, "map": grid}

# COMPACT separators are load-bearing: WLED 16.x streams the map with a raw
# byte search for `"map":[` (FX_fcn.cpp deserializeMap) — `"map": [` with a
# space silently loads ZERO entries and the matrix falls back to an identity
# map (chain crammed into the top rows). width/height still apply, which
# makes the failure look like a scrambled 2D layout, not a missing file.
for path, m in (("wled/board-controller/ledmap.json",
                 ledmap(board, "CHARGE bolt board", FW, FH)),
                ("wled/word-controller/ledmap.json",
                 ledmap(word, "CHARGE word", wx1 - wx0, W["face_h"],
                        ox=wx0, oy=wy0))):
    json.dump(m, open(path, "w"), separators=(",", ":"))
    assert '"map":[' in open(path).read(), "%s: map key not byte-exact" % path

# Segments in 2D mode are rectangles; WLED v16 composites them in id order
# with blend mode 0 ("top"), so a later rect paints over an earlier one.
def rseg(i, x0, x1, y0, y1, col, name):
    return {"id": i, "start": x0, "stop": x1, "startY": y0, "stopY": y1,
            "col": [col, [0, 0, 0], [0, 0, 0]], "fx": 0, "n": name,
            "on": True, "bri": 255}

def pad(segs):  # {"stop":0} deletes leftover segments on the controller
    return segs + [{"id": i, "stop": 0} for i in range(len(segs), 32)]

def paint(segs, W_, H_):  # emulate v16: rects in id order, later wins
    px = {}
    for s in segs:
        assert 0 < s["stop"] <= W_ and s["stopY"] <= H_, \
            "segment %r exceeds the grid — WLED would clamp it" % s["n"]
        for y in range(s["startY"], s["stopY"]):
            for x in range(s["start"], s["stop"]):
                px[(x, y)] = s["n"]
    return px

# Bolt: yellow base rect + fewest red rects that trap no yellow cell (empty
# cells are free — no LED, nothing to mis-color). Candidates are maximal
# yellow-free column runs per row band; greedy set cover over red cells.
BW, BH = math.ceil(FW / CELL), math.ceil(FH / CELL)
bcell = {grid_xy(p, FW, FH): p["color"] for p in board}
red = {c for c, v in bcell.items() if v == "red"}
yel = {c for c, v in bcell.items() if v == "yellow"}
cands = []
for y0 in range(BH):
    for y1 in range(y0, BH):
        ok = [all((x, y) not in yel for y in range(y0, y1 + 1)) for x in range(BW)]
        x = 0
        while x < BW:
            if not ok[x]:
                x += 1
                continue
            x2 = x
            while x2 + 1 < BW and ok[x2 + 1]:
                x2 += 1
            cov = frozenset(c for c in red if x <= c[0] <= x2 and y0 <= c[1] <= y1)
            if cov:
                cands.append((cov, (x, x2, y0, y1)))
            x = x2 + 1
uncov, rrects = set(red), []
while uncov:
    cov, r = max(cands, key=lambda cr: (len(cr[0] & uncov),
                                        -(cr[1][1] - cr[1][0] + 1) * (cr[1][3] - cr[1][2] + 1)))
    rrects.append(r)
    uncov -= cov
bsegs = [rseg(0, 0, BW, 0, BH, [255, 190, 30], "yellow")] + \
        [rseg(k + 1, x0, x1 + 1, y0, y1 + 1, [255, 40, 20], "red %d" % (k + 1))
         for k, (x0, x1, y0, y1) in enumerate(sorted(rrects, key=lambda r: (r[2], r[0])))]
bpx = paint(bsegs, BW, BH)
assert all((bcell[c] == "red") == bpx[c].startswith("red") for c in bcell), \
    "bolt rect stack mis-colors a pixel — red cover no longer clean"

# Word: one column band per letter, full height; cut columns chosen to
# misassign the fewest cells where slanted neighbors interleave.
WW = math.ceil((wx1 - wx0) / CELL)
WH = math.ceil(W["face_h"] / CELL)
wcell = {grid_xy(p, wx1 - wx0, W["face_h"], wx0, wy0): p["letter"] for p in word}
lcols = {L: sorted(x for (x, y), v in wcell.items() if v == L) for L in letters}
cuts = [0]
for a, b in zip(letters, letters[1:]):
    lo = min(min(lcols[b]), max(lcols[a]) + 1)
    hi = max(max(lcols[a]) + 1, min(lcols[b]))
    cuts.append(min((sum(1 for x in lcols[a] if x >= k)
                     + sum(1 for x in lcols[b] if x < k), k)
                    for k in range(lo, hi + 1))[1])
cuts.append(WW)
wsegs = [rseg(i, cuts[i], cuts[i + 1], 0, WH, [235, 245, 255], L)
         for i, L in enumerate(letters)]
wpx = paint(wsegs, WW, WH)
stray = sorted(c for c in wcell if wpx[c] != wcell[c])
# 16 seam cells (C/H 5, H/A 8, G/E 3) sit in the neighbor's band — invisible
# while every letter runs the same color; pinned so geometry drift fails loudly.
assert len(stray) == 16, "letter seam misassignment changed: %d %r" % (len(stray), stray)

json.dump({"1": {"n": "Bolt zones", "mainseg": 0, "on": True, "bri": 200,
                 "seg": pad(bsegs)}},
          open("wled/board-controller/presets.json", "w"), indent=1)
json.dump({"1": {"n": "Word letters", "mainseg": 0, "on": True, "bri": 200,
                 "seg": pad(wsegs)}},
          open("wled/word-controller/presets.json", "w"), indent=1)

# chain color runs — physical zone documentation for the wiring tables
bruns, cur = [], None
for p in board:
    if cur and cur[0] == p["color"]:
        cur[2] = p["chain"]
    else:
        cur = [p["color"], p["chain"], p["chain"]]
        bruns.append(cur)
lruns, cur = [], None
for p in word:
    if cur and cur[0] == p["letter"]:
        cur[2] = p["chain"]
    else:
        cur = [p["letter"], p["chain"], p["chain"]]
        lruns.append(cur)

# ---------- wiring page ----------
def hue(f):                              # chain-position gradient, readable on dark
    h = 175 + 145 * f                    # cyan -> magenta
    return "hsl(%.0f 90%% 62%%)" % h

def chain_svg(chain, paths, w_mm, h_mm, ox, oy, back, tube_w, labels_every=10):
    """back=True mirrors x (viewed from behind — the wiring reality)."""
    def X(x): return (w_mm - (x - ox)) if back else (x - ox)
    def Y(y): return h_mm - (y - oy)
    s = ['<svg viewBox="-14 -14 %.0f %.0f" xmlns="http://www.w3.org/2000/svg">'
         % (w_mm + 28, h_mm + 28)]
    s.append('<rect x="-14" y="-14" width="%.0f" height="%.0f" rx="8" fill="#0e1014"/>'
             % (w_mm + 28, h_mm + 28))
    for p in paths:
        d = "M " + " L ".join("%.1f %.1f" % (X(q[0]), Y(q[1])) for q in p)
        s.append('<path d="%s" fill="none" stroke="#232830" stroke-width="%.0f" '
                 'stroke-linecap="round" stroke-linejoin="round"/>' % (d, tube_w))
    n = len(chain)
    for k in range(n - 1):
        a, b = chain[k], chain[k + 1]
        L = math.dist((a["x"], a["y"]), (b["x"], b["y"]))
        ext = L > LINK_MM
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="%s"%s opacity="0.9"/>'
                 % (X(a["x"]), Y(a["y"]), X(b["x"]), Y(b["y"]),
                    "#ffd34d" if ext else hue(k / max(1, n - 2)),
                    "3.4" if ext else "2",
                    ' stroke-dasharray="6 4"' if ext else ""))
        if ext:
            mx, my = (X(a["x"]) + X(b["x"])) / 2, (Y(a["y"]) + Y(b["y"])) / 2
            s.append('<text x="%.1f" y="%.1f" fill="#ffd34d" font-size="13" '
                     'font-weight="700" text-anchor="middle" '
                     'font-family="ui-monospace,Menlo,monospace">EXT %.0fmm</text>'
                     % (mx, my - 8, L))
    for k, p in enumerate(chain):
        s.append('<circle cx="%.1f" cy="%.1f" r="3.1" fill="%s"/>'
                 % (X(p["x"]), Y(p["y"]), hue(k / max(1, n - 1))))
        if k % labels_every == 0 or k == n - 1:
            s.append('<text x="%.1f" y="%.1f" fill="#aab4c0" font-size="11" '
                     'text-anchor="middle" font-family="ui-monospace,Menlo,monospace">'
                     '%d</text>' % (X(p["x"]), Y(p["y"]) - 7, k))
    for k, lab, col in ((0, "DATA IN", "#7ad48a"), (n - 1, "END", "#ff5340")):
        p = chain[k]
        s.append('<circle cx="%.1f" cy="%.1f" r="8" fill="none" stroke="%s" '
                 'stroke-width="2.5"/><text x="%.1f" y="%.1f" fill="%s" '
                 'font-size="14" font-weight="700" text-anchor="middle" '
                 'font-family="ui-monospace,Menlo,monospace">%s</text>'
                 % (X(p["x"]), Y(p["y"]), col,
                    X(p["x"]), Y(p["y"]) + 24, col, lab))
    s.append('</svg>')
    return "\n".join(s)

def ext_rows(chain, exts):
    out = []
    for k, L in exts:
        a, b = chain[k], chain[k + 1]
        out.append("<tr><td>link %d → %d</td><td>(%.0f, %.0f) → (%.0f, %.0f)</td>"
                   "<td>%.0f mm</td><td>cut + splice ≥ %.0f mm in</td></tr>"
                   % (k, k + 1, a["x"], a["y"], b["x"], b["y"], L, L - LINK_MM + 20))
    return "\n".join(out) or '<tr><td colspan="4">none — every link fits a 4-inch string</td></tr>'

def seg_rows(runsx, palette):
    return "\n".join('<tr><td>%s</td><td>%d – %d</td><td>%d px</td><td>%s</td></tr>'
                     % (nm, a, b, b - a + 1, palette(nm)) for nm, a, b in runsx)

wtube = W.get("band_out", 22.0)
html = """<title>CHARGE — wiring & WLED</title>
<style>
:root { --bg:#14161a; --panel:#1d222a; --line:#2c333d; --ink:#e9e5db;
  --mut:#8b94a1; --yel:#ffc93c; --ok:#7ad48a; --red:#ff5340; --cyan:#9fd8ff; }
html { background:var(--bg); }
body { margin:0; color:var(--ink); background:var(--bg);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.wrap { max-width:1120px; margin:0 auto; padding:36px 22px 80px; }
h1,h2,h3,th,.cap,.stat b { font-family:ui-monospace,Menlo,Consolas,monospace; }
h1 { font-size:26px; margin:0 0 4px; }
h2 { font-size:15px; letter-spacing:.14em; text-transform:uppercase; color:var(--yel);
  margin:52px 0 14px; }
h2:after { content:""; display:block; height:1px; background:var(--line); margin-top:8px; }
h3 { font-size:13px; letter-spacing:.1em; text-transform:uppercase; color:var(--mut);
  margin:22px 0 8px; }
.sub { color:var(--mut); margin:0 0 20px; max-width:70ch; }
.stats { display:flex; flex-wrap:wrap; gap:10px; margin:18px 0; }
.stat { background:var(--panel); border:1px solid var(--line); border-radius:8px;
  padding:9px 15px; }
.stat b { display:block; font-size:20px; font-variant-numeric:tabular-nums; }
.stat span { color:var(--mut); font-size:12px; letter-spacing:.05em; text-transform:uppercase; }
.wide svg { width:100%; height:auto; display:block; border-radius:10px; }
.front { max-width:46%; opacity:.85; }
.cap { font-size:12.5px; color:var(--mut); letter-spacing:.06em;
  text-transform:uppercase; margin:8px 0 18px; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th { text-align:left; color:var(--mut); font-size:12px; letter-spacing:.1em;
  text-transform:uppercase; font-weight:600; padding:8px 14px 8px 0; }
td { padding:7px 14px 7px 0; border-top:1px solid var(--line);
  font-variant-numeric:tabular-nums; }
.note { background:var(--panel); border:1px solid var(--line);
  border-left:3px solid var(--yel); border-radius:8px; padding:12px 16px;
  color:var(--mut); font-size:14px; margin:16px 0; }
code { background:#232830; border-radius:4px; padding:1px 6px; font-size:13px; }
.grad { height:10px; border-radius:5px; margin:6px 0 2px;
  background:linear-gradient(90deg, hsl(175 90% 62%), hsl(247 90% 62%), hsl(320 90% 62%)); }
</style>
<div class="wrap">
<h1>WIRING &amp; WLED MAPPING</h1>
<p class="sub">Physical data chains for both signs, drawn <b>as seen from BEHIND</b>
(that's your view while wiring — front views included small for orientation). Chain
color runs start-to-end along this gradient:</p>
<div class="grad"></div>
<p class="cap">DATA IN → END &nbsp;·&nbsp; dashed yellow links = longer than the 101.6&nbsp;mm
(4-inch) string → cut + splice an extension &nbsp;·&nbsp; numbers = chain index (every 10th)</p>

<h2>Bolt board — 137 px, one chain</h2>
<div class="stats">
  <div class="stat"><b>{{BRUN}} m</b><span>total run</span></div>
  <div class="stat"><b>{{BEXT}}</b><span>extensions needed</span></div>
  <div class="stat"><b>{{BMAX}} mm</b><span>longest link</span></div>
  <div class="stat"><b>{{BSEGN}}</b><span>WLED segments (Y base + red rects)</span></div>
</div>
<h3>Back view — wire it from this</h3>
<div class="wide">{{BOARD_BACK}}</div>
<h3>Front view (orientation)</h3>
<div class="wide front">{{BOARD_FRONT}}</div>
<h3>Cut &amp; extend list</h3>
<div style="overflow-x:auto"><table>
<tr><th>chain link</th><th>from → to (front coords, mm)</th><th>straight run</th><th>action</th></tr>
{{BOARD_EXT}}
</table></div>
<div class="note">The two extensions are exactly the yellow→red→red→yellow zone hops
(the red inner is its own shape). Every other link folds its ~85&nbsp;mm slack into the plenum.</div>
<h3>Color zones (chain order — physical reference)</h3>
<div style="overflow-x:auto"><table>
<tr><th>zone</th><th>chain range</th><th>count</th><th>suggested color</th></tr>
{{BOARD_SEG}}
</table></div>

<h2>CHARGE word — {{WPX}} px, one chain, letters C → E</h2>
<div class="stats">
  <div class="stat"><b>{{WRUN}} m</b><span>total run</span></div>
  <div class="stat"><b>{{WEXT}}</b><span>extensions needed</span></div>
  <div class="stat"><b>{{WMAX}} mm</b><span>longest link</span></div>
  <div class="stat"><b>6</b><span>WLED segments (letters)</span></div>
</div>
<h3>Back view — wire it from this (letters read reversed: E … C)</h3>
<div class="wide">{{WORD_BACK}}</div>
<h3>Front view (orientation)</h3>
<div class="wide">{{WORD_FRONT}}</div>
<h3>Cut &amp; extend list</h3>
<div style="overflow-x:auto"><table>
<tr><th>chain link</th><th>from → to (front coords, mm)</th><th>straight run</th><th>action</th></tr>
{{WORD_EXT}}
</table></div>
<h3>Letter runs (chain order — physical reference)</h3>
<div style="overflow-x:auto"><table>
<tr><th>letter</th><th>chain range</th><th>count</th><th>suggested color</th></tr>
{{WORD_SEG}}
</table></div>
<div class="note">The word chain order is now PERSISTED in
<code>src/parts/word_pixmap.json</code> — wire to it and every mapping stays true.
Chain runs each tube end-to-end, nearest-end hops between tubes, letters strictly
left→right (C first, nearest the controller/PSU side).</div>

<h2>WLED setup (verified against WLED 16.x)</h2>
<ol style="padding-left:22px">
<li><b>Use 16.0.1 or newer</b> — 16.0.1 fixed a ledmap parser bounds bug
(reading past the end of the map array).</li>
<li>Two controllers (or two outputs): board GPIO → 137 px, word GPIO → {{WPX}} px.</li>
<li>Upload each map to the controller's filesystem at <code>/edit</code>, renamed to
<code>ledmap.json</code>: <code>wled/board-controller/ledmap.json</code> — {{BGRID}} grid,
<code>wled/word-controller/ledmap.json</code> — {{WGRID}} grid; 10&nbsp;mm cells, −1 = empty
cell. On reboot the map's <code>"width"/"height"</code> switch the controller into 2D
matrix mode by itself (16.x <code>deserializeMap</code> sets the dims at boot) — 2D effects
(plasma, Matrix, DNA…) then render in true sign space. Check Info shows the grid size.
<b>Never pretty-print these files</b>: 16.x streams the map with a byte-exact
<code>"map":[</code> search — <code>"map": [</code> (space) silently loads zero entries
and the sign renders as if the chain were crammed into the top rows.</li>
<li><b>No Config → 2D Configuration needed, and no <code>2d-gaps.json</code></b> — gap
files only patch panel-scan matrices and WLED ignores them whenever a custom ledmap
exists. If the sign ever boots as a single line of pixels, open 2D Configuration and
hit Save once (0.15-era quirk, issue #5082) — the ledmap re-wins on next boot.</li>
<li><b>Segments become RECTANGLES once the map loads</b>: <code>start/stop</code> = column
range, <code>startY/stopY</code> = row range (stops exclusive), origin top-left. Chain-index
segments (e.g. 87–107) would be read as columns — off-grid starts collapse to
overlapping full-width strips, which looks like a few random cells lit. The shipped
presets are rect stacks: bolt = full-grid yellow base + {{BREDN}} red rectangles painted
over it (v16 composites segments in id order, blend "top"); word = one column band per
letter, cut at columns {{WCUTS}}. {{WSTRAY}} seam cells sit in the neighbor's band —
invisible while all letters run one color. Upload each as <code>presets.json</code> at
<code>/edit</code> (replaces all presets), or merge via Presets backup/restore. Trailing
<code>{"stop":0}</code> entries clear any leftover segments from earlier experiments.</li>
<li>Colors are software — the bolt's red zone is chain 87–107 no matter what's playing.</li>
</ol>
</div>
"""
bm = ledmap(board, "", FW, FH)
wm = ledmap(word, "", wx1 - wx0, W["face_h"], ox=wx0, oy=wy0)
for k, v in {
    "{{BOARD_BACK}}": chain_svg(board, bpaths, FW, FH, 0, 0, True, 22),
    "{{BOARD_FRONT}}": chain_svg(board, bpaths, FW, FH, 0, 0, False, 22, 999),
    "{{WORD_BACK}}": chain_svg(word, wpaths, wx1 - wx0, W["face_h"], wx0, wy0, True, wtube),
    "{{WORD_FRONT}}": chain_svg(word, wpaths, wx1 - wx0, W["face_h"], wx0, wy0, False, wtube, 999),
    "{{BOARD_EXT}}": ext_rows(board, bext),
    "{{WORD_EXT}}": ext_rows(word, wext),
    "{{BOARD_SEG}}": seg_rows([(c, a, b) for c, a, b in bruns],
                              lambda n: "255,190,30 (amber)" if n == "yellow" else "255,40,20 (red)"),
    "{{WORD_SEG}}": seg_rows([(L, a, b) for L, a, b in lruns],
                             lambda n: "235,245,255 (white)"),
    "{{BRUN}}": "%.1f" % (sum(blinks) / 1000), "{{WRUN}}": "%.1f" % (sum(wlinks) / 1000),
    "{{BEXT}}": str(len(bext)), "{{WEXT}}": str(len(wext)),
    "{{BMAX}}": "%.0f" % max(blinks), "{{WMAX}}": "%.0f" % max(wlinks),
    "{{WPX}}": str(len(word)),
    "{{BGRID}}": "%d×%d" % (bm["width"], bm["height"]),
    "{{WGRID}}": "%d×%d" % (wm["width"], wm["height"]),
    "{{BSEGN}}": str(len(bsegs)),
    "{{BREDN}}": str(len(bsegs) - 1),
    "{{WCUTS}}": "/".join(str(k) for k in cuts[1:-1]),
    "{{WSTRAY}}": str(len(stray)),
}.items():
    html = html.replace(k, v)
open("docs/sign-preview/wiring.html", "w").write(html)
print("word chain: %d px, run %.1fm, %d extensions (max link %.0fmm)"
      % (len(word), sum(wlinks) / 1000, len(wext), max(wlinks)))
print("board chain: %d px, run %.1fm, %d extensions (max link %.0fmm)"
      % (len(board), sum(blinks) / 1000, len(bext), max(blinks)))
print("wrote wiring.html + word_pixmap.json + wled/{word,board}-controller/{ledmap,presets}.json")
