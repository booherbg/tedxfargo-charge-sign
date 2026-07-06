# LED Sign Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline; this run is autonomous and the executor holds full context — subagents are used only for separable leaf tasks: asset fetching, torture fixtures, web static). Steps use checkbox syntax. **Deviation from writing-plans:** full code blocks appear only where a decision is subtle; elsewhere the plan locks exact paths/signatures/tests and cites the CHARGE source lines being ported (the executor has the repo; stale copies are worse than citations).

**Goal:** Ship a working generic LED Sign Builder (library + CLI + web UI) that turns text/fonts/vector/raster art into verified, print-ready multi-material sign kits with previews and a zip bundle.

**Architecture:** Pure-Python pipeline: ingest → Artwork (2D) → Layout → TubePlan/fills → LedPlan → panelize → per-piece Bodies (manifold3d solids) → verify gates → export (STL/3MF/preview/BOM/zip). Web/CLI are thin clients of `pipeline.build()`.

**Tech Stack:** Python 3.12 (uv-managed), numpy, shapely≥2, manifold3d, fontTools, svgelements, ezdxf, Pillow, pydantic v2, FastAPI+uvicorn (web), pytest+httpx (tests), vendored three.js (viewer). No external binaries, no network at runtime.

## Global Constraints

- Everything lives under `led-sign-builder/` on branch `led-sign-builder`; never modify files outside it.
- All dimensions mm, +Z = print-up; parts emit in print orientation (lens-up); flip-to-use parts pre-mirrored (chiral lesson).
- Every exported mesh passes `verify.audit_mesh` — hard fail, no warn-only (lesson 10).
- Generated geometry never kisses a boolean partner's plane: standoff ≥0.02 mm (lesson 9); welds use fuse overlap 0.1 mm.
- CHARGE-validated defaults everywhere (constants table in `docs/LESSONS-FROM-CHARGE.md` §C).
- `uv run pytest` green before every commit; commit per task with `feat:`/`test:`/`docs:` prefixes.
- No outbound network calls in library/web code paths. Test-asset downloads happen once, committed with licenses.

---

## Phase 0 — Scaffold

### Task 0.1: Package skeleton + env + docs shell
**Files:** Create `led-sign-builder/pyproject.toml`, `signforge/__init__.py`, `tests/test_smoke.py`, `README.md`, `CLAUDE.md`, `HANDOFF.md`, `.gitignore`, `docs/LESSONS-FROM-CHARGE.md`.
- [ ] `uv venv --python 3.12 .venv`; deps in pyproject: numpy, shapely>=2.0, manifold3d>=3.0, fonttools>=4.50, svgelements, ezdxf, pillow, pydantic>=2, fastapi, uvicorn, python-multipart; dev: pytest, httpx.
- [ ] `tests/test_smoke.py`: import manifold3d, build a cube ∪ sphere, assert `.status() == OK` and volume > 0 (proves wheels work).
- [ ] Run `uv run pytest` → PASS. Commit: `feat: scaffold signforge package, env, docs shell`.

## Phase 1 — Foundation (params, 2D, solids, gate, STL)

