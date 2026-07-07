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
  for (const [name, cfg] of Object.entries(meta.presets || {})){
    const b = document.createElement('button');
    b.className = 'mini ghost'; b.textContent = name;
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
  schedule();
}

function refreshRelevance(){
  const kind = $('kind').value;
  const neon = kind === 'neon';
  // options only show where they actually apply — v1 simplicity audit
  $('row-tubesource').hidden = !neon;
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
