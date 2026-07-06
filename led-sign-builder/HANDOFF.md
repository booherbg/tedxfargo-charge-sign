# HANDOFF — LED Sign Builder

**Updated:** 2026-07-06 ~16:30 · autonomous overnight build (~24 h window, cron check-ins every 20 min)

## Mission
Extract the CHARGE pipeline into a generic, launchable "LED Sign Builder": web UI + CLI + library, upload fonts/vectors, customize everything, get verified print files + previews + zip. Spec: `docs/specs/2026-07-06-led-sign-builder-design.md`. Plan: `docs/plans/2026-07-06-implementation.md`. Evidence base: `docs/LESSONS-FROM-CHARGE.md`.

## State (updated ~17:20, day 1)
- [x] Recon: repo map + archaeology (agents) — distilled into LESSONS doc
- [x] Design spec + implementation plan written
- [x] Phase 0: scaffold + env + smoke test
- [x] Phase 1: params / geom2d / solids / audit gate / STL
- [x] Phase 2: fonts → layout → channel bodies → pipeline+CLI (first e2e)
- [x] Phase 3: 3MF + bundle zip + preview v1 (**P0 complete**)
- [x] Phase 4: skeleton port (+end extension) + neon bodies + LED planner + QA gates
- [x] Phase 5: V8 textures + panelization (seam-aware pixels, labels, screws)
- [ ] **Phase 6 ← IN PROGRESS**: preview v2 (3D viewer) → web app → SVG/DXF/PNG
      ingest → fixture matrix → coupons → polish
- 72 tests green. Landmark: `CHARGE` @250 cap = 6 pieces / 161 px / 1.4 kg in 6.5 s.
- Notable engineering: coverage QA gate caught real skeleton amputations on bold
  fonts during dev (min_path clamp + width-scaled thresholds); sub-µm boolean
  seams handled by weld-collapse in gated_mesh; pixels dodge seams (not vice versa).

## Resume protocol (any fresh session)
1. `cd /Users/blaine/workspace/2026-charge-tedxfargo/.claude/worktrees/led-sign-builder/led-sign-builder`
2. Read this file, then `git log --oneline -15`, then `uv run pytest`.
3. Open the plan, find the first unchecked task, continue. Update this file + check plan boxes at every commit.

## Decisions of record
- Pure-Python core (shapely + manifold3d), no OpenSCAD/ghostscript — spec §4.
- Channel-letter style first (fewest unknowns), neon-tube immediately after.
- Python 3.12 pinned (manifold3d wheels). Package name `signforge`, product name "LED Sign Builder".
- Worktree discipline: nothing outside `led-sign-builder/` is ever modified.
