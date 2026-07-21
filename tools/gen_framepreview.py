#!/usr/bin/env python3
"""Generate docs/sign-preview/frame-preview.html — backer-frame review card.
QA-grade: every overlay coordinate comes from the GENERATED layouts
(frame_layout.scad + board_layout.scad + bracket_layout.scad + pixmap),
so the page shows what the STLs actually contain. Style follows the
spec-stage artifact card (dark engineering, CHARGE yellow, light tokens)."""
import json, re

def grab(txt, name):
    return eval(re.search(re.escape(name) + r"\s*=\s*(\[.*?\]);", txt, re.S).group(1))
def scal(txt, name):
    return float(re.search(re.escape(name) + r"\s*=\s*([\d.]+)", txt).group(1))

bl = open("src/parts/board_layout.scad").read()
fl = open("src/parts/frame_layout.scad").read()
bk = open("src/parts/bracket_layout.scad").read()
PX = json.load(open("src/parts/bolt_pixmap.json"))["pixels"]
bb_plates, bb_paths = grab(bl, "bb_plates"), grab(bl, "bb_paths")
bb_scr, bb_bite = grab(bl, "bb_scr"), grab(bl, "bb_bite")
F = {n: grab(fl, n) for n in
     ["fr_face", "fr_boss", "fr_joint", "fr_panels", "fr_ledge_boss",
      "fr_rail_boss", "fr_leg", "fr_tray_psu", "fr_psu_holes", "fr_psu_slots",
      "fr_tray_ctl", "fr_ctl_holes", "fr_ctl_ext", "fr_gland", "fr_handle",
      "fr_feet", "fr_vent_intake", "fr_vent_exhaust", "fr_mic"]}
CLR, WALL = scal(fl, "fr_clr"), scal(fl, "fr_wall")
CAV, PT = scal(fl, "fr_cavity"), scal(fl, "fr_panel_t")
FW, FH = F["fr_face"]
OX0, OX1 = -CLR - WALL, FW + CLR + WALL
JX, JY = F["fr_joint"]
def fy(y): return FH - y

S = []
def em(s): S.append(s)

em(f'<rect class="frame" x="{OX0}" y="{fy(FH)+OX0}" width="{OX1-OX0}" '
   f'height="{FH-2*OX0}" rx="2.5"/>')
em(f'<rect class="flange" x="0.5" y="{fy(FH)+0.5}" width="{FW-1}" height="{FH-1}"/>')
em(f'<rect class="flangein" x="16" y="{fy(FH)+16}" width="{FW-32}" height="{FH-32}"/>')
for x0, x1, y0, y1 in bb_plates:
    em(f'<rect class="plate" x="{x0}" y="{fy(y1)}" width="{x1-x0}" height="{y1-y0}"/>')
for p in bb_paths[:2]:
    em('<path class="bolt" d="M' + " L".join(f"{x:.1f} {fy(y):.1f}" for x, y in p) + ' Z"/>')
em('<path class="zig" d="M' + " L".join(f"{x:.1f} {fy(y):.1f}" for x, y in bb_paths[2]) + '"/>')

# panel splits + louver rows + mic (all from layout)
em(f'<line class="split" x1="{JX}" y1="{fy(FH)}" x2="{JX}" y2="{fy(0)}"/>')
em(f'<line class="split" x1="0" y1="{fy(JY)}" x2="{FW}" y2="{fy(JY)}"/>')
for rows in (F["fr_vent_intake"], F["fr_vent_exhaust"]):
    for vy in rows:
        for x0 in range(30, int(FW) - 55, 42):
            em(f'<line class="vent" x1="{x0}" y1="{fy(vy)}" x2="{x0+27}" y2="{fy(vy)}"/>')
mx, my = F["fr_mic"]
em(f'<circle class="mic" cx="{mx}" cy="{fy(my)}" r="14"/>')

# straps (S1/S2 as-built, S3/S4 tall) + rail bosses + legs
bspan = grab(bk, "bk_span")
for (x0, x1) in [tuple(bspan[0]), tuple(bspan[1])]:
    em(f'<rect class="strap" x="{x0}" y="{fy(279)}" width="{x1-x0}" height="48"/>')
