'use strict';
const $ = id => document.getElementById(id);
let fontToken = null, artToken = null, libraryPick = null, fontPick = 'bungee';
let defaults = null, meta = null, me = null;
let timer = null, queueTimer = null;

/* ---------- boot ---------- */
async function init(){
  meta = await (await fetch('/api/presets')).json();
  defaults = meta.defaults;
  buildStaticControls();
  await loadFonts();
  await loadLibrary();
  await refreshMe();
  wireEvents();
  $('advanced').value = JSON.stringify(defaults, null, 2);
  schedule();
  pollQueue();
}

async function loadFonts(){
  const fonts = (await (await fetch('/api/fonts')).json()).fonts;
  const grid = $('fontgrid');
  for (const f of fonts){
    try {
      const face = new FontFace(`sf-${f.name}`, `url(${f.url})`);
      await face.load();
      document.fonts.add(face);
    } catch { /* tile falls back to system font */ }
    const t = document.createElement('div');
    t.className = 'ftile' + (f.name === fontPick ? ' sel' : '');
    t.dataset.name = f.name;
    t.innerHTML = `<div class="sample" style="font-family:'sf-${f.name}',system-ui">GLOW 24</div>
                   <div class="fname">${f.label} · ${f.vibe}</div>`;
    t.onclick = () => {
      fontPick = f.name;
      fontToken = null; $('fontfile').value = ''; $('fontchip').classList.remove('show');
      grid.querySelectorAll('.ftile').forEach(x => x.classList.remove('sel'));
      t.classList.add('sel');
      schedule();
    };
    grid.appendChild(t);
  }
}

async function loadLibrary(){
  const lib = (await (await fetch('/api/library')).json()).art;
  const grid = $('library');
  for (const item of lib){
    const t = document.createElement('div');
    t.className = 'tile'; t.title = item.name; t.dataset.name = item.name;
    t.innerHTML = `<img src="${item.url}" alt="${item.name}" loading="lazy">`;
    t.onclick = () => {
      if (libraryPick === item.name){ libraryPick = null; t.classList.remove('sel'); }
      else {
        libraryPick = item.name;
        artToken = null; $('artfile').value = ''; $('artchip').classList.remove('show');
        grid.querySelectorAll('.tile').forEach(x => x.classList.remove('sel'));
        t.classList.add('sel');
      }
      schedule();
    };
    grid.appendChild(t);
  }
}

function buildStaticControls(){
  const PRESET_TIPS = {
    'neon-classic': 'the CHARGE look: tube sign, bullet pixels you can see, faceted lens',
    'channel-bold': 'face-lit box letters — LEDs hide INSIDE the cavity and glow through the face',
    'mini-desk': 'desk-size strip-lit sign with slim 10mm tubes — prints on small beds',
    'halo-backlit': 'wall-glow: opaque letters, light fires BACKWARD onto the wall',
    'open-sign': 'the red OPEN — open-tube channel letters at true neon scale',
  };
  for (const [name, cfg] of Object.entries(meta.presets || {})){
    const b = document.createElement('button');
    b.className = 'mini ghost'; b.textContent = name;
    b.title = PRESET_TIPS[name] || '';
    b.onclick = () => applyPreset(cfg);
    $('presets').appendChild(b);
  }
  for (const p of Object.keys(meta.printers)){
    const o = new Option(`${p} (${meta.printers[p].bed[0]}×${meta.printers[p].bed[1]}${meta.printers[p].bridging === 'weak' ? ' · weak bridging' : ''})`, p);
    $('printer').appendChild(o);
  }
  $('printer').appendChild(new Option('custom bed…', 'custom'));
  $('printer').value = defaults.printer.preset;
  for (const s of meta.plaques) $('plaque').appendChild(new Option(s, s));
  for (const [name, pal] of Object.entries(meta.palettes)){
    const o = new Option(`${name}`, name);
    o.style.background = pal.shell; o.style.color = pal.lens;
    $('palette').appendChild(o);
  }
  $('palette').value = 'charge-classic';
}

