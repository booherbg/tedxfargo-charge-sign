# HANDOFF — LED Sign Builder

**Updated:** 2026-07-06 ~16:30 · autonomous overnight build (~24 h window, cron check-ins every 20 min)

## Mission
Extract the CHARGE pipeline into a generic, launchable "LED Sign Builder": web UI + CLI + library, upload fonts/vectors, customize everything, get verified print files + previews + zip. Spec: `docs/specs/2026-07-06-led-sign-builder-design.md`. Plan: `docs/plans/2026-07-06-implementation.md`. Evidence base: `docs/LESSONS-FROM-CHARGE.md`.

## State (updated ~17:30 day 1 — ALL PLANNED PHASES COMPLETE)
- [x] Recon → LESSONS doc · spec · plan
- [x] Phase 0-3: scaffold, foundation, channel e2e, 3MF/bundle/preview (**P0**)
- [x] Phase 4: skeleton port (+end extension), neon bodies, LED planner, QA gates
- [x] Phase 5: V8 textures, panelization (seam-aware pixels, labels, screws)
- [x] Phase 6: embedded WebGL 3D viewer, web app, SVG/DXF/PNG ingest,
      9-case format×style matrix, fit-ladder coupons, examples, docs
- **99 tests green.** Landmarks: text `CHARGE` @250 = 6 pieces/161 px/6.5 s;
  **the real `assets/svg/CHARGE.svg` builds: 7 pieces / 403 px / 2.0 kg / 12.8 s.**

## Engineering notes for whoever picks this up
- Coverage QA caught real skeleton amputations during dev (bold-font min_path
  clamp + width-scaled thresholds; strict for glyphs, warn for shape art).
- gated_mesh weld-collapses sub-µm boolean seams (surface-preserving, unlike
  the deleted CHARGE soup-healer) and fan-splits pinch edges; always re-audits.
- Pixels dodge seams, not vice versa (17 mm pitch < 2×12.5 keepout — provable).
- The 3D viewer is custom WebGL because ES-module three.js won't load from file://.
- Web trust boundary: uploads are tokens; client font_path/art_path are stripped.

## Next candidates (P2, none blocking)
Corridor/piecewise seams · halo style · keyholes · relaxation parity · strip LEDs
· wiring diagram SVG · presets gallery UI · hosted hardening · PyPI packaging.

## Resume protocol (any fresh session)
1. `cd /Users/blaine/workspace/2026-charge-tedxfargo/.claude/worktrees/led-sign-builder/led-sign-builder`
2. Read this file, then `git log --oneline -15`, then `uv run pytest`.
3. Open the plan, find the first unchecked task, continue. Update this file + check plan boxes at every commit.

## Decisions of record
- Pure-Python core (shapely + manifold3d), no OpenSCAD/ghostscript — spec §4.
- Channel-letter style first (fewest unknowns), neon-tube immediately after.
- Python 3.12 pinned (manifold3d wheels). Package name `signforge`, product name "LED Sign Builder".
- Worktree discipline: nothing outside `led-sign-builder/` is ever modified.