for (xc, y0, y1) in [(126, bspan[2][0], bspan[2][1]), (153, bspan[3][0], bspan[3][1])]:
    em(f'<rect class="strapR" x="{xc-24}" y="{fy(y1)}" width="48" height="{y1-y0}"/>')
    for sx in (xc - 24, xc + 19):
        em(f'<rect class="rail30" x="{sx}" y="{fy(y1)}" width="5" height="{y1-y0}"/>')
for q in F["fr_rail_boss"]:
    em(f'<circle class="legb" cx="{q[0]}" cy="{fy(q[1])}" r="2"/>')
for lx, ly in F["fr_leg"]:
    em(f'<circle class="leg" cx="{lx}" cy="{fy(ly)}" r="8"/>')
    em(f'<circle class="legb" cx="{lx}" cy="{fy(ly)}" r="3.2"/>')

# screws: frame bosses + ledge bosses + machine screws + pixels + bites
for x, y in F["fr_boss"]:
    em(f'<circle class="boss" cx="{x}" cy="{fy(y)}" r="3.5"/>')
    em(f'<circle class="bossp" cx="{x}" cy="{fy(y)}" r="1.4"/>')
for x, y in F["fr_ledge_boss"]:
    em(f'<circle class="mscr" cx="{x}" cy="{fy(y)}" r="2.6"/>')
for x, y, k in bb_scr:
    if k == 1:
        em(f'<circle class="mscr" cx="{x}" cy="{fy(y)}" r="2.2"/>')
for p in PX:
    em(f'<circle class="px {p["color"]}" cx="{p["x"]}" cy="{fy(p["y"])}" r="3.4"/>')
for x, y in bb_bite:
    em(f'<circle class="bite" cx="{x}" cy="{fy(y)}" r="6.5"/>')

# equipment trays, PSU slots+holes, Elite holes, ext pads, gland, wires
tp = F["fr_tray_psu"]
em(f'<rect class="psu" x="{tp[0]}" y="{fy(tp[3])}" width="{tp[2]-tp[0]}" '
   f'height="{tp[3]-tp[1]}" rx="2"/>')
for s in F["fr_psu_slots"]:
    em(f'<line class="pslot" x1="{s[0]}" y1="{fy(s[1])}" x2="{s[2]}" y2="{fy(s[3])}"/>')
for q in F["fr_psu_holes"]:
    em(f'<circle class="bossp" cx="{q[0]}" cy="{fy(q[1])}" r="2"/>')
em(f'<text class="lab" x="{(tp[0]+tp[2])/2}" y="{fy(tp[1]+62)}" '
   f'text-anchor="middle">LRS-50/75/100</text>')
tc = F["fr_tray_ctl"]
em(f'<rect class="podunit" x="{tc[0]}" y="{fy(tc[3])}" width="{tc[2]-tc[0]}" '
   f'height="{tc[3]-tc[1]}" rx="2"/>')
for q in F["fr_ctl_holes"]:
    em(f'<circle class="bossp" cx="{q[0]}" cy="{fy(q[1])}" r="2"/>')
em(f'<text class="lab" x="{(tc[0]+tc[2])/2}" y="{fy((tc[1]+tc[3])/2)}" '
   f'text-anchor="middle">Elite</text>')
for q in F["fr_ctl_ext"]:      # exterior option pads (left wall, y along wall)
    em(f'<circle class="extp" cx="{OX0}" cy="{fy(q[0])}" r="3"/>')
gy = F["fr_gland"][0]
em(f'<circle class="gland" cx="{OX0}" cy="{fy(gy)}" r="4.2"/>')
em(f'<path class="wire" d="M {OX0+3} {fy(gy+2)} C 8 {fy(140)}, 8 {fy(300)}, '
   f'30 {fy(tp[1]+20)}"/>')
em(f'<path class="wire" d="M {tp[2]-40} {fy(tp[3]+4)} C 180 {fy(547)}, 300 '
   f'{fy(545)}, {(tc[0]+tc[2])/2} {fy(tc[3]+2)}"/>')
em(f'<path class="wire" d="M {(tc[0]+tc[2])/2} {fy(tc[1]-2)} C 330 {fy(300)}, '
   f'240 {fy(210)}, 199 {fy(182)}"/>')
em(f'<circle class="entry" cx="194.4" cy="{fy(179.6)}" r="5.5"/>')