async function refreshMe(){
  me = await (await fetch('/api/auth/me')).json();
  const authed = !!me.user;
  $('authmodal').classList.toggle('show', !authed && !me.open_mode);
  $('acctchip').hidden = !authed || me.open_mode;
  $('adminchip').hidden = !(authed && me.user.role === 'admin' && !me.open_mode);
  if (me.open_mode){ $('tierstamp').textContent = 'OPEN MODE'; }
  else if (authed){
    $('tierstamp').textContent = (me.user.role === 'admin' ? 'ADMIN' : me.user.tier.toUpperCase());
    $('acctemail').textContent = me.user.email;
  } else { $('tierstamp').textContent = 'SIGNED OUT'; }
}

/* ---------- params ---------- */
function applyPreset(cfg){
  const merged = JSON.parse(JSON.stringify(defaults));
  for (const [k, v] of Object.entries(cfg)){
    if (v && typeof v === 'object' && !Array.isArray(v)) Object.assign(merged[k] = merged[k] || {}, v);
    else merged[k] = v;
  }
  $('advanced').value = JSON.stringify(merged, null, 2);
  if (merged.content){
    if (merged.content.text) $('text').value = merged.content.text;
    if (merged.content.cap_height_mm) $('cap').value = merged.content.cap_height_mm;
  }
  if (merged.style){
    if (merged.style.kind) $('kind').value = merged.style.kind;
    if (merged.style.backer) $('backer').value = merged.style.backer;
    if (merged.style.backer_shape) $('plaque').value = merged.style.backer_shape;
  }
  if (merged.texture && merged.texture.mode) $('texture').value = merged.texture.mode;
  if (merged.leds && merged.leds.kind) $('leds').value = merged.leds.kind;
  if (merged.printer && merged.printer.preset) $('printer').value = merged.printer.preset;
  if (merged.colors && merged.colors.palette){
    $('palette').value = merged.colors.palette;
    syncPickersToPalette();
  }
  if (merged.style && merged.style.neon && merged.style.neon.channel_interior)
    $('tubewidth').value = merged.style.neon.channel_interior + 4;  // band = interior+walls
  else
    $('tubewidth').value = 22;
  schedule();
}

// ---- custom PLA colors: pickers track the palette until the user edits ----
const CKEYS = {lens:'c_lens', shell:'c_shell', liner:'c_liner', pixel:'c_pixel'};
let colorDirty = {};
function syncPickersToPalette(){
  const pal = (meta.palettes || {})[$('palette').value];
  if (!pal) return;
  colorDirty = {};
  for (const [k, id] of Object.entries(CKEYS)) $(id).value = pal[k];
}
function customColors(){
  const out = {};
  for (const [k, id] of Object.entries(CKEYS))
    if (colorDirty[k]) out[k] = $(id).value;
  return out;
}