### Task 1.1: `signforge/params.py` — full parameter schema
**Produces (exact):** `SignParams(BaseModel)` with sub-models `ContentParams` (mode:"text"|"art", text, font_path, cap_height_mm=250.0, letter_spacing_mm=0.0, line_spacing=1.2, align:"left"|"center"|"right", art_path, art_target_height_mm=250.0, trace_threshold=128, invert=False), `StyleParams` (kind:"neon"|"channel", backer:"tile"|"contour"|"none"="tile", tile_margin_mm=12.0, contour_margin_mm=8.0, neon:NeonSection, channel:ChannelSection), `NeonSection` (channel_interior=18.0, liner_wall=0.8, outer_wall=1.2, plate_t=2.0, liner_floor_t=0.4, wall_height=19.0, lens_t=1.2), `ChannelSection` (plate_t=2.4, wall_t=1.6, wall_height=30.0, lens_t=1.5, lip_depth=3.0, lip_clear=-0.2, counter_mode:"glow"|"open"="glow"), `LedParams` (kind:"bullet12"|"none"="bullet12", pitch_mm=17.0, min_chord_mm=14.8, flange_floor_mm=14.5, seam_keepout_mm=12.5, bore_mm=12.3, collar=True, collar_od_mm=16.0, collar_h_mm=2.0, volts=24.0, watts_per_px=0.25, psu_headroom=0.8, budget_px:int|None=None, grid_pitch_mm=40.0), `TextureParams` (mode:"none"|"random"|"pyramid"|"pyramid_jitter"="pyramid_jitter", cell_mm=2.0, height_mm=0.6, seed=7, standoff_mm=0.02, sample_div=3), `FitParams` (seam_clearance_mm=0.06, fuse_mm=0.1, min_feature_mm=0.8), `PrinterParams` (preset="bambu-h2d-dual", bed_x_mm/bed_y_mm optional override; PRESETS dict incl. ("bambu-h2d-dual",316,295), ("bambu-x1c",256,256), ("bambu-a1",256,256), ("prusa-mk4",250,210), ("ender-3",220,220)), `ColorParams` (extruders {"shell":1,"liner":2,"lens":3}, preview hex map), `OutputParams` (stl/threemf/preview/bom/debug_overlays all True). Plus `schema_version:int=1`, `SignParams.model_validate_json`, presets: `PRESET_PARAMS = {"neon-classic":…, "channel-bold":…, "mini-desk":…}`.
- [ ] Tests `tests/test_params.py`: defaults valid; round-trip json; unknown preset raises; bed override wins. Commit `feat: parameter schema with CHARGE-validated defaults`.

### Task 1.2: `signforge/geom2d.py` — healing + bands
**Produces:** `heal(geom)->MultiPolygon` (shapely make_valid+buffer(0)+orient, drops slivers < min_feature² area), `band(strokes:list[Stroke], width:float)->MultiPolygon` (round-cap/round-join buffer of LineString/LinearRing — the `path_stroke`/`band` port of `src/parts/piece.scad:36-41`), `ring_offset(mpoly, delta)->MultiPolygon`, `rings(mpoly)->list[np.ndarray]` (CCW shells, CW holes — manifold3d CrossSection convention), `Stroke` dataclass (pts, width|None, closed). 
- [ ] Tests: self-intersecting bowtie heals to valid; band of L-polyline ≈ analytic area (len·w + π(w/2)² within 2%); closed ring band has hole; rings orientation. Commit.

### Task 1.3: `signforge/solids.py` — manifold-by-construction builders
**Produces:** `prism(mpoly, z0, z1)->Manifold` (CrossSection→extrude→translate), `heightfield(grid:np.ndarray, cell:float, origin:(x,y), z_base:float)->Manifold` (closed solid: displaced top grid + skirt + flat bottom, built as triangle mesh → `Manifold(mesh)`; grid values are heights ABOVE z_base; degenerate-free by construction), `revolve_profile(profile_pts, cx, cy, z0)->Manifold` (for collars: lathe of 2D profile — manifold3d `Manifold.revolve` of CrossSection, then translate), `mesh_of(man)->(verts f32[n,3], tris i32[m,3])`, `cylinder(d, h, cx, cy, z0)`.
- [ ] Tests: prism volume exact for square/donut; heightfield watertight via audit (Task 1.4 dep — write audit first inside test as import), revolve collar volume ≈ analytic ring. Commit.

### Task 1.4: `signforge/verify.py` (part 1) — the hard manifold gate
**Produces:** `audit_mesh(verts, tris, name:str)->None` raising `BuildError` — port of `tools/make_3mf.py:102-117` (every undirected edge exactly 2 tris, no degenerate tris; operate on POSITION-welded mesh: quantize verts to 1e-6, weld, then audit so we catch T-junctions the way Bambu would). Also `BuildError(Exception)`.
- [ ] Tests: cube passes; cube missing a face fails; two cubes sharing an edge (pinch) fails; degenerate tri fails. Commit.

### Task 1.5: `signforge/export/stl.py`
**Produces:** `write_stl(path, verts, tris)` binary little-endian; `read_stl(path)->(verts,tris)` (binary + ascii, for tests/viewer); round-trip test + audit gate integration (`export_mesh(path, man, name)` = mesh_of→audit→write). Commit.