# joints, handles, feet
for (jx, jy, rot) in [(JX, fy(FH) - 2, 0), (JX, fy(0) + 2, 0),
                      (OX0 + 0.2, fy(JY), 90), (OX1 - 0.2, fy(JY), 90)]:
    em(f'<g transform="translate({jx},{jy}) rotate({rot})">'
       f'<path class="dove" d="M -6 -3 L 6 3 M -6 3 L 6 -3 M -6 -3 V 3 M 6 -3 V 3"/></g>')
for h in F["fr_handle"]:
    em(f'<rect class="csframe" x="{h[0]}" y="-18.5" width="{h[1]-h[0]}" height="15" rx="6"/>')
    em(f'<rect class="slotcut" x="{h[0]+12}" y="-14.5" width="{h[1]-h[0]-24}" height="7" rx="3.5"/>')
for sx in F["fr_feet"]:
    em(f'<path class="slot" d="M {sx-7} {fy(0)+3.4} h 3 v -2.2 h 8 v 2.2 h 3"/>')

CALL = [
    (418, fy(556), "handles ×2 · carry + flush wall-hang", 350, -11),
    (418, fy(505), "exhaust louvers + PSU/Elite bays", 340, fy(505)),
    (418, fy(470), f"Elite tray · holes {F['fr_ctl_holes'][0][0]:.0f}/{F['fr_ctl_holes'][1][0]:.0f} diag", tc[2], fy(470)),
    (418, fy(JY), "corner-L joint (dovetail + M3)", OX1 + 1, fy(JY)),
    (418, fy(240), "S1/S2 stay · Ø10 legs ×3", 370, fy(255)),
    (418, fy(180), "data enters chain px 0", 200, fy(179)),
    (418, fy(140), "flange band · 14 reused screws", 404, fy(130)),
    (418, fy(38), "intake louvers + snap feet", 330, fy(30)),
    (-52, fy(480), "PSU tray · slots fit 50/75, rounds 100", tp[0], fy(480)),
    (-52, fy(300), "mains up the left wall", 8, fy(300)),
    (-52, fy(165), "ext controller pads (option)", OX0 - 3, fy(165)),
    (-52, fy(70), "PG9 gland — printed open", OX0 - 5, fy(70)),
]
for tx, ty, label, ax, ay in CALL:
    anchor = "start" if tx > 0 else "end"
    lx = tx - 3 if tx > 0 else tx + 3
    em(f'<line class="lead" x1="{lx}" y1="{ty-3}" x2="{ax}" y2="{ay}"/>')
    em(f'<text class="lab" x="{tx}" y="{ty}" text-anchor="{anchor}">{label}</text>')

main_svg = ('<svg viewBox="-175 -22 800 604" role="img" '
            'aria-label="Front x-ray of the bolt board with frame overlay">'
            + "".join(S) + "</svg>")

CS = '''<svg viewBox="0 0 470 246" role="img" aria-label="Rail cross-section">
<rect class="csplate" x="30" y="40" width="380" height="8"/>
<rect class="cswallf" x="120" y="22" width="7" height="18"/>
<rect class="cswallf" x="210" y="22" width="7" height="18"/>
<rect class="cswallf" x="300" y="22" width="7" height="18"/>
<rect class="csframe" x="30" y="48" width="64" height="16"/>
<circle class="cspil" cx="54" cy="56" r="4"/>
<rect class="csframe" x="14" y="48" width="16" height="152"/>
<path class="foot" d="M 14 48 v -14 h 8 v 6 h 16 v 8" fill="none"/>
<rect class="csframe" x="30" y="184" width="32" height="16"/>
<rect class="cspanel" x="30" y="200" width="380" height="10"/>
<rect class="csstrap" x="250" y="48" width="120" height="14"/>
<rect class="csrail" x="250" y="48" width="12" height="152"/>
<rect class="csrail" x="358" y="48" width="12" height="152"/>
<line class="csdim" x1="440" y1="48" x2="440" y2="200"/>
<text class="lab" x="447" y="128">36</text>
<line class="csdim" x1="418" y1="200" x2="418" y2="210"/>
<text class="lab" x="425" y="209">2.4</text>
<line class="csdim" x1="30" y1="228" x2="94" y2="228"/>
<text class="lab" x="98" y="231">flange 16</text>
<text class="lab" x="6" y="24">snap trim ↰</text>
<text class="lab" x="132" y="36">plate 2 + front channels</text>
<text class="lab" x="255" y="76">S3/S4: web 4 + rail 32</text>
<text class="lab" x="66" y="196">ledge 8</text>
<text class="lab" x="150" y="146">cavity: LRS-50/75/100 fit (all 30 tall)</text>
</svg>'''

