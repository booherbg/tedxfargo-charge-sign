#!/usr/bin/env python3
"""Generate docs/sign-preview/index.html — the publishable story of the CHARGE
sign build: brief -> optics -> font forensics -> bolt -> seam straps -> wiring,
with the real diagrams embedded from the generated preview pages, plus a brief
on the generic spin-off (signforge). Run AFTER gen_systempreview.py,
gen_bracketpreview.py and gen_wiring.py so the source SVGs exist."""
import re

def svgs(path, min_w=380):
    """big diagram SVGs from a generated page, in document order"""
    out = []
    for m in re.finditer(r"<svg viewBox=\"[^\"]*?[- ]([\d.]+) ([\d.]+)\"[^>]*>.*?</svg>",
                         open(path).read(), re.S):
        if float(m.group(1)) >= min_w:
            out.append(m.group(0))
    return out

sysv = svgs("docs/sign-preview/system-preview.html")     # [hero, map]
brk = svgs("docs/sign-preview/bracket-preview.html")     # [before, after, overlay, straps...]
wir = svgs("docs/sign-preview/wiring.html")              # [board back, board front, word back, word front]

HERO, SYSMAP = sysv[0], sysv[1]
BEFORE, AFTER, OVERLAY = brk[0], brk[1], brk[2]
BOARD_BACK, WORD_BACK = wir[0], wir[2]

