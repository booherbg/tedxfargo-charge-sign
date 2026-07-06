# HANDOFF — LED Sign Builder

**Updated:** 2026-07-06 ~16:30 · autonomous overnight build (~24 h window, cron check-ins every 20 min)

## Mission
Extract the CHARGE pipeline into a generic, launchable "LED Sign Builder": web UI + CLI + library, upload fonts/vectors, customize everything, get verified print files + previews + zip. Spec: `docs/specs/2026-07-06-led-sign-builder-design.md`. Plan: `docs/plans/2026-07-06-implementation.md`. Evidence base: `docs/LESSONS-FROM-CHARGE.md`.

## State
- [x] Recon: repo map + archaeology (agents) — done, distilled into LESSONS doc
- [x] Design spec + implementation plan written
- [ ] **Phase 0: scaffold + env + smoke test ← IN PROGRESS**
- [ ] Phase 1: params / geom2d / solids / audit gate / STL
- [ ] Phase 2: fonts → layout → channel bodies → pipeline+CLI (first e2e)
- [ ] Phase 3: 3MF + bundle zip + preview v1 (**P0 complete here**)
- [ ] Phase 4: skeleton + neon bodies + LED planner + clearance/coverage QA
- [ ] Phase 5: textures + panelize + full preview (3D viewer)
- [ ] Phase 6: SVG/DXF/PNG ingest + web app + fixture matrix + coupons + polish

## Resume protocol (any fresh session)
1. `cd /Users/blaine/workspace/2026-charge-tedxfargo/.claude/worktrees/led-sign-builder/led-sign-builder`
2. Read this file, then `git log --oneline -15`, then `uv run pytest`.
3. Open the plan, find the first unchecked task, continue. Update this file + check plan boxes at every commit.

## Decisions of record
- Pure-Python core (shapely + manifold3d), no OpenSCAD/ghostscript — spec §4.
- Channel-letter style first (fewest unknowns), neon-tube immediately after.
- Python 3.12 pinned (manifold3d wheels). Package name `signforge`, product name "LED Sign Builder".
- Worktree discipline: nothing outside `led-sign-builder/` is ever modified.
