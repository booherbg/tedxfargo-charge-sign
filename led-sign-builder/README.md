# LED Sign Builder (signforge)

Turn **text + a font** — or an **SVG / DXF / PNG logo** — into a complete, print-ready **LED sign kit**:

- Multi-material 3D-printable parts (STL + Bambu-ready multi-filament 3MF)
- Two styles: **neon-tube** (faux-neon channels with diffuser lens, the CHARGE look) and **channel-letter**
- Automatic LED pixel layout (spacing solver, wiring order, PSU sizing, budget tracking)
- Panelization to your printer's bed with seam clearances and piece labels
- Baked lens textures (the PETG bake-off-winning jittered facet field)
- Hard verification gates: manifold audit, clearance audit, art-coverage QA
- Self-contained offline HTML preview (2D layout + 3D viewer) and a zip bundle, reproducible from `params.json`

**Pure local software.** No cloud, no external APIs, no OpenSCAD/ghostscript binaries — pip-installable Python.

> Status: pre-alpha, built as an overnight extraction of the proven TEDxFargo CHARGE pipeline.
> The physics inside (fits, clearances, optics) comes from printed tests — see `docs/LESSONS-FROM-CHARGE.md`.

## Quickstart

```bash
uv run signforge build --text "OPEN" --font tests/assets/fonts/Bungee-Regular.ttf \
    --style neon -o out/open-sign
uv run signforge serve   # web UI at http://127.0.0.1:8763
```

The zip in `out/open-sign/` contains STLs per color body, per-piece 3MFs, `preview/index.html`, `BOM.md`, and `params.json`.

## Trust model
Font/art files are parsed in-process (fontTools/svgelements/Pillow); run the web UI for yourself or people you trust, not as a hardened public service (v1).

## Layout
`signforge/` library (pipeline stages) · `signforge/web/` FastAPI + static UI · `tests/` incl. fixture fonts (OFL, licenses committed) · `docs/` spec, plan, lessons.
