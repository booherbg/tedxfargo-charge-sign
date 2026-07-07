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

**Loop iteration 4:** web guardrails (per-IP rate limits, upload/job caps with
eviction + job-dir cleanup, font parse-check + raster sniff at upload).

## AUTONOMOUS QUEUE EXHAUSTED — 118 fast + 13 slow tests green, 24 commits
Deliberately NOT done: param-schema-generated UI (JSON textarea + preset
buttons cover it; churn without user feedback). Everything else that remains
is USER-gated:
1. Product name (working title "LED Sign Builder", package `signforge`)
2. PyPI publish (wheel builds clean; `uv build` verified)
3. Physical validation on the H2D — print the fit ladder first
   (`uv run signforge coupon -o out/coupons`), then a mini-desk kit
4. Bambu Studio eyeball of any kit 3MF (File→Import; writer is byte-ported
   from the CHARGE-verified make_3mf.py)

**Future pings: run `uv run pytest`, confirm green, one-line status, STOP.**

## PHASE 2 (user-directed, evening day 1) — COMPLETE
Spec: docs/specs/2026-07-06-phase2-platform-design.md · seed 582035 UI notes:
docs/DESIGN-NOTES.md
- Catalog: plaque shapes (rounded/oval/shield/starburst/scallop), texture
  targets (lens + backer field), 5 filament palettes, printer bridging
  profiles, internal support ribs (inter-pixel midpoints = led_void/2).
- Platform: sqlite accounts (scrypt, sessions), free/premium tiers enforced
  (150mm / 6-a-day / 1-queued vs uncapped+priority), admin API, priority job
  queue (positions, cancel, thumbnails), --open flag for solo self-host.
- Console SF-1 UI: bakelite-and-brass (seeded off-default), full UX audit
  fixed, auth/account/admin/queue surfaces, custom bed + palette + plaque +
  rib + texture-target controls.
- PNG lit-preview renderer in every kit → the visual QA loop that drove:
  outline neon mode (auto for shape art) + per-component spine fallback,
  mixed fill+stroke support, SVG transform baking (abs), bold-K glyph-relative
  pruning + capped coverage thresholds, corridor fit-or-halve rule.
- 10 example artworks (examples/art) + gallery/examples contact set.
- 141 fast + 23 slow tests green, 33 commits.

Remaining USER-gated items unchanged (name, PyPI, physical print, Bambu eyeball)
+ new: try the accounts flow (`uv run signforge serve`, admin password prints
once on first run; `--open` to skip accounts).

## Post-phase-2 loop iterations
- Design library: bundled motifs selectable in the console (packaged art,
  /api/library, thumbnail grid). README caught up to phase 2.
- Halo mounting plaque: backer tile/contour now emits a real plaque body
  (standoff-matched anchor bores, corner wall screws, own plate, BOM assembly
  notes) — the UI promise the engine didn't keep. Halo PNG render fixed
  (crisp face post-blend, counters restored; visual-verified).
- Per-letter halo pieces (glyph → piece, print-space clip masks, one shared
  plaque; first-piece plate emission decoupled from names) + job history
  across restarts (sqlite → 'expired' cards in the queue UI).
- 145 fast + 23 slow green, 43 commits. **Autonomous candidate list is empty
  — future pings: verify green, one-line status, stop.** USER-gated: name,
  PyPI, H2D fit-ladder print, Bambu 3MF eyeball, console walkthrough.

## Resume protocol (any fresh session)
1. `cd /Users/blaine/workspace/2026-charge-tedxfargo/.claude/worktrees/led-sign-builder/led-sign-builder`
2. Read this file, then `git log --oneline -15`, then `uv run pytest`.
3. Open the plan, find the first unchecked task, continue. Update this file + check plan boxes at every commit.

## Decisions of record
- Pure-Python core (shapely + manifold3d), no OpenSCAD/ghostscript — spec §4.
- Channel-letter style first (fewest unknowns), neon-tube immediately after.
- Python 3.12 pinned (manifold3d wheels). Package name `signforge`, product name "LED Sign Builder".
- Worktree discipline: nothing outside `led-sign-builder/` is ever modified.

## Font library + GitHub (2026-07-07)
- 15 bundled OFL typefaces (registry in ingest/fonts.py, /api/fonts, console
  typeface grid w/ live FontFace previews, CLI --font names). Clearance floods
  aggregate into one actionable size-hint line (the Monoton lesson).
- Branch pushed to origin (PUBLIC repo) — push after every commit batch now.

## Neon-aesthetic round (user-directed, 2026-07-07)
- WLED ledmap.json ships in every pixel kit (2D grid map, chain order, BOM
  upload instructions). LED pitch was already fully adjustable (UI/CLI/params).
- Outline mode now applies to TEXT (open-tube channel letters); AUTO picks
  outline vs skeleton by measured stroke width (2.2×band, visually calibrated).
  Chunky-tube advisory when band >15% of letter height. Counters/open shapes
  are carried by the shared backer plate (nothing floats) + optional ribs.

## 2026-07-07 day session (user-driven) — QA BASELINE ESTABLISHED
Full record for post-compaction pickup:
- Queue delete/✕/CLEAR FINISHED (files removed too); job history expiry cards.
- Control-impact audit → 3D badges, tube-source select added (was JSON-only).
- Word×font sweep 0/112: per-glyph auto mode + retry ladder (2× raster →
  outline switch) + friendly coverage-gate message.
- Bed-fit guarantee: flat plates (channel lens 1047mm!, halo plaque) now
  rotate/grid-split; rotated pieces export physically rotated. tests/test_bed_fit.
- v1 simplification: fonts curated at defaults (monoton + great-vibes hidden,
  ?all=1 restores), conditional control relevance, strip×channel gated,
  pitch floor 13, budget-px + uniform-pyramid JSON-only.
- CHARGE ground truth: tube-art auto-detect (thin+elongated → skeleton),
  original dot+collar pixel rendering, examples/charge-replica.json,
  slow parity test, scripts/qa_gold.py (verifies FROM EXPORTED FILES).
- **Gold QA caught + fixed: float32 write gap** (gate now audits f32-rounded
  coords). docs/QA-BASELINE.md = the canonical baseline + rules.
- State: 174 fast + 24 slow + gold_rc=0 + wheel smoke OK. Console serving
  on :8763 (open mode, background task).