// ---- FX preview: generic WLED-style effects on the real pixel layout ----
let fxNodes = [], fxRAF = null, fxBase = [];
function fxCollect(){
  fxNodes = [...document.querySelectorAll('#svgbox .px')].map(n => ({
    n, i: +n.dataset.i, x: +n.getAttribute('cx'), y: +n.getAttribute('cy'),
  }));
  fxBase = fxNodes.length ? fxNodes.map(p => p.n.getAttribute('fill')) : [];
  if (fxNodes.length){
    const xs = fxNodes.map(p => p.x), ys = fxNodes.map(p => p.y);
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const y0 = Math.min(...ys), y1 = Math.max(...ys);
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    const rmax = Math.max(...fxNodes.map(p => Math.hypot(p.x - cx, p.y - cy)), 1);
    fxNodes.forEach(p => {
      p.u = (p.x - x0) / Math.max(x1 - x0, 1);          // 0..1 across the sign
      p.r = Math.hypot(p.x - cx, p.y - cy) / rmax;      // 0..1 from center
    });
  }
}
function hsv(h, s, v){
  h = ((h % 1) + 1) % 1;
  const i = Math.floor(h * 6), f = h * 6 - i;
  const p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
  const rgb = [[v,t,p],[q,v,p],[p,v,t],[p,q,v],[t,p,v],[v,p,q]][i % 6];
  return '#' + rgb.map(c => Math.round(c * 255).toString(16).padStart(2, '0')).join('');
}
function shade(hex, k){
  const v = parseInt(hex.slice(1), 16);
  const f = c => Math.round(Math.max(0, Math.min(255, c * k))).toString(16).padStart(2, '0');
  return '#' + f(v >> 16) + f((v >> 8) & 255) + f(v & 255);
}
const FX = {
  solid:   (p, t, n, c) => c,
  breathe: (p, t, n, c) => shade(c, 0.25 + 0.75 * (0.5 + 0.5 * Math.sin(t * 2.2))),
  chase:   (p, t, n, c) => {
    const d = ((p.i - t * n * 0.25) % n + n) % n;
    return d < n * 0.12 ? shade(c, 1 - d / (n * 0.12)) : '#1c1c22';
  },
  rainbow: (p, t, n) => hsv(p.i / n + t * 0.15, 1, 1),
  sweep:   (p, t) => hsv(p.u * 0.7 + t * 0.25, 1, 1),
  pulse:   (p, t, n, c) => {
    const w = ((p.r - t * 0.35) % 1 + 1) % 1;
    return w < 0.25 ? shade(c, 1 - w / 0.25) : shade(c, 0.06);
  },
};
function fxTick(ts){
  const mode = $('fx').value;
  if (mode === 'off' || !fxNodes.length){ fxRAF = null; return; }
  const t = ts / 1000, n = Math.max(fxNodes.length, 1), c = $('fxcolor').value;
  for (const p of fxNodes) p.n.setAttribute('fill', FX[mode](p, t, n, c));
  fxRAF = requestAnimationFrame(fxTick);
}
function fxApply(){
  const mode = $('fx').value;
  $('fxcolor').hidden = !['solid', 'breathe', 'chase', 'pulse'].includes(mode);
  if (mode === 'off'){
    if (fxRAF) cancelAnimationFrame(fxRAF);
    fxRAF = null;
    fxNodes.forEach((p, i) => p.n.setAttribute('fill', fxBase[i]));
    return;
  }
  if (!fxRAF) fxRAF = requestAnimationFrame(fxTick);
}

function refreshRelevance(){
  const kind = $('kind').value;
  const neon = kind === 'neon';
  // options only show where they actually apply — v1 simplicity audit
  $('row-tubesource').hidden = !neon;
  // bullet pixels fix the channel at 18/22 — width is a knob for strip/unlit
  $('row-tubewidth').hidden = !neon || $('leds').value === 'bullet12';
  $('row-src').hidden = !neon;
  $('row-texture').hidden = !neon;
  $('row-texlens').hidden = !neon;
  $('row-texbacker').hidden = kind === 'halo' || $('backer').value === 'none';
  $('row-plaque').hidden = $('backer').value !== 'tile';
  const stripOpt = $('leds').querySelector('option[value=strip]');
  stripOpt.disabled = kind === 'channel';
  if (stripOpt.disabled && $('leds').value === 'strip') $('leds').value = 'none';
  $('row-pitch').hidden = $('leds').value !== 'bullet12';
}

