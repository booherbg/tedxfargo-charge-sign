#!/usr/bin/env python3
"""Generate docs/sign-preview/frame-3d.html — rotatable WebGL assembly view.
Loads the REAL rendered STLs, applies each part's install transform into
board coordinates (z=0 plate back, +z into the cavity), quantizes to int16,
and embeds everything in one self-contained page (no external libraries).
Board plates / bolt outline / pixels / controller are synthesized from the
layout data so the giant board meshes stay out of the page."""
import base64, json, math, re, struct

def grab(txt, name):
    return eval(re.search(re.escape(name) + r"\s*=\s*(\[.*?\]);", txt, re.S).group(1))

def load_stl(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:300]:
        tris, cur = [], []
        for line in data.decode(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("vertex"):
                cur.append(tuple(float(v) for v in line.split()[1:4]))
                if len(cur) == 3:
                    tris.append(cur); cur = []
        return tris
    n = struct.unpack("<I", data[80:84])[0]
    out = []
    for i in range(n):
        f = struct.unpack("<9f", data[84 + i*50 + 12:84 + i*50 + 48])
        out.append([(f[0], f[1], f[2]), (f[3], f[4], f[5]), (f[6], f[7], f[8])])
    return out

bl = open("src/parts/board_layout.scad").read()
fl = open("src/parts/frame_layout.scad").read()
PXM = json.load(open("src/parts/bolt_pixmap.json"))["pixels"]
bb_plates, bb_paths = grab(bl, "bb_plates"), grab(bl, "bb_paths")
fr_joint = grab(fl, "fr_joint")
fr_leg, fr_feet, fr_handle = grab(fl, "fr_leg"), grab(fl, "fr_feet"), grab(fl, "fr_handle")
fr_ctl_ext = grab(fl, "fr_ctl_ext")
JX, JY = fr_joint
Z1 = 50.4

parts = []          # (group, color, tris)
def add(group, color, tris):
    parts.append((group, color, tris))

def xform(tris, fn):
    return [[fn(v) for v in t] for t in tris]

# frame segments: print = board - clip origin
for seg, (ox, oy) in {1: (-3.5, -3.5), 2: (205, -3.5),
                      3: (205, 300), 4: (-3.5, 300)}.items():
    add("frame", "#8b94a1", xform(load_stl(f"stl/frame_seg{seg}.stl"),
        lambda v, ox=ox, oy=oy: (v[0] + ox, v[1] + oy, v[2])))
# panels: print = Rx180 . (board + t)  ->  board = (x, ey1 - y, Z1 - z)
for i in range(4):
    ex0 = 0.3 if i in (0, 2) else JX - 2.7
    ey1 = JY + 2.7 if i in (0, 1) else 549.7
    add("panels", "#57637a", xform(load_stl(f"stl/frame_panel{i+1}.stl"),
        lambda v, a=ex0, b=ey1: (v[0] + a, b - v[1], Z1 - v[2])))
# straps: local (u, v, z) -> installed board coords
for n, fn in ((1, lambda v: (v[0], 255 - v[1], v[2])),
              (2, lambda v: (v[0], 255 - v[1], v[2])),
              (3, lambda v: (126 + v[1], v[0], v[2])),
              (4, lambda v: (153 + v[1], v[0], v[2]))):
    add("straps", "#7ad48a", xform(load_stl(f"stl/strap_s{n}.stl"), fn))
# legs, handles, feet, keys
leg = load_stl("stl/frame_leg.stl")
for lx, ly in fr_leg:
    add("hardware", "#e8ebef", xform(leg, lambda v, a=lx, b=ly: (v[0]+a, v[1]+b, v[2]+1)))
hnd = load_stl("stl/frame_handle.stl")
for h in fr_handle:
    cx = (h[2] + h[3]) / 2
    add("hardware", "#e8ebef", xform(hnd,
        lambda v, a=cx: (v[0] + a, v[1] + 575.5, v[2] + Z1 - 15)))
ft = load_stl("stl/frame_foot.stl")
for fx in fr_feet:
    add("hardware", "#e8ebef", xform(ft,
        lambda v, a=fx: (v[0] + a, v[2] - 9.5, v[1] + 23)))
key = load_stl("stl/frame_key.stl")
for fn in (lambda v: (JX + v[0], 3.5 + v[2], 19 + v[1]),
           lambda v: (JX + v[0], 542.5 + v[2], 19 + v[1]),
           lambda v: (3.5 + v[2], JY + v[0], 19 + v[1]),
           lambda v: (402.5 + v[2], JY + v[0], 19 + v[1])):
    add("hardware", "#e8ebef", xform(key, fn))

# synthesized board: plates, bolt ribbon, pixels, controller
def box(x0, y0, z0, x1, y1, z1):
    c = [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
         (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    f = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
         (2,3,7),(2,7,6),(1,2,6),(1,6,5),(3,0,4),(3,4,7)]
    return [[c[a], c[b], c[d]] for a, b, d in f]
pl = []
for x0, x1, y0, y1 in bb_plates:
    pl += box(x0, y0, -2, x1, y1, 0)
add("board", "#1d232c", pl)
rib = []
for p in bb_paths:
    for i in range(len(p) - 1):
        a, b = p[i], p[i+1]
        rib.append([(a[0], a[1], -2), (b[0], b[1], -2), (b[0], b[1], -12)])
        rib.append([(a[0], a[1], -2), (b[0], b[1], -12), (a[0], a[1], -12)])
add("board", "#dfe3e8", rib)      # white channel liner walls
# pixel hardware, rear-visible: white collar liner rings through the plate
# + dark bullet bodies punching back through the strap pass holes
def ringpts(cx, cy, r, z, n=12):
    return [(cx + r*math.cos(6.2832*k/n), cy + r*math.sin(6.2832*k/n), z)
            for k in range(n)]
def tube(cx, cy, r, z0, z1, n=12):
    a, b = ringpts(cx, cy, r, z0, n), ringpts(cx, cy, r, z1, n)
    return [t for k in range(n) for t in
            ([a[k], a[(k+1) % n], b[(k+1) % n]], [a[k], b[(k+1) % n], b[k]])]
def disc(cx, cy, r, z, n=12):
    a = ringpts(cx, cy, r, z, n)
    return [[(cx, cy, z), a[k], a[(k+1) % n]] for k in range(n)]
def annulus(cx, cy, r0, r1, z, n=12):
    a, b = ringpts(cx, cy, r0, z, n), ringpts(cx, cy, r1, z, n)
    return [t for k in range(n) for t in
            ([a[k], b[k], b[(k+1) % n]], [a[k], b[(k+1) % n], a[(k+1) % n]])]
collars, bullets = [], []
for p in PXM:
    collars += tube(p["x"], p["y"], 8, -2, 2) + annulus(p["x"], p["y"], 6, 8, 2)
    bullets += tube(p["x"], p["y"], 6, 0, 14)
add("board", "#dfe3e8", collars)
add("board", "#2a323d", bullets)
# animated LED faces: front lens disc + rear glow cap per pixel (72 verts ea)
led_pos, led_meta = [], []
for p in PXM:
    for t in disc(p["x"], p["y"], 6, -2.3) + disc(p["x"], p["y"], 5, 14.3):
        led_pos += [c for v in t for c in v]
    led_meta.append({"c": p["chain"], "x": p["x"], "y": p["y"],
                     "z": 1 if p["color"] == "red" else 0})
ec = (fr_ctl_ext[0][0] + fr_ctl_ext[1][0]) / 2
add("controller", "#d9a017", box(-26.5, ec - 64.5, 0.4, -3.5, ec + 64.5, Z1))

# quantize + encode
enc, total = [], 0
for group, color, tris in parts:
    vid, verts, idx = {}, [], []
    for t in tris:
        for v in t:
            k = tuple(round(c, 2) for c in v)
            if k not in vid:
                vid[k] = len(verts); verts.append(k)
            idx.append(vid[k])
    mins = [min(v[i] for v in verts) for i in range(3)]
    maxs = [max(v[i] for v in verts) for i in range(3)]
    scale = [max((maxs[i] - mins[i]) / 32760.0, 1e-6) for i in range(3)]
    qv = b"".join(struct.pack("<3h", *[int(round((v[i] - mins[i]) / scale[i]))
                                       for i in range(3)]) for v in verts)
    qi = b"".join(struct.pack("<I", i) for i in idx)
    total += len(qv) + len(qi)
    enc.append({"g": group, "c": color, "n": len(idx),
                "min": mins, "sc": scale,
                "v": base64.b64encode(qv).decode(),
                "i": base64.b64encode(qi).decode()})
print(f"parts: {len(enc)}, payload {total/1024:.0f} KB raw")

LED = json.dumps({"pos": base64.b64encode(
    struct.pack("<%df" % len(led_pos), *led_pos)).decode(), "meta": led_meta})
DATA = json.dumps(enc)
page = """<title>Bolt backer frame — 3D assembly</title>
<style>
:root { --bg:#101318; --card:#171c23; --ink:#e8ebef; --mut:#97a0ac;
  --line:#2a323d; --accent:#ffc93c; }
@media (prefers-color-scheme: light) { :root { --bg:#eef0f3; --card:#ffffff;
  --ink:#1a2027; --mut:#5b6572; --line:#d7dce2; --accent:#c79616; } }
:root[data-theme="dark"] { --bg:#101318; --card:#171c23; --ink:#e8ebef;
  --mut:#97a0ac; --line:#2a323d; --accent:#ffc93c; }
:root[data-theme="light"] { --bg:#eef0f3; --card:#ffffff; --ink:#1a2027;
  --mut:#5b6572; --line:#d7dce2; --accent:#c79616; }
html, body { height:100%; }
body { margin:0; background:var(--bg); color:var(--ink); overflow:hidden;
  font:14px/1.4 -apple-system, "Segoe UI", system-ui, sans-serif; }
#c { position:fixed; inset:0; width:100%; height:100%; touch-action:none; }
#hud { position:fixed; top:14px; left:14px; background:var(--card);
  border:1px solid var(--line); border-radius:8px; padding:12px 14px;
  max-width:250px; }
#hud h1 { font-size:14px; margin:0 0 2px; }
#hud p { font-size:11px; color:var(--mut); margin:0 0 8px; }
label { display:inline-flex; align-items:center; gap:5px; margin:2px 10px 2px 0;
  font-size:12px; cursor:pointer; user-select:none; }
.sw { width:10px; height:10px; border-radius:2px; display:inline-block; }
</style>
<canvas id="c"></canvas>
<div id="hud">
  <h1>Bolt backer frame — assembly</h1>
  <p>drag rotate · wheel zoom · shift-drag pan<br>view from the back; front
  face (bolt) points away at start</p>
  <div id="tg"></div>
  <p style="margin:8px 0 2px">led effect</p><div id="fx"></div>
</div>
<script>
const PARTS = __DATA__;
const LEDS = __LED__;
const groups = {frame:true, panels:false, straps:true, hardware:true,
                board:true, controller:true, leds:true};
const gcol = {frame:"#8b94a1", panels:"#57637a", straps:"#7ad48a",
              hardware:"#e8ebef", board:"#dfe3e8", controller:"#d9a017",
              leds:"#ffc93c"};
const tg = document.getElementById("tg");
for (const g in groups) {
  const l = document.createElement("label");
  const cb = document.createElement("input");
  cb.type = "checkbox"; cb.checked = groups[g];
  cb.onchange = () => { groups[g] = cb.checked; };
  const sw = document.createElement("span");
  sw.className = "sw"; sw.style.background = gcol[g];
  l.append(cb, sw, document.createTextNode(g));
  tg.append(l);
}
const cv = document.getElementById("c");
const gl = cv.getContext("webgl2", {antialias:true});
const vs = `#version 300 es
in vec3 p; uniform mat4 mvp; out vec3 w;
void main(){ w = p; gl_Position = mvp * vec4(p, 1.0); }`;
const fs = `#version 300 es
precision highp float; in vec3 w; uniform vec3 col, eye; out vec4 o;
void main(){
  vec3 n = normalize(cross(dFdx(w), dFdy(w)));
  vec3 L = normalize(eye - w);
  float d = 0.34 + 0.62 * abs(dot(n, L)) + 0.18 * pow(abs(dot(n, L)), 24.0);
  o = vec4(col * d, 1.0); }`;
function sh(t, s){ const h = gl.createShader(t); gl.shaderSource(h, s);
  gl.compileShader(h); return h; }
const pr = gl.createProgram();
gl.attachShader(pr, sh(gl.VERTEX_SHADER, vs));
gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, fs));
gl.linkProgram(pr); gl.useProgram(pr);
const uMvp = gl.getUniformLocation(pr, "mvp"),
      uCol = gl.getUniformLocation(pr, "col"),
      uEye = gl.getUniformLocation(pr, "eye");
const vs2 = `#version 300 es
in vec3 p; in vec3 c; uniform mat4 mvp; out vec3 vc;
void main(){ vc = c; gl_Position = mvp * vec4(p, 1.0); }`;
const fs2 = `#version 300 es
precision highp float; in vec3 vc; out vec4 o;
void main(){ o = vec4(vc, 1.0); }`;
const pr2 = gl.createProgram();
gl.attachShader(pr2, sh(gl.VERTEX_SHADER, vs2));
gl.attachShader(pr2, sh(gl.FRAGMENT_SHADER, fs2));
gl.linkProgram(pr2);
const uMvp2 = gl.getUniformLocation(pr2, "mvp");
function b64(s){ const b = atob(s), a = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) a[i] = b.charCodeAt(i); return a.buffer; }
const meshes = PARTS.map(p => {
  const q = new Int16Array(b64(p.v)), nv = q.length / 3;
  const f = new Float32Array(q.length);
  for (let i = 0; i < nv; i++) for (let k = 0; k < 3; k++)
    f[i*3+k] = p.min[k] + q[i*3+k] * p.sc[k];
  const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  const vb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, vb);
  gl.bufferData(gl.ARRAY_BUFFER, f, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
  const ib = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint32Array(b64(p.i)), gl.STATIC_DRAW);
  const c = parseInt(p.c.slice(1), 16);
  return {vao, n: p.n, g: p.g,
          col: [(c>>16&255)/255, (c>>8&255)/255, (c&255)/255]};
});
// LED mesh: static positions + per-frame color buffer (72 verts/pixel)
const ledPos = new Float32Array(b64(LEDS.pos));
const nled = LEDS.meta.length;
const ledCol = new Float32Array(nled * 72 * 3);
const ledVao = gl.createVertexArray(); gl.bindVertexArray(ledVao);
const lpb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, lpb);
gl.bufferData(gl.ARRAY_BUFFER, ledPos, gl.STATIC_DRAW);
gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
const lcb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, lcb);
gl.bufferData(gl.ARRAY_BUFFER, ledCol, gl.DYNAMIC_DRAW);
gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 3, gl.FLOAT, false, 0, 0);
function hsv(h, s2, v){ const i = Math.floor(h*6), f = h*6 - i;
  const a = v*(1-s2), q = v*(1-f*s2), t2 = v*(1-(1-f)*s2);
  return [[v,t2,a],[q,v,a],[a,v,t2],[a,q,v],[t2,a,v],[v,a,q]][((i%6)+6)%6]; }
const FX = {
  "as-built": p => p.z ? [1,.30,.30] : [1,.78,.22],
  chase: (p,t) => { const d = (p.c - t*40%137 + 137) % 137;
    const v = Math.max(.04, 1 - d/14);
    return p.z ? [v,v*.28,v*.28] : [v,v*.78,v*.2]; },
  rainbow: (p,t) => hsv((p.c/137 + t*.10) % 1, 1, 1),
  wave: (p,t) => hsv(((p.x + p.y)/800 + t*.22) % 1, .92, 1),
  sparkle: (p,t) => { const s2 = Math.sin(p.c*127.1 +
      Math.floor(t*7)*311.7) * 43758.55, r = s2 - Math.floor(s2);
    return r > .9 ? [1,1,.92] : [.13,.09,.02]; },
  breathe: (p,t) => { const v = .25 + .75*(.5 + .5*Math.sin(t*2.2 -
      (p.x+p.y)/260));
    return p.z ? [v,v*.26,v*.26] : [v,v*.76,v*.2]; },
};
let fx = "chase";
const fxd = document.getElementById("fx");
for (const name in FX) {
  const b = document.createElement("button");
  b.textContent = name;
  b.style.cssText = "margin:2px 4px 2px 0;padding:3px 8px;font-size:11px;" +
    "border:1px solid var(--line);border-radius:5px;background:var(--card);" +
    "color:var(--ink);cursor:pointer";
  b.onclick = () => { fx = name;
    [...fxd.children].forEach(x => x.style.borderColor = "var(--line)");
    b.style.borderColor = "var(--accent)"; };
  if (name === fx) b.style.borderColor = "var(--accent)";
  fxd.append(b);
}
function ledTick(t){
  const f = FX[fx];
  for (let i = 0; i < nled; i++) {
    const c = f(LEDS.meta[i], t);
    for (let k = 0; k < 36; k++) ledCol.set(c, (i*72 + k)*3);
    const r = [c[0]*.45, c[1]*.45, c[2]*.45];
    for (let k = 36; k < 72; k++) ledCol.set(r, (i*72 + k)*3);
  }
  gl.bindBuffer(gl.ARRAY_BUFFER, lcb);
  gl.bufferSubData(gl.ARRAY_BUFFER, 0, ledCol);
}
let th = 0.6, ph = 0.42, R = 900, tgt = [205, 275, 15];
function mat(){
  const cw = cv.clientWidth, chh = cv.clientHeight;
  const eye = [tgt[0] + R*Math.cos(ph)*Math.sin(th),
               tgt[1] + R*Math.sin(ph),
               tgt[2] + R*Math.cos(ph)*Math.cos(th)];
  const f = norm(sub(tgt, eye)), s = norm(cross(f, [0,1,0])), u = cross(s, f);
  const V = [s[0],u[0],-f[0],0, s[1],u[1],-f[1],0, s[2],u[2],-f[2],0,
             -dot(s,eye), -dot(u,eye), dot(f,eye), 1];
  const n = 5, fa = 6000, a = cw/chh, t = Math.tan(0.45)*n;
  const P = [n/(t*a),0,0,0, 0,n/t,0,0, 0,0,-(fa+n)/(fa-n),-1,
             0,0,-2*fa*n/(fa-n),0];
  return [mul(P, V), eye];
}
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=a=>{const l=Math.hypot(...a);return[a[0]/l,a[1]/l,a[2]/l];};
function mul(A,B){ const o=new Array(16);
  for(let r=0;r<4;r++)for(let c2=0;c2<4;c2++){let s2=0;
    for(let k=0;k<4;k++)s2+=A[k*4+r]*B[c2*4+k]; o[c2*4+r]=s2;} return o; }
let drag=0, px0=0, py0=0;
cv.addEventListener("pointerdown", e=>{drag=e.shiftKey?2:1;px0=e.clientX;py0=e.clientY;
  cv.setPointerCapture(e.pointerId);});
cv.addEventListener("pointermove", e=>{
  if(!drag) return;
  const dx=e.clientX-px0, dy=e.clientY-py0; px0=e.clientX; py0=e.clientY;
  if(drag===1){ th-=dx*0.006; ph=Math.max(-1.5,Math.min(1.5,ph+dy*0.006)); }
  else { const s=R*0.0012;
    const ey=[Math.cos(ph)*Math.sin(th),Math.sin(ph),Math.cos(ph)*Math.cos(th)];
    const rt=norm(cross([0,1,0],ey)), up=cross(ey,rt);
    tgt=[tgt[0]+rt[0]*dx*s+up[0]*dy*s, tgt[1]+rt[1]*dx*s+up[1]*dy*s,
         tgt[2]+rt[2]*dx*s+up[2]*dy*s]; }});
cv.addEventListener("pointerup", ()=>drag=0);
cv.addEventListener("wheel", e=>{e.preventDefault();
  R=Math.max(120,Math.min(3500,R*Math.exp(e.deltaY*0.001)));},{passive:false});
function bg(){
  const s=getComputedStyle(document.documentElement).getPropertyValue("--bg").trim();
  const c=parseInt(s.slice(1),16);
  return [(c>>16&255)/255,(c>>8&255)/255,(c&255)/255];
}
function frame(){
  const d=window.devicePixelRatio||1;
  if(cv.width!==cv.clientWidth*d||cv.height!==cv.clientHeight*d){
    cv.width=cv.clientWidth*d; cv.height=cv.clientHeight*d;}
  gl.viewport(0,0,cv.width,cv.height);
  const b=bg(); gl.clearColor(b[0],b[1],b[2],1);
  gl.enable(gl.DEPTH_TEST);
  gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  const [M,eye]=mat();
  gl.useProgram(pr);
  gl.uniformMatrix4fv(uMvp,false,new Float32Array(M));
  gl.uniform3fv(uEye,eye);
  for(const m of meshes){ if(!groups[m.g]) continue;
    gl.bindVertexArray(m.vao); gl.uniform3fv(uCol,m.col);
    gl.drawElements(gl.TRIANGLES,m.n,gl.UNSIGNED_INT,0); }
  if (groups.leds) {
    ledTick(performance.now()/1000);
    gl.useProgram(pr2);
    gl.uniformMatrix4fv(uMvp2,false,new Float32Array(M));
    gl.bindVertexArray(ledVao);
    gl.drawArrays(gl.TRIANGLES, 0, nled*72);
  }
  requestAnimationFrame(frame);
}
frame();
</script>"""
page = page.replace("__DATA__", DATA).replace("__LED__", LED)
open("docs/sign-preview/frame-3d.html", "w").write(page)
print("wrote docs/sign-preview/frame-3d.html (%d KB)" % (len(page) // 1024))