## Phase 2 — P0 e2e: text → channel-letter sign → STL zip

### Task 2.1: `signforge/ingest/fonts.py`
**Produces:** `load_font(path)->Font` (fontTools TTFont; TTF/OTF/WOFF/WOFF2 via fontTools built-in woff support), `text_to_artwork(font, text, cap_height_mm, letter_spacing_mm, line_spacing, align)->Artwork` — glyph outlines via `fontTools.pens.recordingPen` + quad/cubic flattening (adaptive, ≤0.1 mm sagitta at final scale), advances + `kern` table pair kerning when present, per-glyph shapely polygons healed & unioned per glyph, scaled so cap height (H of 'H' if present else ascender) = cap_height_mm, multi-line with align. `Artwork` dataclass in `signforge/model.py`: `fills: MultiPolygon|None, strokes: list[Stroke], glyphs: list[GlyphBox(char, poly, bbox)], bbox, source:str`.
- [ ] Tests (fixture font: download OFL font in Task 2.0-lite — instead: generate a fixture with fontTools? NO — use committed OFL fonts; see Task 6.1; for now vendor ONE small OFL font `tests/assets/fonts/` fetched during this task with its LICENSE) — 'HELLO' produces 5 glyph groups, 'O' has a hole, cap height within 0.5 mm, kerning shifts 'AV' closer than 'AA'. Commit.

### Task 2.2: `signforge/layout.py`
**Produces:** `build_layout(artwork, params)->Layout` — `Layout(fills, strokes, tile: Polygon|None, bbox, pieces:list[Piece]|None=None)`; positions art at origin+margins, builds tile rect (bbox+tile_margin) or contour backer (`ring_offset(fills, contour_margin)`) or none; weld option implicit (fills already unioned). Tests: tile bounds = art bbox+2·margin; contour contains fills. Commit.

