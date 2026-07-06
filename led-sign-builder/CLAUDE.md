# CLAUDE.md — LED Sign Builder (signforge)

Rules for any agent/dev working in this subproject.

## Where you are
- Branch `led-sign-builder`, worktree `.claude/worktrees/led-sign-builder/`. **Only touch `led-sign-builder/**`.** The parent CHARGE project is reference-only — read it at the repo root paths, never modify it.
- Continuity: `HANDOFF.md` (state + next step), session task list, `docs/plans/2026-07-06-implementation.md` (checkboxes), `docs/specs/…-design.md` (why).

## Commands
- Tests: `uv run pytest` (auto-creates .venv, Python 3.12, syncs deps)
- CLI: `uv run signforge build --text HI --font tests/assets/fonts/<f>.ttf --style channel -o /tmp/out`
- Web: `uv run signforge serve` → http://127.0.0.1:8763

## Architecture
`ingest/*` → `model.Artwork` → `layout` → `skeleton` (neon) → `leds` → `panelize` → `parts/{neon,channel}` Bodies (manifold3d) → `verify` gates → `export/{stl,threemf,bundle}` → `preview/html`. Orchestrator `pipeline.build(params, outdir)`; CLI and `web/app.py` are thin clients. Parameter schema: `params.py` (pydantic v2, CHARGE-validated defaults).

## Laws (evidence: docs/LESSONS-FROM-CHARGE.md)
1. Every exported mesh passes `verify.audit_mesh` — **hard fail**, never warn-only.
2. ≥0.02 mm standoff between generated fields and boolean partner planes; 0.1 mm fuse welds; no exact tangencies.
3. LED spacing is chord-measured with a 14.5 mm flange floor; budget overruns surface loudly.
4. The vector is the authority; coverage QA closes the art→geometry loop; always emit debug overlays.
5. Print in use orientation; pre-mirror flip-to-use parts.
6. mm everywhere; constants change only with a new printed test (they carry provenance).
7. No outbound network calls in library/web code. Test assets are committed with licenses.

## Porting sources (read, don't copy blindly)
- 3MF + manifold audit: `tools/make_3mf.py` · skeleton: `tools/centerline.py` · textures: `tools/make_fuzz.py`
- Bodies: `src/parts/piece.scad`, `src/letter.scad`, `src/config.scad` · panelizer: `tools/panelize.py`
- Audits: `tools/clearance_audit.py`, `tools/qa_coverage.py` · previews: `tools/gen_cutpreview.py`
