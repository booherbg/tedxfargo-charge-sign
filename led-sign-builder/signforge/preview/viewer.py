"""Self-contained 3D kit viewer: zero dependencies, works from file://.

Embeds each body's binary STL as base64 and renders with raw WebGL (a tiny
flat-shaded viewer beats vendoring three.js: ES-module builds don't load from
file://, and kit previews must open from an unzipped folder with no server).
"""

from __future__ import annotations

import base64
import json

JS = r"""
'use strict';
function b64ToBuf(b64){
  const raw = atob(b64); const buf = new ArrayBuffer(raw.length);
  const u8 = new Uint8Array(buf);
  for (let i=0;i<raw.length;i++) u8[i] = raw.charCodeAt(i);
  return buf;
}
function parseSTLBuf(buf){
  const dv = new DataView(buf);
  const ntri = dv.getUint32(80, true);
  const pos = new Float32Array(ntri*9), nrm = new Float32Array(ntri*9);
  let o = 84;
  for (let t=0;t<ntri;t++){
    const nx=dv.getFloat32(o,true), ny=dv.getFloat32(o+4,true), nz=dv.getFloat32(o+8,true);
    o += 12;
    for (let v=0;v<3;v++){
      const k = t*9+v*3;
      pos[k]=dv.getFloat32(o,true); pos[k+1]=dv.getFloat32(o+4,true); pos[k+2]=dv.getFloat32(o+8,true);
      nrm[k]=nx; nrm[k+1]=ny; nrm[k+2]=nz;
      o += 12;
    }
    o += 2;
  }
  return {pos, nrm, count:ntri*3};
}
const VS=`attribute vec3 aP; attribute vec3 aN; uniform mat4 uMV,uP; uniform mat3 uN;
varying vec3 vN; varying vec3 vE;
void main(){ vec4 e=uMV*vec4(aP,1.0); vE=-e.xyz; vN=uN*aN; gl_Position=uP*e; }`;
const FS=`precision mediump float; varying vec3 vN; varying vec3 vE; uniform vec3 uC; uniform float uA;
void main(){ vec3 N=normalize(vN); if(!gl_FrontFacing) N=-N; vec3 L=normalize(vec3(0.5,0.6,1.0));
 float d=max(dot(N,L),0.0); vec3 E=normalize(vE); vec3 H=normalize(L+E);
 float s=pow(max(dot(N,H),0.0),40.0)*0.35;
 vec3 c=uC*(0.35+0.65*d)+vec3(s); gl_FragColor=vec4(c,uA); }`;
function hex(c){ return [parseInt(c.slice(1,3),16)/255, parseInt(c.slice(3,5),16)/255, parseInt(c.slice(5,7),16)/255]; }

const canvas=document.getElementById('gl');
const gl=canvas.getContext('webgl',{antialias:true});
function sh(t,src){const s=gl.createShader(t);gl.shaderSource(s,src);gl.compileShader(s);
 if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw gl.getShaderInfoLog(s);return s;}
const prog=gl.createProgram();
gl.attachShader(prog,sh(gl.VERTEX_SHADER,VS));gl.attachShader(prog,sh(gl.FRAGMENT_SHADER,FS));
gl.linkProgram(prog);gl.useProgram(prog);
const loc={aP:gl.getAttribLocation(prog,'aP'),aN:gl.getAttribLocation(prog,'aN'),
 uMV:gl.getUniformLocation(prog,'uMV'),uP:gl.getUniformLocation(prog,'uP'),
 uN:gl.getUniformLocation(prog,'uN'),uC:gl.getUniformLocation(prog,'uC'),uA:gl.getUniformLocation(prog,'uA')};
gl.enable(gl.DEPTH_TEST);

const meshes=[];
let bbox=[1e9,1e9,1e9,-1e9,-1e9,-1e9];
let C=[0,0,0], R=100;
let cam=null;
async function loadAll(){
  for (const pc of SIGN_DATA.pieces){
    for (const b of pc.bodies){
      const buf = b.stl ? b64ToBuf(b.stl) : await (await fetch(b.url)).arrayBuffer();
      const m=parseSTLBuf(buf);
      for (let i=0;i<m.pos.length;i+=3){
        bbox[0]=Math.min(bbox[0],m.pos[i]);bbox[3]=Math.max(bbox[3],m.pos[i]);
        bbox[1]=Math.min(bbox[1],m.pos[i+1]);bbox[4]=Math.max(bbox[4],m.pos[i+1]);
        bbox[2]=Math.min(bbox[2],m.pos[i+2]);bbox[5]=Math.max(bbox[5],m.pos[i+2]);
      }
      const vb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vb);gl.bufferData(gl.ARRAY_BUFFER,m.pos,gl.STATIC_DRAW);
      const nb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,nb);gl.bufferData(gl.ARRAY_BUFFER,m.nrm,gl.STATIC_DRAW);
      meshes.push({vb,nb,count:m.count,color:hex(b.color),alpha:b.name==='lens'?0.55:1.0,
        piece:pc.label,body:b.name,pc:pc.center,lens:b.name==='lens'});
      draw();  // progressive: each body appears as it streams in
    }
  }
  C=[(bbox[0]+bbox[3])/2,(bbox[1]+bbox[4])/2,(bbox[2]+bbox[5])/2];
  R=Math.max(bbox[3]-bbox[0],bbox[4]-bbox[1],bbox[5]-bbox[2]);
  cam={th:-0.5,ph:0.9,d:R*1.6,tx:0,ty:0};
  draw();
}
let explode=0, lift=0;
const vis={};
document.querySelectorAll('.bodytoggle').forEach(cb=>{vis[cb.dataset.b]=cb.checked;
 cb.onchange=()=>{vis[cb.dataset.b]=cb.checked;draw();};});
document.getElementById('explode').oninput=e=>{explode=+e.target.value;draw();};
document.getElementById('lift').oninput=e=>{lift=+e.target.value;draw();};

function mat(){
  if(!cam){
    C=[(bbox[0]+bbox[3])/2,(bbox[1]+bbox[4])/2,(bbox[2]+bbox[5])/2];
    R=Math.max(bbox[3]-bbox[0],bbox[4]-bbox[1],bbox[5]-bbox[2],1);
    cam={th:-0.5,ph:0.9,d:R*1.6,tx:0,ty:0};
  }
  const {th,ph,d}=cam;
  const eye=[C[0]+cam.tx+d*Math.cos(ph)*Math.cos(th), C[1]+cam.ty+d*Math.cos(ph)*Math.sin(th), C[2]+d*Math.sin(ph)];
  const ctr=[C[0]+cam.tx,C[1]+cam.ty,C[2]];
  const up=[0,0,1];
  function sub(a,b){return [a[0]-b[0],a[1]-b[1],a[2]-b[2]];}
  function nrm(a){const l=Math.hypot(a[0],a[1],a[2]);return [a[0]/l,a[1]/l,a[2]/l];}
  function crs(a,b){return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];}
  const z=nrm(sub(eye,ctr)), x=nrm(crs(up,z)), y=crs(z,x);
  const mv=[x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0,
    -(x[0]*eye[0]+x[1]*eye[1]+x[2]*eye[2]),
    -(y[0]*eye[0]+y[1]*eye[1]+y[2]*eye[2]),
    -(z[0]*eye[0]+z[1]*eye[1]+z[2]*eye[2]),1];
  const f=1/Math.tan(0.4), a=canvas.width/canvas.height, zn=R*0.01, zf=R*10;
  const p=[f/a,0,0,0, 0,f,0,0, 0,0,(zf+zn)/(zn-zf),-1, 0,0,2*zf*zn/(zn-zf),0];
  return {mv,p,nm:[x[0],y[0],z[0], x[1],y[1],z[1], x[2],y[2],z[2]]};
}
function draw(){
  if(!meshes.length)return;
  const dpr=window.devicePixelRatio||1;
  canvas.width=canvas.clientWidth*dpr; canvas.height=canvas.clientHeight*dpr;
  gl.viewport(0,0,canvas.width,canvas.height);
  gl.clearColor(0.075,0.075,0.09,1); gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  const {mv,p,nm}=mat();
  gl.uniformMatrix4fv(loc.uP,false,new Float32Array(p));
  gl.uniformMatrix3fv(loc.uN,false,new Float32Array(nm));
  const sorted=[...meshes].sort((a,b)=>(a.alpha<1)-(b.alpha<1)); // opaque first
  for (const m of sorted){
    if (vis[m.body]===false) continue;
    const ex=(m.pc[0]-C[0])*explode, ey=(m.pc[1]-C[1])*explode, ez=m.lens?lift:0;
    const mv2=mv.slice();
    mv2[12]+=mv[0]*ex+mv[4]*ey+mv[8]*ez;
    mv2[13]+=mv[1]*ex+mv[5]*ey+mv[9]*ez;
    mv2[14]+=mv[2]*ex+mv[6]*ey+mv[10]*ez;
    gl.uniformMatrix4fv(loc.uMV,false,new Float32Array(mv2));
    gl.uniform3fv(loc.uC,m.color); gl.uniform1f(loc.uA,m.alpha);
    if (m.alpha<1){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);}
    gl.bindBuffer(gl.ARRAY_BUFFER,m.vb);gl.enableVertexAttribArray(loc.aP);gl.vertexAttribPointer(loc.aP,3,gl.FLOAT,false,0,0);
    gl.bindBuffer(gl.ARRAY_BUFFER,m.nb);gl.enableVertexAttribArray(loc.aN);gl.vertexAttribPointer(loc.aN,3,gl.FLOAT,false,0,0);
    gl.drawArrays(gl.TRIANGLES,0,m.count);
    if (m.alpha<1){gl.disable(gl.BLEND);gl.depthMask(true);}
  }
}
let drag=null;
canvas.addEventListener('mousedown',e=>{drag={x:e.clientX,y:e.clientY,b:e.button};e.preventDefault();});
window.addEventListener('mouseup',()=>drag=null);
window.addEventListener('mousemove',e=>{
  if(!drag)return;
  const dx=e.clientX-drag.x, dy=e.clientY-drag.y; drag.x=e.clientX; drag.y=e.clientY;
  if (drag.b===2||e.shiftKey){cam.tx-=dx*cam.d*0.001;cam.ty+=dy*cam.d*0.001;}
  else {cam.th-=dx*0.008; cam.ph=Math.min(1.5,Math.max(-1.5,cam.ph+dy*0.008));}
  draw();
});
canvas.addEventListener('wheel',e=>{cam.d*=Math.exp(e.deltaY*0.001);draw();e.preventDefault();},{passive:false});
canvas.addEventListener('contextmenu',e=>e.preventDefault());
window.addEventListener('resize',draw);
loadAll();
"""