html = r"""<title>CHARGE — a 3D-printed neon sign, from billboard to bulletproof</title>
<style>
:root {
  --bg:#0e1014; --panel:#171b21; --line:#2a303a; --ink:#e9e5db; --mut:#8f98a5;
  --cyan:#9fd8ff; --yel:#ffc93c; --red:#ff5340; --ok:#7ad48a; --wood:#a9855c;
}
html { background:var(--bg); scroll-behavior:smooth; }
body { margin:0; color:var(--ink); background:var(--bg);
  font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.mono { font-family:ui-monospace,Menlo,Consolas,monospace; }
.wrap { max-width:880px; margin:0 auto; padding:0 22px; }
.wide { max-width:1120px; margin:26px auto; padding:0 22px; }
.wide svg { width:100%; height:auto; display:block; border-radius:12px; }

/* hero */
header { padding:84px 0 30px; text-align:center; }
.neon { font-family:ui-monospace,Menlo,Consolas,monospace; font-weight:800;
  font-size:clamp(52px,11vw,124px); letter-spacing:.06em; margin:0; line-height:1;
  color:#dff4ff;
  text-shadow:0 0 6px #bfe9ff, 0 0 18px #7cc7ff, 0 0 42px #2e9fff, 0 0 80px #1272c8; }
.neon .bolt { color:#ffe08a;
  text-shadow:0 0 6px #ffd34d, 0 0 18px #ffb320, 0 0 42px #ff8c00, 0 0 80px #b35300; }
@keyframes flick { 0%,92%,96%,100% {opacity:1} 93%,95% {opacity:.35} }
.neon .fl { animation:flick 7s infinite; }
@media (prefers-reduced-motion:reduce) { .neon .fl { animation:none; } }
.tagline { color:var(--mut); font-size:17px; max-width:62ch; margin:22px auto 0;
  text-wrap:balance; }
.stats { display:flex; flex-wrap:wrap; gap:10px; justify-content:center;
  margin:34px 0 10px; }
.stat { background:var(--panel); border:1px solid var(--line); border-radius:8px;
  padding:9px 16px; text-align:left; }
.stat b { display:block; font-size:20px; font-variant-numeric:tabular-nums;
  font-family:ui-monospace,Menlo,monospace; }
.stat span { color:var(--mut); font-size:11.5px; letter-spacing:.07em;
  text-transform:uppercase; }

/* chapters */
.stamp { font-family:ui-monospace,Menlo,monospace; font-size:12.5px; color:var(--yel);
  letter-spacing:.16em; text-transform:uppercase; margin:74px 0 6px; }
.stamp:before { content:"▮ "; color:var(--red); }
h2 { font-size:30px; margin:0 0 14px; letter-spacing:-.01em; text-wrap:balance; }
p { max-width:68ch; margin:0 0 16px; }
p b { color:#fff; }
.cap { font-family:ui-monospace,Menlo,monospace; font-size:12.5px; color:var(--mut);
  letter-spacing:.06em; text-transform:uppercase; margin:10px auto 0; max-width:1076px;
  padding:0 0; }
.fail { border-left:3px solid var(--red); background:var(--panel); border-radius:0 8px 8px 0;
  padding:12px 18px; margin:18px 0; color:var(--mut); font-size:15px; max-width:62ch; }
.fail b { color:var(--red); font-family:ui-monospace,Menlo,monospace; font-size:12px;
  letter-spacing:.12em; text-transform:uppercase; display:block; margin-bottom:4px; }
.rule { border-left:3px solid var(--ok); background:var(--panel); border-radius:0 8px 8px 0;
  padding:12px 18px; margin:18px 0; font-size:15px; max-width:62ch; }
.rule b { color:var(--ok); font-family:ui-monospace,Menlo,monospace; font-size:12px;
  letter-spacing:.12em; text-transform:uppercase; display:block; margin-bottom:4px; }
.duo { display:flex; flex-wrap:wrap; gap:16px; max-width:1120px; margin:26px auto;
  padding:0 22px; }
.duo > div { flex:1 1 340px; }
.duo svg { width:100%; height:auto; display:block; border-radius:12px; }
.duo .lab { font-family:ui-monospace,Menlo,monospace; font-size:12px; color:var(--mut);
  letter-spacing:.1em; text-transform:uppercase; margin:0 0 8px; }
code { background:#232830; border-radius:4px; padding:1px 6px; font-size:14px;
  font-family:ui-monospace,Menlo,monospace; }
a { color:var(--cyan); }
.sf { background:linear-gradient(180deg,#181c23,#14171d); border:1px solid var(--line);
  border-radius:14px; padding:28px 30px; margin:30px 0; }
.sf h3 { font-family:ui-monospace,Menlo,monospace; font-size:22px; margin:0 0 12px;
  color:var(--yel); letter-spacing:.03em; }
.sf ul { margin:12px 0 0; padding-left:20px; color:var(--mut); }
.sf li { margin:6px 0; }
.sf li::marker { color:var(--yel); }
footer { border-top:1px solid var(--line); margin-top:90px; padding:34px 0 70px;
  color:var(--mut); font-size:14px; }
footer .links { display:flex; flex-wrap:wrap; gap:18px; margin-top:10px; }
</style>

<header class="wrap">
  <h1 class="neon">CH<span class="fl">A</span>RGE<span class="bolt">⚡</span></h1>
  <p class="tagline">How a TEDxFargo billboard became a two-meter, 596-LED,
  3D-printed neon sign — seventeen days of coupons, forensics, seam physics and
  glue-free press fits, with every defect caught by a tool built the same day.</p>
</header>
<div class="wrap stats">
  <div class="stat"><b>17 days</b><span>brief → wiring</span></div>
  <div class="stat"><b>126</b><span>commits</span></div>
  <div class="stat"><b>596/600</b><span>LEDs placed / owned</span></div>
  <div class="stat"><b>~3.5 kg</b><span>PETG, 15 parts</span></div>
  <div class="stat"><b>2.07 m</b><span>sign width</span></div>
  <div class="stat"><b>43/43</b><span>final QA checks</span></div>
</div>
<div class="wide">{{HERO}}</div>
<p class="cap wrap" style="text-align:center">the whole system, to scale — 6 printed
letters + a 4-plate lightning-bolt board, one wood frame</p>

<div class="wrap">
<div class="stamp">Day 1 · June 24</div>
<h2>The brief</h2>
<p>TEDxFargo's 2026 theme art is a neon billboard: <b>CHARGE</b> in white tube
letters, a yellow lightning bolt fused through an X, a red strike inside it. The
job: rebuild it as a physical sign — 3D-printed on a Bambu H2D, lit from behind by
12&nbsp;mm bullet pixels, big enough to own a stage.</p>
<p>The first real decision wasn't about printing at all. It was admitting that
<b>light through printed plastic is an optics problem</b>, and optics problems are
settled by experiments, not opinions.</p>

<div class="stamp">Days 1–8 · the optics safari</div>
<h2>Burning plastic to learn light</h2>
<p>We printed coupon ladders — little test cells sweeping air gaps, lens
thicknesses, infills, textures — and pointed real pixels through every one of
them. The findings rewired the whole design:</p>
<p><b>Air gap dominates everything.</b> 35–50&nbsp;mm gaps went dim and washy;
10–20&nbsp;mm made the lens matter again. <b>A white interior is worth ~5 LEDs of
brightness</b> — the shell became a three-color print: black face, white reflector
liner, clear lens. And the diffusion winner, after an eight-cell bake-off of masks,
cones and gyroid fills, was… <b>the simplest cell on the plate</b>: a plain clear
face over an open cavity.</p>
<div class="fail"><b>failed branch № 1</b> The perforated diffuser mask — physics
said it would flatten the hotspot beautifully. The printer said no: a disc on tiny
legs printed as spaghetti. The simplest cell won the same test the mask was designed
to win.</div>
<div class="fail"><b>failed branch № 2</b> Making clear PETG cloudier with slicer
settings. A whole research doc of haze levers; empirically none of them did
anything visible. The lever that worked was <b>baked geometry</b> — a jittered
pyramid-facet texture (V8) modeled directly into the lens top, because no slicer
can fuzzy-skin a top face.</div>
<div class="fail"><b>failed branch № 3</b> A snap-over diffuser cap. Abandoned —
and it taught the chirality lesson: any part you flip over to use must be designed
pre-mirrored. That gotcha got a name, and it came back twice.</div>

<div class="stamp">Days 8–13 · the word</div>
<h2>The font is the vector</h2>
<p>The letterforms came out of the actual billboard art: EPS → raster → a
skeleton-thinning centerline extractor written in pure stdlib Python. Neon letters
turn out to be <b>open tube runs</b>, not outlines — the C is one continuous
1.16-meter tube. Each tube got widened 3&nbsp;mm per side so a Ø12 pixel could live
inside, and the whole word became one continuous black billboard face, corridor-cut
into six bed-sized pieces <b>through the black field only</b> — never through a
letter. The letters kiss at true kerning; two pairs had to be nudged apart a few
millimeters or their widened tubes would have physically fused.</p>
<p>Then the forensics. The slicer preview showed the A's crossbar "didn't even make
a triangle." Investigation found the extractor had quietly amputated two font
features — the hat's left arm and the triangle's left side — by treating them as
skeleton spurs. A raster mockup nearly tricked us into adding a floating dash that
was actually a glow highlight. Out of that mess came the project's sharpest rule:</p>
<div class="rule"><b>the rule</b> The outlined vector IS the font. Nothing gets
added from raster readings the vector doesn't corroborate — and every rendered STL
gets eyeballed before it's declared done. A coverage QA tool now diffs the art's
ink against the built geometry, because the extractor can't audit itself.</div>
<p>The repaired pieces printed beautifully. Quote from the shop floor:
<i>"printing amazingly… blowing my mind."</i></p>

<div class="stamp">Days 11–12 · the bolt</div>
<h2>A lightning bolt with physics opinions</h2>
<p>The bolt panel is one fused outline — flat-top bolt woven through an X — plus
the billboard's red inner strike. It wanted to be 410×550&nbsp;mm, which means four
printed plates, which means seams. A straight vertical seam is impossible here: it
always grazes one of the X's near-vertical legs, so the cuts went <b>piecewise</b>,
stepping around the strokes. The red zigzag got hand-fit to the billboard and then
argued down by clearance physics — the bar literally cannot tilt (a 0&nbsp;mm
corridor) and the tail stops where the wedge pinches shut. Fidelity to the art,
bounded by what 22&nbsp;mm light channels allow.</p>

<div class="stamp">Day 17 · July 10</div>
<h2>Killing the seam shadows</h2>
<p>One problem left: pixels kept a safe 12.5&nbsp;mm off every plate joint (a
press-fit collar can't straddle a cut), so the tube went dark for 34–58&nbsp;mm at
each of the seven seam crossings. The fix everyone reaches for first — just shrink
the keepout — <b>doesn't work</b>: the placement algorithm marched past seams
without back-filling, and shallow-angle crossings stretch any keepout by
1/sin&nbsp;θ along the tube.</p>
<p>What worked: <b>anchor pixels symmetrically at every crossing</b> (walked out to
true perpendicular distance), and for the two crossings too shallow to straddle,
put the pixel <b>on the seam itself</b> — its calibrated press-fit collar embedded
in a printed splice strap behind the joint, shining through a small bite in the
plate edges. The straps do triple duty: they carry those collars, they bolt the
four plates into one rigid panel with captive M4 nuts, and they replaced an entire
wood rail in the frame plan. Same 137 pixels, worst gap 58&nbsp;mm → 23.5&nbsp;mm.</p>
</div>
<div class="duo">
  <div><p class="lab">before — 12.5&nbsp;mm keepout</p>{{BEFORE}}</div>
  <div><p class="lab">after — anchored straddle + 2 strap collars</p>{{AFTER}}</div>
</div>
<div class="wrap">
<p>The straps have "pizza-saver" leg sockets (empty until the mounted panel proves
it needs them), chamfered pass-through holes so pixels install <i>through</i> the
bracket — which makes wire pinching geometrically impossible — and a 43-check
independent QA audit that probes the actual STL vertices. The audit earned its keep
immediately: it found one pixel at a T-junction whose flange overlapped a strap
corner by 0.8&nbsp;mm. Fixed, re-rendered, re-audited, then printed.</p>
</div>
<div class="wide">{{OVERLAY}}</div>
<p class="cap wrap" style="text-align:center">the splice straps (white), machine screws
(amber), frame screws (gray), embedded collars (ringed), leg sockets (green)</p>

<div class="wrap">
<div class="stamp">Day 17 · night shift</div>
<h2>Wires and light</h2>
<p>Wiring diagrams are drawn <b>as seen from behind</b>, because that's where the
person with the wire strippers stands. One data chain per sign — the word runs
C→E letter by letter, the bolt's red strike falls out as one contiguous block
(chain 87–107), and exactly <b>eight links in the whole sign need a splice
extension</b>; everything else folds its slack into the plenum. The chains compile
straight into WLED&nbsp;16 mappings: 2D grids at 10&nbsp;mm resolution, so plasma
and fire effects render in true sign-space, plus ready-made segment presets for the
color zones.</p>
</div>
<div class="duo">
  <div><p class="lab">bolt — back view, data in → end</p>{{BOARD_BACK}}</div>
  <div><p class="lab">word — back view (letters read reversed)</p>{{WORD_BACK}}</div>
</div>

<div class="wrap">
<div class="stamp">the spin-off</div>
<h2>And then it became a machine</h2>
<div class="sf">
<h3>signforge — LED Sign Builder</h3>
<p style="max-width:100%">Everything above got extracted into a generic,
pip-installable tool: type <b>text in any font</b> — or drop an <b>SVG / DXF /
PNG logo</b> — and get back a complete, verified, print-ready LED sign kit. Pure
local Python, no cloud, no OpenSCAD. Born from this build's scars: <i>every
default was set by a printed test, and every automated gate exists because a
defect once shipped past a preview.</i></p>
<ul>
<li>Multi-material STLs + Bambu-ready 3MFs per plate (black shell / white
reflector / clear textured lens — the CHARGE cross-section)</li>
<li>LED plan with chord-measured spacing, seam keepouts, PSU sizing,
strings-of-50 budgeting and jumper flags</li>
<li>Panelization to any bed, with the Text Plating Law: big signs cut at kerning
gaps, one letter per plate — never through a letterform</li>
<li>The V8 baked lens texture, lit-preview renders, a zero-dependency WebGL
viewer, and <code>params.json</code> so any kit rebuilds exactly</li>
<li>A retro console UI with accounts, tiers and a build queue — 165 tests green,
CHARGE itself is the pinned gold standard</li>
</ul>
</div>

<div class="stamp">colophon</div>
<h2>Built by a human and a robot</h2>
<p>Blaine ran the printers, made the calls, caught the A's missing triangle, and
kept a hard rule that approved designs are final. Claude wrote the pipeline —
extractors, panelizers, placement solvers, QA audits, these very pages — and
learned, repeatedly, that the eyeball test outranks the elegant abstraction.
Everything regenerates from source: one command per artifact, no hand-edited
geometry anywhere.</p>
</div>
<div class="wide">{{SYSMAP}}</div>
<p class="cap wrap" style="text-align:center">system map — pieces, plates, straps,
screws, and the frame concept</p>

<footer><div class="wrap">
  <span class="mono">TEDxFargo CHARGE 2026 · printed on a Bambu H2D · PETG ·
  WLED 16 · July 2026</span>
  <div class="links">
    <a href="https://claude.ai/code/artifact/c7c442d3-80b4-4f2f-85ff-844858b0aa0b">full system preview</a>
    <a href="https://claude.ai/code/artifact/758534c5-1e14-42fa-afa7-ca9a555f5aa3">seam-bracket deep dive</a>
    <a href="https://claude.ai/code/artifact/331a7816-0ea2-4cc6-b2c7-80d7e29291fa">wiring &amp; WLED</a>
  </div>
</div></footer>
"""
for k, v in {"{{HERO}}": HERO, "{{SYSMAP}}": SYSMAP, "{{BEFORE}}": BEFORE,
             "{{AFTER}}": AFTER, "{{OVERLAY}}": OVERLAY,
             "{{BOARD_BACK}}": BOARD_BACK, "{{WORD_BACK}}": WORD_BACK}.items():
    html = html.replace(k, v)
open("docs/sign-preview/index.html", "w").write(html)
print("wrote docs/sign-preview/index.html (%.0f KB)" % (len(html) / 1024))
