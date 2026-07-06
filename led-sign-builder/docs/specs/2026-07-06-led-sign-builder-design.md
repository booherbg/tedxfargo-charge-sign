# LED Sign Builder — Design Spec

**Date:** 2026-07-06 · **Status:** approved-for-build (autonomous mode, see §12) · **Working title:** LED Sign Builder (package codename `signforge`)

## 1. What this is

A generic, self-hostable tool that turns **text + a font file** (or an uploaded **SVG / DXF / PNG logo**) into a complete, print-ready **LED sign kit**:

- Parameterized, multi-material 3D-printable parts (STL per body + Bambu-ready multi-filament 3MF per piece)
- Automatic LED pixel layout with spacing rules, wiring order, and PSU sizing
- Panelization into printer-bed-sized pieces with seam clearances
- A self-contained offline **HTML preview** (2D cut layout + 3D viewer) — no CDN, no network
- A **zip bundle** of everything, reproducible from an included `params.json`
- A local **web UI** (upload → customize → preview → download). Pure local software; **zero external API dependencies**.

It is the generic extraction of the TEDxFargo **CHARGE** sign pipeline (this repo), which was proven end-to-end: 65 commits, V1→V9 iterations, physical prints validated on a Bambu H2D.

## 2. Users and jobs

- **Maker with a printer**: "Type my word, pick a font and style, print a glowing sign."
- **Small shop / power user**: upload brand vector art, tune every constant, get production files + BOM.
- **Developer**: `pip install`-able library + CLI; the web UI is a thin layer over the same pipeline.

## 3. Provenance: what CHARGE proved (and this tool encodes)

