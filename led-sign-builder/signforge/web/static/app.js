'use strict';
const $ = id => document.getElementById(id);
let fontToken = null, artToken = null, defaults = null, timer = null, currentJob = null;

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
  }
  if (merged.texture && merged.texture.mode) $('texture').value = merged.texture.mode;
  if (merged.leds && merged.leds.kind) $('leds').value = merged.leds.kind;
  if (merged.printer && merged.printer.preset) $('printer').value = merged.printer.preset;
  schedule();
}

async function init(){
  const r = await fetch('/api/presets'); const data = await r.json();
  defaults = data.defaults;
  for (const [name, cfg] of Object.entries(data.presets || {})){
    const b = document.createElement('button');
    b.className = 'mini'; b.style.marginRight = '6px'; b.textContent = name;
    b.onclick = () => applyPreset(cfg);
    $('presets').appendChild(b);
  }
  for (const p of data.printers){
    const o = document.createElement('option'); o.value = p; o.textContent = p;
    if (p === defaults.printer.preset) o.selected = true;
    $('printer').appendChild(o);
  }
  $('advanced').value = JSON.stringify(defaults, null, 2);
  for (const id of ['text','cap','kind','backer','texture','leds','pitch','budget','printer','name'])
    $(id).addEventListener('input', schedule);
  $('fontfile').addEventListener('change', () => uploadFile('font'));
  $('artfile').addEventListener('change', () => uploadFile('art'));
  $('artclear').addEventListener('click', () => { artToken = null; $('artfile').value=''; $('artclear').hidden = true; schedule(); });
  $('advanced').addEventListener('input', schedule);
  $('buildbtn').addEventListener('click', build);
  schedule();
}

function paramsFromUI(){
  let base;
  try { base = JSON.parse($('advanced').value); }
  catch { base = JSON.parse(JSON.stringify(defaults)); }
  base.name = $('name').value.trim() || 'sign';
  base.content = base.content || {};
  base.content.mode = artToken ? 'art' : 'text';
  base.content.text = $('text').value;
  base.content.cap_height_mm = +$('cap').value || 150;
  base.content.art_target_height_mm = +$('cap').value || 150;
  base.style = base.style || {};
  base.style.kind = $('kind').value;
  base.style.backer = $('backer').value;
  base.texture = base.texture || {};
  base.texture.mode = $('texture').value;
  base.leds = base.leds || {};
  base.leds.kind = $('leds').value;
  base.leds.pitch_mm = +$('pitch').value || 17;
  base.leds.budget_px = $('budget').value ? +$('budget').value : null;
  base.printer = base.printer || {};
  base.printer.preset = $('printer').value;
  return base;
}

function payload(){
  return {params: paramsFromUI(), font_token: fontToken, art_token: artToken};
}

async function uploadFile(kind){
  const input = kind === 'font' ? $('fontfile') : $('artfile');
  const f = input.files[0];
  if (!f) return;
  const fd = new FormData(); fd.append('file', f);
  const r = await fetch(`/api/upload?kind=${kind}`, {method:'POST', body: fd});
  if (!r.ok){ alert(await r.text()); input.value=''; return; }
  const data = await r.json();
  if (kind === 'font') fontToken = data.token;
  else { artToken = data.token; $('artclear').hidden = false; }
  schedule();
}

function schedule(){
  clearTimeout(timer);
  timer = setTimeout(preview, 450);
}

async function preview(){
  $('statline').textContent = 'planning…';
  const r = await fetch('/api/preview2d', {method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload())});
  const data = await r.json();
  if (data.error){
    $('statline').innerHTML = `<span class="err">${data.error}</span>`;
    return;
  }
  $('svgbox').innerHTML = data.svg;
  const watts = data.watts ? ` · ${data.pixels} px · ${data.watts} W → ${data.psu} W PSU` : '';
  $('statline').textContent =
    `${data.sign_mm[0]} × ${data.sign_mm[1]} mm · ${data.pieces} piece(s)${watts}`;
  $('warnings').textContent = (data.warnings || []).map(w => '⚠ ' + w).join('\n');
}

async function build(){
  $('buildbtn').disabled = true;
  $('joblog').hidden = false; $('joblog').textContent = 'starting…';
  $('jobactions').hidden = true;
  const r = await fetch('/api/build', {method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload())});
  if (!r.ok){ $('joblog').textContent = await r.text(); $('buildbtn').disabled = false; return; }
  currentJob = (await r.json()).job;
  poll();
}

async function poll(){
  const r = await fetch(`/api/jobs/${currentJob}`);
  const job = await r.json();
  $('joblog').textContent = (job.progress || []).map(m => '· ' + m).join('\n');
  if (job.status === 'done'){
    $('joblog').textContent += '\n✓ done';
    $('dl').href = `/api/jobs/${currentJob}/download`;
    $('v3d').href = `/api/jobs/${currentJob}/viewer`;
    $('vprev').href = `/api/jobs/${currentJob}/preview`;
    $('jobactions').hidden = false;
    $('buildbtn').disabled = false;
    if (job.warnings && job.warnings.length)
      $('warnings').textContent = job.warnings.map(w => '⚠ ' + w).join('\n');
  } else if (job.status === 'error'){
    $('joblog').textContent += '\n✗ ' + job.error;
    $('buildbtn').disabled = false;
  } else {
    setTimeout(poll, 700);
  }
}

init();