function paramsFromUI(){
  refreshRelevance();
  let base;
  try {
    base = JSON.parse($('advanced').value);
    $('jsonbadge').textContent = 'VALID'; $('jsonbadge').className = 'badge ok';
  } catch {
    $('jsonbadge').textContent = 'ERROR'; $('jsonbadge').className = 'badge bad';
    base = JSON.parse(JSON.stringify(defaults));
  }
  base.name = $('name').value.trim() || 'sign';
  base.content = base.content || {};
  base.content.mode = (artToken || libraryPick) ? 'art' : 'text';
  base.content.text = $('text').value;
  base.content.cap_height_mm = +$('cap').value || 150;
  base.content.art_target_height_mm = +$('cap').value || 150;
  base.content.letter_spacing_mm = +$('tracking').value || 0;
  base.style = base.style || {};
  base.style.kind = $('kind').value;
  base.style.backer = $('backer').value;
  base.style.backer_shape = $('plaque').value;
  base.style.support_ribs = $('ribs').value;
  base.style.neon = base.style.neon || {};
  base.style.neon.source = $('tubesource').value;
  const tw = Math.max(8, Math.min(40, +$('tubewidth').value || 22));
  base.style.neon.channel_interior = Math.max(tw - 4, 4.5);  // band derives as interior+walls
  base.texture = base.texture || {};
  base.texture.mode = $('texture').value;
  const targets = [];
  if ($('tex_lens').checked) targets.push('lens');
  if ($('tex_backer').checked) targets.push('backer');
  base.texture.targets = targets.length ? targets : ['lens'];
  base.leds = base.leds || {};
  base.leds.kind = $('leds').value;
  base.leds.pitch_mm = Math.max(14, +$('pitch').value || 17);
  base.colors = base.colors || {};
  base.colors.palette = $('palette').value;
  const cc = customColors();
  if (Object.keys(cc).length) base.colors.custom = cc;
  base.printer = base.printer || {};
  if ($('printer').value === 'custom'){
    base.printer.preset = 'custom';
    base.printer.bed_x_mm = +$('bedx').value || 220;
    base.printer.bed_y_mm = +$('bedy').value || 220;
  } else {
    base.printer.preset = $('printer').value;
    delete base.printer.bed_x_mm; delete base.printer.bed_y_mm;
  }
  return base;
}

const payload = () => ({params: paramsFromUI(), font_token: fontToken,
                        font: fontToken ? null : fontPick,
                        art_token: artToken, library: artToken ? null : libraryPick});

/* ---------- preview ---------- */
function schedule(){ clearTimeout(timer); timer = setTimeout(preview, 450); }

async function preview(){
  if (!me || (!me.user && !me.open_mode)) return;
  $('statline').textContent = 'computing blueprint…';
  const r = await fetch('/api/preview2d', {method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload())});
  if (r.status === 401){ refreshMe(); return; }
  const data = await r.json();
  if (data.error){
    $('statline').innerHTML = `<span style="color:var(--danger)">✗ ${data.error}</span>`;
    return;
  }
  $('svgbox').innerHTML = data.svg;
  fxCollect();
  fxApply();
  const watts = data.watts ? ` · ${data.pixels} px · ${data.watts} W → ${data.psu} W PSU` : '';
  $('statline').textContent =
    `${data.sign_mm[0]} × ${data.sign_mm[1]} mm · ${data.pieces} piece(s)${watts}`;
  $('warnings').textContent = (data.warnings || []).slice(0, 8).map(w => '⚠ ' + w).join('\n');
}

/* ---------- uploads ---------- */
async function uploadFile(kind){
  const input = kind === 'font' ? $('fontfile') : $('artfile');
  const chip = kind === 'font' ? $('fontchip') : $('artchip');
  const f = input.files[0];
  if (!f) return;
  const fd = new FormData(); fd.append('file', f);
  const r = await fetch(`/api/upload?kind=${kind}`, {method:'POST', body: fd});
  if (!r.ok){ alert(await r.text()); input.value = ''; return; }
  const data = await r.json();
  if (kind === 'font'){
    fontToken = data.token;
    $('fontgrid').querySelectorAll('.ftile').forEach(x => x.classList.remove('sel'));
  }
  else {
    artToken = data.token;
    libraryPick = null;
    $('library').querySelectorAll('.tile').forEach(x => x.classList.remove('sel'));
  }
  chip.querySelector('span').textContent = '◈ ' + data.filename;
  chip.classList.add('show');
  schedule();
}

/* ---------- queue ---------- */
async function build(){
  $('buildbtn').disabled = true;
  const r = await fetch('/api/build', {method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload())});
  $('buildbtn').disabled = false;
  if (!r.ok){
    $('joblog').hidden = false;
    $('joblog').textContent = '✗ ' + (await r.text());
    return;
  }
  $('joblog').hidden = true;
  pollQueue(true);
}

