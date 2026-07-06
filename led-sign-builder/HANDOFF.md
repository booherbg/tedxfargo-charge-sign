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

## P2 progress (evening day 1, 107 tests green)
- [x] #18 seam-segment pixel placement (replaces slide-nudging; keepout by
      construction) + wiring diagram (chain/jumpers/DATA IN on dashboard, BOM section)
- [x] #20 halo/backlit style (face-down pre-mirrored, rear flange pixel racetrack,
      standoffs, optional diffuser; unpanelized v1) + LED-strip mode (BOM power plan).
      Keyholes deferred: standoff bosses are the natural halo mount.
- [x] #19 corridor/piecewise seams: corridors.py (chamfer clearance field +
      widest-then-shortest Dijkstra), polygon regions split by seam LineStrings,
      full-span corridor fallback when straight cuts cross tubes, polyline seam
      keepout in the LED planner.
- [x] #21 launch prep: MIT LICENSE, wheel+sdist build verified, demo gallery
      (scripts/make_gallery.py → docs/gallery/, 5 real builds), README linked.
- [x] BONUS: **terminal rescue** — uncovered coverage clusters re-skeletonized
      (gentle pruning, blob-midline fallback) and added as tubes; unblocks
      script fonts (Pacifico) and improves shape tips. The automated make_repairs.

## Hardening round (loop iteration 2 — 115 tests green, 19 commits)
17-case torture sweep (script in session scratchpad `torture.py`): **0 crashes**,
every case builds or gates with a clear message. Drove 4 real fixes: progress-first
cut scoring (M@500 16→4 pieces), corridor bounds-progress guard (kills the
27-piece spiral), narrow-halo racetrack→skeleton collapse, audit aggregation.

**Loop iteration 3:** heightfield mesh vectorized (the one profiled hot spot we
control; CHARGE stays ~12s — boolean-bound, fine for a 1.6m kit), web preset
buttons, torture sweep promoted to `tests/test_torture.py` behind `-m slow`
(fast suite 115 / slow 13, all green).

**Loop discipline for future pings:** if nothing is queued — run
`uv run pytest`, confirm green, give a one-line status, and STOP. Do not
invent churn. Remaining candidates:
- hosted hardening basics (simple rate limit, upload-count and job-count caps)
- param-schema-driven advanced UI (generate controls from pydantic schema)
- USER-gated: product name, PyPI publish, physical H2D print of a kit
  (fit ladder first: `uv run signforge coupon -o out/coupons`).

## Resume protocol (any fresh session)
1. `cd /Users/blaine/workspace/2026-charge-tedxfargo/.claude/worktrees/led-sign-builder/led-sign-builder`
2. Read this file, then `git log --oneline -15`, then `uv run pytest`.
3. Open the plan, find the first unchecked task, continue. Update this file + check plan boxes at every commit.

## Decisions of record
- Pure-Python core (shapely + manifold3d), no OpenSCAD/ghostscript — spec §4.
- Channel-letter style first (fewest unknowns), neon-tube immediately after.
- Python 3.12 pinned (manifold3d wheels). Package name `signforge`, product name "LED Sign Builder".
- Worktree discipline: nothing outside `led-sign-builder/` is ever modified.
