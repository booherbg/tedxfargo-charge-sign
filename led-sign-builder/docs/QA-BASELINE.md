# QA Baseline — CHARGE is the gold standard

**Established 2026-07-07.** Every future change iterates from this verified
ground truth. Re-run the whole baseline:

```bash
uv run pytest                      # 174 fast (rc must be 0 — never pipe away exit codes)
uv run pytest -m slow              # 24 slow: torture, example art, fonts, CHARGE parity
uv run python scripts/qa_gold.py   # the gold standard, verified FROM THE EXPORTED FILES
uv run python scripts/qa_upload.py # CHARGE through the real web stack: upload→preview→build→zip
```

## The gold standard (scripts/qa_gold.py)

`assets/svg/CHARGE.svg` @ 250 mm cap, tile margin 22.5, V8 texture, 17 mm
pixels, budget 600, H2D. Pinned results (2026-07-07):

| measure | replica | original production | note |
|---|---|---|---|
| sign width | 1499 mm | 1597 mm face | production face included hand kerns (+1.2/+5.9) & measured margins |
| cap height | 250 | 250 | |
| pieces | 5 | 6 | production used corridor cuts at 295 face height |
| pixels | 415 | 454 | production count is POST hand-repairs (which added px) |
| filament | ~2.1 kg | 1.9–3.1 kg class | |
| shell z | 0→21.0 | plate 2.0 + walls 19 | measured from mesh |
| lens z-top | 22.8 | 21 + 1.2 lens + ≤0.7 V8 texture | measured from mesh |
| treatment | skeleton centerlines | centerline tubes | tube-art auto-detect (thin + elongated) |

Every exported STL: 2-manifold **as written to disk** and fits the bed as-is.
Every 3MF: parseable, Bambu extruder-mapped. Kit: BOM (PSU/chain/Import/WLED),
reproducible params.json, WLED ledmap covering each LED exactly once, preview
PNG/dashboard/debug overlay.

## Bugs this baseline has already caught

1. **float32 write gap** — the manifold gate audited float64 geometry, then
   STL writing quantized to float32, minting fresh zero-area slivers: 4 of 5
   CHARGE lens files failed re-audit from disk. Fix: gate audits
   float32-rounded coordinates (what ships is what was checked).
2. Tube-art outlined (double lines around tube-shaped ink) — auto now detects
   tube-ness (w̄ ≤ 1.4·band AND P²/4πA ≥ 4).
3. Preview pixels drawn at full 12.3 mm bore ("LEDs too big") — now the
   original's 2.6 mm dot + 4.4 mm collar language.

## The upload path (scripts/qa_upload.py) — verified 2026-07-07

CHARGE.svg through the ACTUAL web stack: multipart upload → live preview
(watts = px·0.25, PSU covers at 80%) → queued build → **preview↔build
consistency (pixels/pieces/dimensions identical)** → downloaded zip verified
file-by-file via the shared `scripts/qa_kit.py` (same manifold/bed/3MF/WLED/
BOM checks as gold) → thumbnail + dashboard serve; 3D viewer size-caps
honestly for the 190 MB textured CHARGE (404 + warning). Pitch reconfig
end-to-end: 17→25 mm gives 415→294 px (×0.71), preview == build == WLED map.

## Iterations from ground truth (the rest of the pyramid)

- 174 fast tests: params/geometry/skeleton/LED/panelize/textures/exports/
  previews/web/users/queue/fonts/bed-fit.
- 24 slow: 13-case torture sweep, 10 example artworks, per-font builds,
  CHARGE parity.
- Word×font sweep: 0/112 gate failures (per-glyph auto + retry ladder).
- Wheel: builds, installs into a clean venv, produces a full kit with
  packaged fonts/art only.

## Rules of the baseline

- The gate audits FILES-as-written semantics, never in-memory-only.
- pytest exit codes are checked (`; echo rc=$?`), never piped away.
- Visual changes get a headless-Chrome screenshot audit; geometry changes get
  a PNG-preview eyeball. If it looks wrong, it is wrong.
- CHARGE parity test (slow) pins the replica inside production tolerances.