The validated recipe (see `docs/LESSONS-FROM-CHARGE.md` and the source repo's `docs/locked-specs.md`):

- **Diffusion win**: white reflective interior + ~15 mm air gap + chunky clear lens with **baked** fuzzy top (slicer fuzzy-skin can't texture top faces). Print lens-up, no supports.
- **Cross-section (neon tube)**: 18 mm channel interior / 22 mm outer band = 0.8 mm white liner wall + 1.2 mm black outer wall per side; plate 2.0 mm; wall height = dome_clear (4.0) + gap (15); lens 1.2 mm, welded with 0.1 mm fuse overlap.
- **Bullet pixel datasheet** (12 mm WS2811-style): dome Ø8, barrel Ø12, flange Ø13.6×2; bore 12.3 mm; press-fit collar; pitch ~17 mm arc / ≥14.8 mm chord for solid-tube glow; relaxation solver beats greedy placement.
- **Textures**: V3 random heightfield (1.5 mm cell / 0.8 mm) and V8 jittered pyramid facets (winner) — with anti-sliver rules: height floor, dead-band float above the lens plane, max-union of neighboring tents, cell/3 sampling.
- **Manifold discipline**: every mesh passes a hard 2-manifold audit before export (warn-only let defects ship; hard-fail is the law). Pinch-edge fan-split healing for tangency cases.
- **3MF for Bambu**: filament mapping lives in `Metadata/model_settings.config` (`extruder` metadata), not standard 3MF basematerials; parts grouped under a parent object via components.
- **Panelization**: bed envelope is a first-class constraint (H2D both-nozzle zone 316×296 validated); rotate-to-fit before splitting; seam clearance 0.06 mm/face; per-piece labels embossed mirrored on the back.
- **QA against the source art, not the extractor's own graph** (`qa_coverage.py`): rasterize source ink vs. produced tube bands, report uncovered clusters. The extractor validating itself missed amputations; coverage QA would have caught them.
- **The vector is the authority** — never "fix" geometry based on raster mockups.
- Chiral gotcha: any flip-to-use part must be pre-mirrored; default is print-in-use-orientation so it never arises.

## 4. Approaches considered

**A. Generalize the existing OpenSCAD pipeline.** Python generates layout JSON + `.scad`; OpenSCAD renders bodies; Python heals/packages.
*Pros*: proven here. *Cons*: external binary dependency (OpenSCAD + ghostscript), slow CGAL renders (minutes/piece), the whole sliver-war class lives in CGAL unions, string `-D` unreliable, hard to run as a web service, untestable geometry internals.

**B. Pure-Python geometry core** — shapely (2D booleans/offsets) + manifold3d (extrude/boolean; the same Manifold engine modern OpenSCAD embeds, guaranteed-manifold output) + trimesh (mesh IO/repair/inspection) + fontTools (glyph outlines) + svgelements/ezdxf/Pillow (ingest). Web = FastAPI + vanilla JS + vendored three.js.
*Pros*: pip-installable everywhere, no binaries, robust booleans kill the sliver class structurally, fast (ms–s), unit-testable at every stage, one language.
*Cons*: we re-implement band/lens/texture construction (small, well-understood after CHARGE); manifold3d wheel availability pins us to Python ≤3.13.

**C. Hybrid**: Python 2D core with pluggable render backends (manifold3d default, OpenSCAD emitter as escape hatch).
*Pros*: migration path. *Cons*: two backends to test; the escape hatch exists only to serve a dependency we're trying to delete.

**Decision: B.** OpenSCAD gave CHARGE its geometry, but every post-processing tool in this repo exists to fight CGAL output; Manifold makes those failure modes structurally impossible while we keep the audits as gates. (A `.scad` *export* of layout data may return later as a feature, not a backend.)

## 5. Architecture

Library-first. The web app and CLI are thin clients of the same pipeline.

```
led-sign-builder/
  signforge/
    params.py        # pydantic models: the full parameter schema, presets, (de)serialization
    ingest/          # anything -> Artwork (normalized 2D)
      fonts.py       #   text + TTF/OTF/WOFF/WOFF2 -> glyph outlines, kerning, layout
      svg.py         #   SVG: filled shapes -> outlines; stroked paths -> centerline polylines
      dxf.py         #   DXF: LWPOLYLINE/SPLINE/etc -> outlines/polylines
      raster.py      #   PNG/JPG: threshold + marching squares -> outlines
    geom2d.py        # healing (make_valid, orient, simplify), offsets, band(=stroke buffer), area ops
    skeleton.py      # raster scanline fill + Zhang-Suen thinning + graph decompose (port of centerline.py)
    layout.py        # scale-to-height, tracking, multi-line, weld/segment, per-letter tiles vs contour
    leds.py          # pixel placement (resample + relaxation), spacing audits, chains, PSU/BOM math
    textures.py      # heightfield generators: random V3, pyramid, pyramid-jitter V8 (all CHARGE rules)
    solids.py        # manifold-by-construction builders: prisms from polygons, heightfield solids, bands
    parts/
      neon.py        #   black/white/clear bodies for tube signs (port of piece.scad/letter.scad)
      channel.py     #   channel-letter style: back pan, walls (+counter walls), face lens w/ lip
    panelize.py      # bed presets, rotate-to-fit, guillotine cuts + seam clearance, piece masks
    verify.py        # manifold audit (hard gate), clearance audit, coverage QA, bed-fit, min-feature
    export/
      stl.py, threemf.py (Bambu port), bundle.py (zip: STLs, 3MFs, previews, BOM.md, params.json)
    preview/
      html.py        #   self-contained preview page: 2D SVG layout, tables, embedded 3D viewer
      static/        #   vendored three.module.js + viewer.js (no CDN)
    cli.py           # signforge build/preview/serve
    web/
      app.py         #   FastAPI: upload, validate, param UI data, preview, job -> zip
      static/        #   index.html + app.js + vendored three.js
  tests/             # unit + e2e (per format × style), fixtures in tests/assets/
  docs/              # this spec, LESSONS-FROM-CHARGE.md, PIPELINE.md, plans/
```

**Data flow** (each arrow a pure, testable function):

```
Ingest -> Artwork          outlines: list[Polygon(+holes)] and/or strokes: list[(polyline, width)]
Artwork -> Layout          scaled/positioned mm geometry + per-glyph/piece structure
Layout -> TubePlan         (neon) centerlines from strokes directly, or skeletonized from fills
Layout/TubePlan -> LedPlan pixel points + chains + audits + power
* -> PartSet               per piece: named colored Solids (manifold3d) + metadata
PartSet -> Verified        hard gates: manifold, clearances, coverage, bed fit
Verified -> Bundle         stl/3mf/preview html/BOM/params.json -> zip
```

**Sign styles (v1):**
1. **neon-tube** — strokes become 18 mm-class channels (the CHARGE look). Sources: stroked SVG paths (centerline = the path itself), or any filled art/font glyph → rasterize → skeletonize.
2. **channel-letter** — filled outlines become back pan + perimeter/counter walls + face lens with calibrated press-fit lip (-0.2 mm interference default). Back pan is the *filled* outline so counters never float.
Both support backer modes: **tile** (rectangular billboard plate, CHARGE style) or **contour** (offset outline plate).

**Key geometry rules (encoded in `solids.py`/`verify.py`):**
- Build manifold-by-construction where possible (prisms, heightfield solids); use Manifold booleans otherwise; **never** rely on exact-tangency unions — keep CHARGE's fuse overlaps (0.1 mm) and texture dead-bands.
- Every exported mesh passes the ported hard manifold audit (every edge exactly 2 tris, no degenerates). No warn-only paths.
- All dimensions mm; +Z is print-up; parts emit in print orientation (lens-up), pre-mirrored if flip-to-use.

## 6. Parameter schema (customization surface)

Grouped, all with validated defaults from CHARGE; presets: `neon-classic` (CHARGE cross-section), `channel-bold`, `mini-desk`, `halo-backlit` (stretch).

- **Content**: text (multi-line), font file or bundled font, per-line size/align, letter spacing, or uploaded vector/raster art; scale by cap-height/total-width.
- **Style**: neon-tube | channel-letter; backer tile|contour|none; tube width, wall heights, plate/lens thickness, liner walls, corner rounding, halo offset.
- **Texture**: none | random(cell,h) | pyramid | pyramid-jitter(cell,h,seed); per-piece seeds.
- **LEDs**: bullet-12mm (bore, collar, pitch, min-chord) | strip-channel(width) | none; voltage, W/pixel, PSU headroom.
- **Fit/print**: seam clearance, lens fit interference, fuse overlap, min feature, printer preset (bed size incl. H2D both-nozzle 316×296, A1/P1S/X1C/Ender presets) or custom bed.
- **Colors/materials**: per-body filament slots (default black/white/clear), preview colors.
- **Mounting**: screw holes (diameter/count), keyholes (stretch), wire exits.
- **Output**: which artifacts (stl/3mf/preview/bom/zip), embossed piece labels.

Everything serializes to `params.json` (versioned schema) — the bundle is reproducible: `signforge build params.json`.

## 7. Web app

- FastAPI, single process, background thread jobs with progress polling (`/api/jobs/{id}`), file uploads capped (fonts ≤5 MB, art ≤20 MB), no outbound network calls anywhere.
- Flow: upload/pick font → type text → params form (grouped, presets) → **instant 2D preview** (SVG from layout+tube plan, <100 ms path) → on-demand 3D preview (build selected piece → embedded viewer) → Generate → zip download.
- Vendored three.js; custom binary-STL loader (~50 lines); works fully offline.
- Not multi-tenant-hardened in v1 (it's self-host); font parsing happens in-process — document the trust model in README.

## 8. Verification & testing

- **Unit**: healing cases (self-intersections, duplicate points, open contours, zero-area), skeleton on synthetic shapes (ring → 1 closed loop; 'S' bar → 1 open path; junction pruning), spacing solver rules, texture invariants (floor/dead-band respected), 3MF XML structure.
- **Property-style invariants**: every produced solid is manifold; volumes within analytic bounds; band area ≈ length×width within tolerance.
- **E2E matrix**: {font-text, filled SVG, stroked SVG, DXF, PNG} × {neon, channel} → bundle builds, all gates pass, zip contains expected artifacts; golden `params.json` fixtures.
- **Web**: httpx TestClient — upload→job→zip round-trip.
- **Fixtures**: OFL-licensed fonts (downloaded once into `tests/assets/fonts/` with licenses committed), hand-crafted SVG/DXF torture cases, generated PNG logo.
- CI-style entry point: `uv run pytest` — everything green before each commit (user ships fast; tests are the safety net, not ceremony).

## 9. Milestones

- **P0 (walking skeleton, first)**: params + font ingest → layout → neon bands → black/white/clear solids → manifold gate → STL+3MF+zip + minimal HTML preview + CLI. One e2e test green.
- **P1**: channel-letter style, skeletonizer (font→neon), SVG/DXF/PNG ingest, textures, LED planning + audits + PSU/BOM, panelization, full preview page, web app, fixture matrix.
- **P2 (stretch)**: relaxation solver parity, halo/backer extras, keyholes, presets gallery, wiring diagram SVG, EPS via optional ghostscript, `.scad` layout export, hosted-mode hardening.

## 10. Risks

- **manifold3d wheels**: pin Python 3.12/3.13 via uv; fallback = trimesh boolean w/ manifold engine (same lib) or building lens tops as open+capped construction only.
- **Skeleton quality on exotic fonts**: keep CHARGE's debug overlay (PNG) + coverage QA as first-class outputs so failures are visible, tunable (spur/rung/min-path in mm are params).
- **Scope**: 24 h. Mitigation: P0 e2e first, then breadth; HANDOFF.md updated every commit for seamless pickup.

## 11. Non-goals (v1)

Cloud multi-tenancy, auth, payment; G-code generation; non-Latin shaping guarantees (uharfbuzz optional); animation/controller firmware (BOM names controller options only); mobile UI polish.

## 12. Process note (deviation log)

Built under `superpowers:brainstorming` adapted for an explicitly autonomous overnight run: the user pre-approved Design→Plan→Execute→Test without interactive gates ("go until there's nothing else to do", cron check-ins). Clarifying questions were answered from repo evidence (locked-specs, git history, session transcripts); open choices default to CHARGE-validated values and are all overridable parameters. Each cron ping is a redirect opportunity; spec location is inside `led-sign-builder/` per the isolation requirement.