### Task 2.3: `signforge/parts/channel.py`
**Produces:** `build_channel_bodies(layout, pixels, params)->list[Body]`; `Body(name, man:Manifold, extruder:int, color:str)` in model.py. Geometry (all from filled letter mpoly `F`, walls both perimeter+counters): shell(black) = backer plate prism(0,plate_t) [tile rect or contour or F] − pixel bores + wall ring prism(plate_t−fuse, plate_t+wall_height) where ring = F − F.buffer(−wall_t); liner(white, only if leds) = floor band F.buffer(−wall_t) prism(plate_t−fuse, plate_t+liner_floor_t) − bores + collars at pixels; lens(clear) = F.buffer(lip_clear... careful: face plate F prism(plate_t+wall_height−fuse, +lens_t) + lip ring (F.buffer(−wall_t)+lip_clear interference→ F.buffer(−wall_t−0.0+lip_clear? define: lip outer = wall interior + lip_clear) prism dropping lip_depth into cavity; counter_mode "open" subtracts counters from lens. Backer "tile": shell plate = tile rect; letters' walls sit on it.
- [ ] Tests: HELLO channel bodies — every body passes audit; volumes > 0; lens bbox ⊆ walls bbox+ε; counters intact ('O' wall count = 2 rings → wall solid genus check via volume vs analytic band area·h within 5%). Commit.

### Task 2.4: `signforge/pipeline.py` + `signforge/cli.py` — FIRST E2E
**Produces:** `build(params, outdir, progress=None)->BuildResult(files:list[Path], stats:dict, warnings:list[str])` — orchestrates ingest→layout→(leds later: pixels=[])→bodies→audit→export per piece (single piece pre-panelize: name "piece1"); `cli.py` argparse: `signforge build params.json|--text HELLO --font f.ttf --style channel -o out/`, `signforge demo`, entry point in pyproject `[project.scripts] signforge = "signforge.cli:main"`.
- [ ] E2E test `tests/test_e2e_channel.py`: text HELLO + fixture font → ≥2 STLs exist, all audited, stats has watts=0 (no leds yet). Run `uv run signforge build --text HI ...` manually once. Commit `feat: first end-to-end channel-letter build`.

## Phase 3 — P0 finish: 3MF + bundle + preview v1

### Task 3.1: `signforge/export/threemf.py` — Bambu multi-filament port
Port `tools/make_3mf.py:124-190` templates exactly (Content_Types, rels, 3dmodel.model with parent components object, `Metadata/model_settings.config` with per-part `extruder` metadata, ID12/ID16 matrices). Input: `list[(name, verts, tris, extruder)]` — already-manifold indexed meshes (no ASCII weld needed; audit is upstream). Test: zip members present; XML parses; extruder values 1..3; open in slicer deferred to user note. Commit.

### Task 3.2: `signforge/export/bundle.py` + BOM
**Produces:** `build_bundle(params, build_result, outdir)->Path(zip)`: `<name>.zip` = stl/…, 3mf/…, preview/index.html(+assets), BOM.md (pixel count, wire chain length, PSU recommendation W = count·watts_per_px/headroom → next standard size of [60,100,150,200,350]W, filament weights via mesh volume · 1.27 g/cm³ PETG default, print-card notes incl. bottom-shells+1 lens note, Import-not-Open Bambu note), params.json (exact reproducibility), LICENSES.txt when bundled fonts used. Test: zip round-trip, BOM contains PSU line. Commit.

### Task 3.3: `signforge/preview/html.py` v1 — 2D SVG page
Port the `gen_cutpreview.py` visual language (round-capped tube strokes / filled letter paths, piece outlines, pixel circles, screw markers, per-piece table incl. grams + px + bed fit, totals row; self-contained inline SVG+CSS, zero JS). `render_preview(build_result, params)->str`. Test: valid XML, contains N piece groups. Commit. **← P0 COMPLETE: text→channel→zip(stl+3mf+preview+bom)**

## Phase 4 — Neon style (the CHARGE look)

### Task 4.1: `signforge/raster.py` + `signforge/skeleton.py`
**Produces:** `rasterize(mpoly, px_per_mm)->np.ndarray(bool)` scanline fill (port `qa_coverage.py:74-86` even-odd approach, numpy row batching); `skeletonize(ink)->set[(x,y)]` Zhang-Suen (port `centerline.py:66-94` — numpy neighbor-count vectorized per pass, keep exact rules); `extract_centerlines(mpoly, px_per_mm=2.4, spur_mm=6.0, rung_mm=9.0, min_path_mm=30.0, smooth_mm=2.0, step_mm=4.0)->list[Stroke]` (port decompose/smooth/resample `centerline.py:117-267` INCLUDING straightest-continuation pairing dot<0.3 and staircase-cluster rule); `debug_overlay(ink, skel, strokes, pixels, path)` → PNG via Pillow (lesson 14: "always eyeball it").
- [ ] Tests: ring polygon → 1 closed stroke ≈ centerline radius; 'S'-bar → 1 open stroke; two kissing bars → 2 pass-through strokes (junction pairing); T-junction spur < 6 mm dropped. Commit.

### Task 4.2: `signforge/parts/neon.py`
Port `src/parts/piece.scad:45-91` in shapely/manifold: bands at widths interior/interior+2·liner/outer=interior+2(liner+outer); shell(black)= plate(backer tile|contour of band_out+margin) − collar_od bores + outer wall ring prism; liner(white)= floor band(interior) − bore holes prism(liner_floor_t) + liner ring + collars (revolve: OD16 bore 12.19→11.44 lip, chamfer 0.5); lens(clear)= band_out prism(lens_t) at wall top −fuse weld + texture (Phase 5 hook: `texture_top(lens_man, band_mpoly, params)`). Piece mask clipping with `offset(−seam_clearance)` (`piece.scad:42-43`).
- [ ] Tests: strokes of 'S' curve → 3 bodies all audit-pass; liner ⊂ shell channel; lens covers band within coverage QA (Task 4.4). Commit.

### Task 4.3: `signforge/leds.py`
**Produces:** `place_pixels(strokes, params)->LedPlan(pixels, per_stroke:list[list[int]], audits, power:PowerPlan)`: resample at pitch (port `centerline.py:248-267` ends-included), then **pinned-end relaxation** (lesson 18): iterate pixels along each stroke to equalize CHORD spacing, enforce flange_floor between ALL pairs (cross-stroke too — port `make_repairs.py:186-195` audit), report snug pairs 13.0–14.5 and worst gap; `power()`: count·watts_per_px, amps@volts, PSU pick with headroom, strings-of-50 note, budget check vs budget_px (WARN line, lesson 19); chain order = stroke order with jumper flags >101.6 mm links.
- [ ] Tests: straight 170 mm → 11 px evenly; circle Ø100 → chords ≥ min; two parallel close strokes → audit flags; power math exact. Commit.

### Task 4.4: `signforge/verify.py` (part 2) — clearance + coverage
`clearance_audit(strokes, band_out)->list[Finding]` port of `tools/clearance_audit.py` rules (min centerline gap = band_out+4; crisp-crossing exemption ≥25°; parallel "mush" runs flagged); `coverage_qa(source_mpoly, band_mpoly, max_mm2=100)->list[Cluster]` (shapely difference + polygon clustering — simpler & exact vs raster port; keep mm² threshold semantics + FAIL/note split at 60 mm²); wire both into pipeline for neon builds (warnings list; coverage FAIL → BuildError unless params override). Auto-kern v1: if glyph bands overlap after widening, nudge apart along x by overlap+1 mm (lesson 16), re-run. Tests: amputated-arm scenario (delete a stroke from a glyph) → coverage FAIL; kissing 'rn' auto-kerns. Commit.

## Phase 5 — Textures, panelize, previews

### Task 5.1: `signforge/textures.py`
Port `tools/make_fuzz.py` all modes with the anti-sliver canon (floor 0.02, float field standoff above lens plane, max-union 3×3 tents, sample at cell/sample_div, per-piece seed = seed+piece_index): `fuzz_grid(mode, cell, hmax, seed, area_xy)->np.ndarray`; `textured_lens(band_mpoly, z_top, params, piece_seed)->Manifold` = heightfield(grid, origin at band bbox, z_base=z_top−standoff... construction: lens prism to z_top−standoff ∪ (heightfield solid ∩ band prism) with 0.1 fuse — but PREFER single-mesh construction: build lens as prism whose top face IS the displaced grid clipped to band via grid-cell masking, sidewalls stitched; fall back to Manifold boolean (guaranteed manifold) if stitching is fiddly — decide in-task, audit gate decides who wins.
- [ ] Tests: grid invariants (min ≥ floor+standoff for pyramid modes, max ≤ hmax+standoff), textured lens audits clean for 3 seeds × 2 modes, volume between plain lens and lens+hmax slab. Commit.

### Task 5.2: `signforge/panelize.py`
v1: rotate-to-fit (90°) then guillotine: candidate straight cuts on a 5 mm grid scored by (tube crossings, crossing angle ≥25°, distance from pixels ≥ seam_keepout, corner keepout 15 mm) — lesson 17's legality gate with straight seams only (corridor/piecewise = P2); apply seam_clearance per face via mask offset; per-piece labels (embossed mirrored on back — `piece.scad:52-53` port; labels also into previews, lesson 27); screws Ø4.5 at 12 mm corner insets + mid-span >160 mm (port `5b9d695` semantics); bed-fit hard check.
**Produces:** `panelize(layout, tubeplan, ledplan, params)->list[Piece(name,label,mask,bbox,rot,screws,pixel_idx)]`.
- [ ] Tests: small sign → 1 piece untouched; 600 mm word on 316×295 → ≥2 pieces, all fit bed, no pixel within keepout of seams, masks tile the footprint. Commit.

### Task 5.3: Preview v2 — full dashboard + 3D viewer
`preview/html.py`: add per-piece detail figures, totals (filament g by color, px count vs budget, PSU), debug overlay thumbnails; `preview/static/three.module.min.js` (vendored, one-time download, LICENSE committed) + `viewer.js` (custom binary-STL parser → BufferGeometry, per-body colors, exploded slider, orbit); `viewer.html` template embedding piece STL paths relative in zip. Test: html contains model list JSON; viewer.js parses a written STL fixture in node? (no node — parse test in Python mirror impl; JS smoke-checked in browser by user later; keep JS tiny & defensive). Commit.

## Phase 6 — Breadth: ingest formats, web app, fixtures, polish

### Task 6.1: Test assets + `ingest/svg.py` + `ingest/dxf.py` + `ingest/raster_img.py`
- Assets (committed with licenses): 3–4 OFL fonts (e.g. Oswald/Bungee/Pacifico/Orbitron from google/fonts raw — script `tests/assets/fetch_assets.sh` documents provenance, run ONCE now), torture SVGs (self-intersecting star, nested holes donut-in-donut, open path, stroked neon path w/ width, script-font-like overlaps, tiny slivers), a DXF (ezdxf-generated polyline logo), a PNG logo (Pillow-drawn bolt).
- `svg.py`: svgelements parse; filled shapes → fills (fill-rule aware); stroked paths (stroke!=none) → Stroke(width=stroke-width). viewBox units → mm (assume 96 dpi unless width/height in mm/cm/in), `art_target_height_mm` rescale.
- `dxf.py`: LWPOLYLINE/POLYLINE/LINE/ARC/CIRCLE/SPLINE (flattening=0.1 mm) → closed loops to fills, open chains to strokes(width=None → neon uses channel_interior).
- `raster_img.py`: Pillow load, threshold+invert, marching squares (implement, 8-connected, sub-pixel lerp) → simplified healed fills; min blob area.
- [ ] Tests per format → Artwork sane; e2e matrix test `test_e2e_matrix.py`: {font, svg-fill, svg-stroke, dxf, png} × {neon, channel} → bundle builds, audits pass (10 combos, mark slow). Commit per sub-module.

### Task 6.2: `signforge/web/app.py` + static UI
FastAPI: `GET /` (static), `POST /api/upload` (font|art, size caps 5/20 MB, returns token), `GET /api/presets`, `POST /api/preview2d` (params JSON → SVG string, <100 ms target: layout+tubes only, no solids), `POST /api/build` → job id (ThreadPoolExecutor(2), progress callback → dict), `GET /api/jobs/{id}`, `GET /api/jobs/{id}/download` (zip FileResponse), `GET /api/jobs/{id}/piece/{n}.stl` (viewer feed). Static `index.html+app.js+style.css`: upload/pick bundled font, textarea, grouped param panel from pydantic schema (auto-generated controls), live 2D SVG preview (debounced), 3D tab per piece, Generate→progress→download. `signforge serve` CLI.
- [ ] Tests httpx: upload→preview2d→build→poll→download zip round-trip on tiny text. Commit.

### Task 6.3: Fit-ladder coupon generator (lesson 1, product feature)
`signforge/coupons.py`: `fit_ladder(joint:"lens-lip"|"panel", values=[-0.3..0.1 step 0.1], params)->Bodies` — small labeled slices of the REAL joint cross-section (debossed value text via glyph outlines from bundled font), one plate; CLI `signforge coupon --joint lens-lip`. Test: 6 bodies audit, labels distinct. Commit.

### Task 6.4: Polish + docs + handoff
README (quickstart: uvx/uv run, web screenshot-less walkthrough, trust model note), CLAUDE.md (build/test commands, architecture map, porting-source pointers, constraints), examples/ (3 params.json presets + `make_examples.sh`), LESSONS doc final, HANDOFF.md final state, version 0.1.0, `uv run pytest` full green. Commit `docs: v0.1.0 handoff`.

## Self-review (spec coverage)
Spec §1 artifacts → Tasks 3.1-3.3, 5.3; §5 styles both → 2.3/4.2; ingest matrix → 2.1/6.1; §6 params → 1.1; §7 web → 6.2; §8 tests → every task + 6.1 matrix; textures → 5.1; leds → 4.3; panelize → 5.2; verification → 1.4/4.4; coupons (lesson 1) → 6.3; EPS = P2 (documented in README as "convert to SVG first"). Types cross-checked: Stroke/Artwork/Layout/Body/Piece/LedPlan defined once in model.py §2.1/2.3/4.3/5.2 and referenced consistently. No placeholders remain; corridor-cut piecewise seams, relaxation parity beyond v1, halo style, keyholes, .scad export explicitly deferred to P2 (spec §9).