async function pollQueue(force){
  clearTimeout(queueTimer);
  if (me && (me.user || me.open_mode)){
    const r = await fetch('/api/jobs');
    if (r.ok){
      const jobs = (await r.json()).jobs.reverse();
      renderQueue(jobs);
      const active = jobs.some(j => j.status === 'queued' || j.status === 'running');
      queueTimer = setTimeout(pollQueue, active ? 900 : 5000);
      return;
    }
  }
  queueTimer = setTimeout(pollQueue, 5000);
}

function renderQueue(jobs){
  const q = $('queue');
  if (!jobs.length){
    q.innerHTML = '<div class="hint">nothing queued yet — dial in a sign and hit BUILD KIT</div>';
    return;
  }
  q.innerHTML = '';
  for (const j of jobs){
    const card = document.createElement('div');
    card.className = 'jobcard';
    const pos = j.position ? ` · position ${j.position}` : '';
    const last = (j.progress || []).slice(-1)[0] || '';
    let links = '';
    const del = `<button class="mini ghost" data-del="${j.id}" title="remove from queue">✕</button>`;
    if (j.expired){
      links = `<div class="log">files expired (server restarted) — rebuild to regenerate</div>
               <div class="links">${del}</div>`;
    } else if (j.status === 'done'){
      links = `<div class="links">
        <a class="btn" href="/api/jobs/${j.id}/download">ZIP</a>
        <a class="btn ghost" target="_blank" href="/api/jobs/${j.id}/viewer">3D</a>
        <a class="btn ghost" target="_blank" href="/api/jobs/${j.id}/preview">DASHBOARD</a>
        ${del}
      </div>`;
    } else if (j.status === 'queued' || j.status === 'running'){
      links = `<div class="links"><button class="mini danger" data-cancel="${j.id}">CANCEL</button></div>`;
    } else {
      links = `<div class="links">${del}</div>`;
    }
    const err = j.error ? `<div class="log" style="color:var(--danger)">${j.error}</div>` : '';
    const thumb = (j.status === 'done' && !j.expired)
      ? `<img src="/api/jobs/${j.id}/thumb.png" alt="" loading="lazy">` : '';
    card.innerHTML = `${thumb}<div class="body">
      <div class="name">${j.name} <span class="state ${j.status}">${j.status.toUpperCase()}${pos}</span></div>
      <div class="log">${last}</div>${err}${links}</div>`;
    q.appendChild(card);
  }
  q.querySelectorAll('[data-cancel]').forEach(b =>
    b.onclick = async () => { await fetch(`/api/jobs/${b.dataset.cancel}`, {method:'DELETE'}); pollQueue(true); });
  q.querySelectorAll('[data-del]').forEach(b =>
    b.onclick = async () => { await fetch(`/api/jobs/${b.dataset.del}`, {method:'DELETE'}); pollQueue(true); });
  $('clearbtn').hidden = !jobs.some(j => j.expired || !['queued','running'].includes(j.status));
}

/* ---------- auth / account / admin ---------- */
async function authPost(url){
  $('autherr').textContent = '';
  const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({email: $('authemail').value, password: $('authpw').value})});
  if (!r.ok){ $('autherr').textContent = (await r.json()).detail || 'failed'; return; }
  await refreshMe(); schedule(); pollQueue(true);
}

async function showAccount(){
  const info = await (await fetch('/api/auth/me')).json();
  const L = info.limits || {};
  $('acctinfo').innerHTML =
    `OPERATOR&nbsp; ${info.user.email}<br>ROLE&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ${info.user.role}` +
    `<br>TIER&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ${info.user.tier}` +
    `<br>MAX SIZE&nbsp; ${L.max_cap_mm} mm<br>BUILDS&nbsp;&nbsp;&nbsp; ${info.builds_today}/${L.builds_per_day} today`;
  $('acctmodal').classList.add('show');
}

