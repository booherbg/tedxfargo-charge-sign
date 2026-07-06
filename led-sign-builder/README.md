# LED Sign Builder (`signforge`)

Turn **text + any font** — or an **SVG / DXF / PNG logo** — into a complete, verified,
print-ready **LED sign kit**: multi-material 3D print files, LED layout and power plan,
previews, and a zip you can hand to anyone.

Born as the generic extraction of the TEDxFargo **CHARGE** sign pipeline (13 days,
65 commits, physically validated on a Bambu H2D). Every default in here was set by a
printed test, and every automated gate exists because a defect once shipped past a
preview — see `docs/LESSONS-FROM-CHARGE.md`.

**Pure local software.** No cloud, no external APIs, no OpenSCAD/ghostscript — a
pip-installable Python package with a web UI.

## What you get in a kit

- **STL per color body per piece** (opaque shell / white reflector liner / clear lens)
- **Bambu-ready multi-filament 3MF** per plate (correct proprietary extruder mapping;
  load with File→Import)
- **LED plan**: 12 mm bullet-pixel placement with chord-measured spacing, seam keepout,
  snug-pair audits, wiring-gap jumper flags, PSU sizing, strings-of-50, budget tracking
- **Panelization** to your printer's bed: scored cuts (tube crossings, crisp angles,
  pixel keepout), seam clearance, debossed mirrored piece labels, mounting screws that
  dodge lit channels
- **Baked lens textures** — the V8 jittered-facet field that won CHARGE's PETG bake-off
  (slicer fuzzy skin can't texture top faces; geometry can)
- **Previews**: a production dashboard (mm-accurate SVG, weights, power, audits) and an
  **embedded 3D viewer** (zero-dependency WebGL, works from `file://`) + skeleton debug
  overlays ("always eyeball it")
- **BOM.md** print card with slicer notes, and **params.json** — every kit rebuilds
  exactly with `signforge build --params params.json`

## Quickstart

```bash
# web UI
uv run signforge serve            # → http://127.0.0.1:8763

# CLI
uv run signforge build --text "OPEN" --style neon --cap-height 200 -o out/open
uv run signforge build --art logo.svg --style channel --cap-height 250 -o out/logo
uv run signforge build --params examples/neon-classic.json -o out/example

# print a fit ladder BEFORE trusting a press fit on your printer/filament
uv run signforge coupon -o out/coupons
```

## Input formats

| Source | Fills (channel/neon) | Strokes (neon tubes) |
|---|---|---|
| TTF / OTF / WOFF / WOFF2 + text | ✓ nonzero winding, kern pairs, multi-line | via per-glyph skeleton |
| SVG | ✓ per-element fill-rule | ✓ stroked paths become tubes directly |
| DXF | ✓ closed entities (nested = holes) | ✓ open polylines/splines |
| PNG / JPG | ✓ threshold + marching-squares trace | via skeleton |
| EPS | convert to SVG first (`gs`/`pdftocairo`) | — |

## Three styles

- **neon** — faux-neon tube channels (the CHARGE look): 18 mm interior / 22 mm band
  cross-section, white-lined, welded textured lens, pixels along the tube.
- **channel** — classic filled channel letters: back pan (counters never float),
  perimeter+counter walls, press-fit face lens (**-0.2 mm interference**, pre-mirrored
  for face-down printing).
- **halo** — backlit wall-glow letters: opaque face (bed-smooth, pre-mirrored),
  white rear flange with backward-firing pixels on a perimeter racetrack, standoff
  bosses, optional drop-in rear diffuser. LEDs: bullet pixels, **LED strip**
  (length+PSU planned in the BOM), or none.

Backers: `tile` (billboard), `contour`, `none`. Printers: H2D (multi-nozzle zone),
X1C, A1, A1-mini, MK4, Ender-3, or custom bed.

## The gates (non-negotiable)

1. **Manifold audit** on every exported mesh — position-welded, 2-manifold, hard fail
   (pinch edges get the CHARGE fan-split heal; sub-µm boolean seams weld-collapse).
2. **Coverage QA** — the tube layout is diffed against the source ink; missing
   letterform parts fail the build (strict for text, warning for shape art).
3. **Clearance audit** — parallel channels closer than band+4 mm are rejected "mush";
   crisp crossings pass. Kissing glyphs auto-kern apart.

## Trust model

Fonts/art are parsed in-process; the web UI is for you and people you trust (uploads
are token-scoped, client paths ignored, no outbound calls — but it is not hardened
multi-tenant hosting).

## Layout

`signforge/` — pipeline (`params → ingest → layout → tubes/leds → panelize → parts →
verify → export → preview`), `web/` FastAPI + static UI, `cli.py`.
`tests/` — 99 tests incl. a 9-case format×style build matrix; fixture fonts are OFL
(licenses committed). `docs/` — design spec, implementation plan, CHARGE lessons.

## Roadmap (P2)

Corridor/piecewise seams · halo/backlit style · keyhole mounts · pixel relaxation
parity · strip-LED channels · presets gallery · wiring diagram SVG · hosted-mode
hardening · `.scad` layout export.