CSS = """
html,body{margin:0;height:100%;background:#131318;color:#dde;font:13px system-ui}
#wrap{display:flex;height:100%}
#gl{flex:1;min-width:0;height:100%;display:block;cursor:grab}
#panel{width:230px;padding:14px;background:#191920;border-left:1px solid #26262e;overflow:auto}
h1{font-size:15px;margin:0 0 10px}
label{display:block;margin:10px 0 2px;color:#99a}
input[type=range]{width:100%}
.bt{display:flex;gap:6px;align-items:center;margin:4px 0}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block}
.hint{color:#667;font-size:11px;margin-top:14px;line-height:1.5}
"""


def _page(name: str, data: dict) -> str:
    body_names = sorted({b["name"] for pc in data["pieces"] for b in pc["bodies"]})
    colors = {b["name"]: b["color"] for pc in data["pieces"] for b in pc["bodies"]}
    toggles = "".join(
        f'<div class="bt"><input class="bodytoggle" type="checkbox" data-b="{n}" checked>'
        f'<span class="sw" style="background:{colors[n]}"></span>{n}</div>'
        for n in body_names
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{name} — 3D</title><style>{CSS}</style></head>
<body><div id="wrap"><canvas id="gl"></canvas><div id="panel">
<h1>{name}</h1>
{toggles}
<label>explode pieces</label><input id="explode" type="range" min="0" max="0.6" step="0.01" value="0">
<label>lift lenses</label><input id="lift" type="range" min="0" max="60" step="1" value="0">
<div class="hint">drag orbit · shift/right-drag pan · wheel zoom.<br>
Lens bodies render translucent. Geometry is the exact exported STL.</div>
</div></div>
<script>const SIGN_DATA = {json.dumps(data)};</script>
<script>{JS}</script>
</body></html>"""


def render_viewer(name: str, pieces_data: list[dict], max_embed_mb: float = 30.0) -> str | None:
    """Offline (file://) viewer: STLs embedded as base64.
    pieces_data: [{label, center:(x,y), bodies:[{name,color,stl:bytes}]}].
    Returns HTML, or None if the kit is too big to embed."""
    total = sum(len(b["stl"]) for pc in pieces_data for b in pc["bodies"])
    if total > max_embed_mb * 1e6:
        return None
    data = {
        "pieces": [
            {
                "label": pc["label"],
                "center": pc["center"],
                "bodies": [
                    {
                        "name": b["name"],
                        "color": b["color"],
                        "stl": base64.b64encode(b["stl"]).decode(),
                    }
                    for b in pc["bodies"]
                ],
            }
            for pc in pieces_data
        ]
    }
    return _page(name, data)


def render_viewer_remote(name: str, meta: dict, url_for) -> str:
    """Web viewer with NO size cap: bodies stream from the server on demand.
    meta is the kit's viewer_meta.json; url_for(rel_path) -> fetchable URL."""
    data = {
        "pieces": [
            {
                "label": pc["label"],
                "center": pc["center"],
                "bodies": [
                    {"name": b["name"], "color": b["color"], "url": url_for(b["file"])}
                    for b in pc["bodies"]
                ],
            }
            for pc in meta["pieces"]
        ]
    }
    return _page(name, data)