async function showAdmin(){
  const users = (await (await fetch('/api/admin/users')).json()).users;
  const t = $('usertable');
  t.innerHTML = '<tr><th>ID</th><th>EMAIL</th><th>ROLE</th><th>TIER</th><th></th></tr>';
  for (const u of users){
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${u.id}</td><td>${u.email}</td>
      <td><select data-role="${u.id}"><option${u.role==='user'?' selected':''}>user</option><option${u.role==='admin'?' selected':''}>admin</option></select></td>
      <td><select data-tier="${u.id}"><option${u.tier==='free'?' selected':''}>free</option><option${u.tier==='premium'?' selected':''}>premium</option></select></td>
      <td><button class="mini danger" data-del="${u.id}">DEL</button></td>`;
    t.appendChild(tr);
  }
  t.querySelectorAll('select[data-role]').forEach(s => s.onchange = () =>
    fetch(`/api/admin/users/${s.dataset.role}`, {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({role: s.value})}));
  t.querySelectorAll('select[data-tier]').forEach(s => s.onchange = () =>
    fetch(`/api/admin/users/${s.dataset.tier}`, {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({tier: s.value})}));
  t.querySelectorAll('[data-del]').forEach(b => b.onclick = async () => {
    await fetch(`/api/admin/users/${b.dataset.del}`, {method:'DELETE'}); showAdmin();
  });
  $('adminmodal').classList.add('show');
}

/* ---------- wiring ---------- */
function wireEvents(){
  for (const id of ['text','cap','tracking','kind','backer','plaque','palette','texture',
                    'tubesource','tex_lens','tex_backer','leds','pitch','printer',
                    'ribs','name','bedx','bedy'])
    $(id).addEventListener('input', () => {
      if (id === 'printer') $('bedrow').hidden = $('printer').value !== 'custom';
      schedule();
    });
  $('advanced').addEventListener('input', schedule);
  $('fontfile').addEventListener('change', () => uploadFile('font'));
  $('artfile').addEventListener('change', () => uploadFile('art'));
  $('fontchip').querySelector('button').onclick = () => { fontToken = null; $('fontfile').value=''; $('fontchip').classList.remove('show'); schedule(); };
  $('artchip').querySelector('button').onclick = () => { artToken = null; $('artfile').value=''; $('artchip').classList.remove('show'); schedule(); };
  $('buildbtn').onclick = build;
  $('clearbtn').onclick = async () => { await fetch('/api/jobs/clear', {method:'POST'}); pollQueue(true); };
  $('wires').checked = localStorage.getItem('sf-wires') === '1';
  $('svgbox').classList.toggle('hidewires', !$('wires').checked);
  $('wires').onchange = () => {
    localStorage.setItem('sf-wires', $('wires').checked ? '1' : '0');
    $('svgbox').classList.toggle('hidewires', !$('wires').checked);
  };
  $('srcart').checked = localStorage.getItem('sf-src') !== '0';
  $('svgbox').classList.toggle('hidesrc', !$('srcart').checked);
  $('srcart').onchange = () => {
    localStorage.setItem('sf-src', $('srcart').checked ? '1' : '0');
    $('svgbox').classList.toggle('hidesrc', !$('srcart').checked);
  };
  $('fx').onchange = fxApply;
  // debug/screenshot hooks: #fx=rainbow, #preset=open-sign
  const hash = new URLSearchParams(location.hash.slice(1));
  if (hash.get('fx')) $('fx').value = hash.get('fx');
  if (hash.get('preset') && meta.presets[hash.get('preset')])
    applyPreset(meta.presets[hash.get('preset')]);
  $('palette').addEventListener('change', syncPickersToPalette);
  syncPickersToPalette();
  for (const [k, id] of Object.entries(CKEYS))
    $(id).addEventListener('input', () => { colorDirty[k] = true; schedule(); });
  $('loginbtn').onclick = () => authPost('/api/auth/login');
  $('registerbtn').onclick = () => authPost('/api/auth/register');
  $('acctchip').onclick = showAccount;
  $('adminchip').onclick = showAdmin;
  $('logoutbtn').onclick = async () => { await fetch('/api/auth/logout', {method:'POST'}); $('acctmodal').classList.remove('show'); refreshMe(); };
  $('adminclose').onclick = () => $('adminmodal').classList.remove('show');
  for (const m of ['acctmodal','adminmodal'])
    $(m).addEventListener('click', e => { if (e.target === $(m)) $(m).classList.remove('show'); });
}

init();