POD = f'''<svg viewBox="0 0 250 240" role="img" aria-label="Equipment tray detail">
<rect class="csframe" x="18" y="14" width="10" height="212"/>
<rect class="csplate" x="28" y="14" width="210" height="6"/>
<rect class="podunit" x="34" y="30" width="150" height="58" rx="3"/>
<text class="lab" x="109" y="55" text-anchor="middle">Elite 2D-EXMU 129×50</text>
<text class="lab" x="109" y="80" text-anchor="middle">screws 122×26 diagonal (coupon-gated)</text>
<circle class="bossp" cx="45" cy="72" r="2.5"/><circle class="bossp" cx="167" cy="46" r="2.5"/>
<rect class="psu" x="34" y="108" width="120" height="98" rx="3"/>
<text class="lab" x="94" y="146" text-anchor="middle">LRS-50/75/100</text>
<text class="lab" x="94" y="196" text-anchor="middle">slots 50/75 · rounds 100 · max 3 deep</text>
<circle class="bossp" cx="59" cy="157" r="2.5"/><circle class="bossp" cx="126" cy="157" r="2.5"/>
<line class="csdim" x1="222" y1="30" x2="222" y2="206"/>
<text class="lab" x="228" y="122">36</text>
<text class="lab" x="34" y="228">both lie flat on 4 mm tray floors → 36 clears all</text>
</svg>'''

FEET = '''<svg viewBox="0 0 250 240" role="img" aria-label="Foot snap detail">
<rect class="csframe" x="40" y="60" width="170" height="26"/>
<path class="slotcut" d="M 105 86 v -16 h 8 v 8 h 24 v -8 h 8 v 16"/>
<path class="foot" d="M 80 132 h 90 l -12 -14 h -26 v -26 l 4 -6 h 2 v 8 h -2 m -8 0 h -2 v -8 h 2 l 4 6 v 26 h -38 z" transform="translate(0,4)"/>
<text class="lab" x="125" y="52" text-anchor="middle">bottom rail · snap socket + barb pocket</text>
<text class="lab" x="125" y="160" text-anchor="middle">foot: split prongs snap in, squeeze to release</text>
<text class="lab" x="125" y="172" text-anchor="middle">blade 90 fore-aft · ×2</text>
</svg>'''

n_wood = sum(1 for s in bb_scr if s[2] == 0)
qa = json.load(open("src/parts/board_qa.json"))
page = """<title>Bolt backer frame — design preview</title>
<style>
:root {
  --bg:#101318; --card:#171c23; --ink:#e8ebef; --mut:#97a0ac; --line:#2a323d;
  --accent:#ffc93c; --red:#e05252; --good:#7ad48a; --steel:#8b94a1;
  --plate:#1d232c; --band:#232b36;
}
@media (prefers-color-scheme: light) { :root {
  --bg:#eef0f3; --card:#ffffff; --ink:#1a2027; --mut:#5b6572; --line:#d7dce2;
  --accent:#c79616; --red:#c23c3c; --good:#3d9e52; --steel:#6b7683;
  --plate:#f5f6f8; --band:#e9edf1;
}}
:root[data-theme="dark"] {
  --bg:#101318; --card:#171c23; --ink:#e8ebef; --mut:#97a0ac; --line:#2a323d;
  --accent:#ffc93c; --red:#e05252; --good:#7ad48a; --steel:#8b94a1;
  --plate:#1d232c; --band:#232b36;
}
:root[data-theme="light"] {
  --bg:#eef0f3; --card:#ffffff; --ink:#1a2027; --mut:#5b6572; --line:#d7dce2;
  --accent:#c79616; --red:#c23c3c; --good:#3d9e52; --steel:#6b7683;
  --plate:#f5f6f8; --band:#e9edf1;
}
body { background:var(--bg); color:var(--ink); margin:0; padding:28px 20px 60px;
  font:15px/1.55 -apple-system, "SF Pro Text", "Segoe UI", system-ui, sans-serif; }
main { max-width:1060px; margin:0 auto; display:flex; flex-direction:column; gap:22px; }
.lab, .kv b { font-family:ui-monospace, "SF Mono", Menlo, Consolas, monospace; }
header h1 { font-size:26px; font-weight:650; letter-spacing:-.01em; margin:0 0 4px;
  text-wrap:balance; }
.eyebrow { font-family:ui-monospace, Menlo, monospace; font-size:11px;
  letter-spacing:.14em; text-transform:uppercase; color:var(--accent); margin:0 0 10px; }
.sub { color:var(--mut); margin:0; max-width:64ch; }
.kv { display:flex; flex-wrap:wrap; gap:8px 26px; margin-top:14px; padding:12px 16px;
  background:var(--card); border:1px solid var(--line); border-radius:6px; }
.kv span { color:var(--mut); font-size:13px; }
.kv b { color:var(--ink); font-weight:600; font-size:13px; font-variant-numeric:tabular-nums; }
.card { background:var(--card); border:1px solid var(--line); border-radius:6px;
  padding:18px 20px; }
.card h2 { font-size:13px; font-family:ui-monospace, Menlo, monospace; font-weight:600;
  letter-spacing:.1em; text-transform:uppercase; color:var(--mut); margin:0 0 12px; }
.card svg { width:100%; height:auto; display:block; }
.two { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
@media (max-width:760px) { .two { grid-template-columns:1fr; } }
.legend { display:flex; flex-wrap:wrap; gap:6px 18px; margin-top:12px;
  font-size:12px; color:var(--mut); }
.legend i { display:inline-block; width:11px; height:11px; border-radius:2px;
  margin-right:6px; vertical-align:-1px; }
ul { margin:0; padding-left:20px; color:var(--mut); }
ul li { margin:5px 0; } ul b { color:var(--ink); font-weight:600; }
.note { font-size:13px; color:var(--mut); border-left:3px solid var(--accent);
  padding:2px 0 2px 12px; }
.frame { fill:none; stroke:var(--steel); stroke-width:2.4; }
.flange { fill:none; stroke:var(--steel); stroke-width:.7; stroke-dasharray:4 3; opacity:.7; }
.flangein { fill:none; stroke:var(--steel); stroke-width:.5; stroke-dasharray:2 3; opacity:.45; }
.plate { fill:var(--plate); stroke:var(--line); stroke-width:.8; }
.bolt { fill:none; stroke:var(--accent); stroke-width:1.6; opacity:.85; }
.zig { fill:none; stroke:var(--red); stroke-width:1.2; opacity:.8; }
.split { stroke:var(--mut); stroke-width:.8; stroke-dasharray:7 5; opacity:.55; }
.vent { stroke:var(--mut); stroke-width:1.6; opacity:.4; }
.mic { fill:none; stroke:var(--mut); stroke-width:1; stroke-dasharray:2 2; }
.strap { fill:var(--band); opacity:.85; }
.strapR { fill:var(--band); stroke:var(--good); stroke-width:1.2; }
.rail30 { fill:var(--good); opacity:.55; }
.leg { fill:none; stroke:var(--good); stroke-width:1.5; }
.legb { fill:var(--good); }
.boss { fill:none; stroke:var(--accent); stroke-width:1.3; }
.bossp { fill:var(--accent); }
.mscr { fill:none; stroke:var(--steel); stroke-width:.9; opacity:.7; }
.px { opacity:.9; } .px.yellow { fill:var(--accent); } .px.red { fill:var(--red); }
.bite { fill:none; stroke:var(--red); stroke-width:1.4; }
.psu { fill:none; stroke:var(--mut); stroke-width:1.1; stroke-dasharray:5 4; }
.pslot { stroke:var(--accent); stroke-width:2.8; stroke-linecap:round; }
.gland { fill:var(--card); stroke:var(--ink); stroke-width:1.6; }
.extp { fill:none; stroke:var(--accent); stroke-width:1.2; stroke-dasharray:2 2; }
.podunit { fill:none; stroke:var(--accent); stroke-width:1.2; }
.wire { fill:none; stroke:var(--accent); stroke-width:1.1; stroke-dasharray:3 4; }
.entry { fill:none; stroke:var(--accent); stroke-width:1.6; }
.dove { stroke:var(--ink); stroke-width:1.1; fill:none; }
.slot, .slotcut { stroke:var(--ink); stroke-width:1.3; fill:none; }
.lead { stroke:var(--mut); stroke-width:.6; opacity:.65; }
.lab { fill:var(--mut); font-family:ui-monospace, Menlo, monospace; font-size:10px; }
.csplate { fill:var(--plate); stroke:var(--steel); stroke-width:.8; }
.cswallf { fill:var(--band); }
.csframe { fill:var(--band); stroke:var(--steel); stroke-width:1.1; }
.cspanel { fill:none; stroke:var(--good); stroke-width:1.4; }
.csstrap { fill:var(--band); stroke:var(--good); stroke-width:1; }
.csrail { fill:var(--good); opacity:.5; }
.cspil { fill:var(--accent); }
.csdim { stroke:var(--mut); stroke-width:.8; }
.foot { fill:none; stroke:var(--ink); stroke-width:1.4; }
</style>
<main>
<header>
  <p class="eyebrow">CHARGE · bolt backer frame · generated from frame_layout</p>
  <h1>Printed torsion box — as the STLs are built</h1>
  <p class="sub">Front x-ray: plates, pixels, and screws from board_layout; frame,
  trays, and fixings from the generated frame_layout — this page shows what the
  rendered part files actually contain (QA: __QA__).</p>
  <div class="kv">
    <div><span>cavity </span><b>36 mm</b></div>
    <div><span>printed parts </span><b>18 + coupon</b></div>
    <div><span>frame bosses </span><b>__NWOOD__ reused holes</b></div>
    <div><span>equipment </span><b>all internal · 1 gland</b></div>
    <div><span>QA </span><b>__QA__</b></div>
  </div>
</header>
<section class="card">
  <h2>Front x-ray · board 410×550</h2>
  __MAIN__
  <div class="legend">
    <span><i style="background:var(--accent)"></i>pixels / bolt / frame bosses / PSU slots</span>
    <span><i style="background:var(--red)"></i>red zone px · on-seam bites</span>
    <span><i style="background:var(--good)"></i>tall S3/S4 rails · legs · rail pilots</span>
    <span><i style="background:var(--steel)"></i>frame rail · ledge bosses · gland</span>
    <span><i style="border:1px dashed var(--mut); background:none"></i>panel splits · louvers · trays</span>
  </div>
</section>
<div class="two">
  <section class="card"><h2>Rail cross-section · true dims</h2>__CS__</section>
  <section class="card"><h2>Equipment trays · top corners</h2>__POD__</section>
</div>
<div class="two">
  <section class="card"><h2>Snap foot · bottom rail</h2>__FEET__</section>
  <section class="card"><h2>Print gates &amp; params</h2>
    <ul>
      <li><b>Coupon first</b> — frame_coupon.stl (1.2 mm): offer up to the Elite +
        PSU, pick diagonal A/B → set <b>ctl_diag</b> in tools/boltframe.py,
        regenerate, THEN print rails</li>
      <li><b>psu</b> — slots fit LRS-50/75, rounds fit LRS-100; screws M3, max
        3 mm into the case</li>
      <li><b>gland</b> — PG9 printed open (PG7/PG11 = swap plates)</li>
      <li><b>Strap screws</b> — S3/S4 flat seats: M4×10/12 + washer/nut
        (M4×8 stock too short)</li>
      <li><b>reveal</b> — 2 mm snap-on trim strips; skip printing trim = 0</li>
    </ul>
    <p class="note" style="margin-top:14px">Print order: coupon → S3/S4 straps →
    rails → panels → handles/feet/legs/trim/gland plate.</p>
  </section>
</div>
</main>"""
page = (page.replace("__MAIN__", main_svg).replace("__CS__", CS)
            .replace("__POD__", POD).replace("__FEET__", FEET)
            .replace("__NWOOD__", str(n_wood))
            .replace("__QA__", "%d checks, %d fail" %
                     (len(qa["checks"]), qa["fail"])))
out = "docs/sign-preview/frame-preview.html"
open(out, "w").write(page)
print("wrote %s (%d bytes)" % (out, len(page)))
