# Phase 2 — Platform & Catalog Design

**Status:** approved-for-build (autonomous continuation of the user's directive) · builds on `2026-07-06-led-sign-builder-design.md`

## Goals (user's words, decomposed)

1. Wide variety of selectable designs → **plaque/backer shape catalog + texture targets + palettes**, all in the web UI.
2. Queuing + smart async → **priority job queue** (positions, cancellation, persistence) replacing fire-and-forget threads.
3. User system, free vs premium, admin management → **accounts (sqlite, stdlib crypto), tiers with enforcement, admin panel**; `--open` flag preserves zero-friction solo self-hosting.
4. Fuzzy layer on many geometries → **texture_targets**: lens (existing) + backer field (the visible dark plate around tubes).
5. Internal supports for weak-bridging printers → **integrated support ribs** in neon channels (thin white ribs floor→lens, permanent by design — removable supports inside sealed cavities are the #1 CHARGE "abandoned" lesson); printer presets gain a bridging profile that drives an `auto` mode.
6. Bed size + colors → custom bed fields and filament color pickers in the UI (engine already parametric).
7. 1950s industrial UX, seeded off-default → see §UX.
8. Example vector sweep, visually verified → PNG preview renderer (also a product feature: kit thumbnails) + build-and-look loop.

## Architecture additions

- `signforge/plaques.py` — backer shape functions: `rect|rounded|oval|shield|starburst|scallop`, param'd (corner radius, ray count), fed from `StyleParams.backer_shape`. Applies wherever `backer="tile"` built a rect.
- `params.py` — `TextureParams.targets: ["lens"]|["lens","backer"]|["backer"]`; `StyleParams.backer_shape`, `support_ribs: auto|on|off`, `rib_spacing_mm=28`, `rib_t=0.9`; `PRINTER_PRESETS` values become `{bed, bridging}`; `ColorParams.palette` presets ("porcelain-diner", "gas-station", "atomic-lounge", plus "charge-classic" default).
- `signforge/preview/png.py` — PIL renderer: fills/bands/pixels/seams/plaque on dark ground → `preview/preview.png` in every kit (web thumbnail + my visual QA).
- `signforge/web/users.py` — sqlite (`~/.signforge/web.db` or `SIGNFORGE_DATA`), scrypt password hashes, session tokens table, roles `admin|user`, tiers `free|premium`. First run creates admin (password printed once to console or `SIGNFORGE_ADMIN_PASSWORD`). Registration open by default (self-host).
- `signforge/web/queue.py` — heap-based priority queue: premium > free, FIFO within class; jobs persisted (params json, state, log tail, timestamps); positions surfaced; cooperative cancel (flag checked in the progress callback between pipeline stages); 2 workers.
- Tier enforcement (accounts mode): free → cap ≤ 150 mm, 6 builds/day, 1 queued at a time, standard priority; premium/admin → uncapped, priority. Open mode → everything free-of-charge locally.

## UX (seeded, deliberately off-default)

Seed drawn with `secrets.randbelow` at design time; it picks among curated non-default directions (palettes/type/ornament). **The seed and the picks get recorded in `docs/DESIGN-NOTES.md`.** Direction: "machine-shop control panel, 1957" — enamel cream panels, deep-pigment accent, riveted corners, toggle-feel controls, stencil display type (bundled Bungee via @font-face — already OFL), letterspaced uppercase micro-labels, spec-plate footers. Clean first: ornament stays in borders/labels, never in reading surfaces. Audit fixes ride along: loading/error/empty states, labeled inputs, queue visibility, mobile stacking, favicon/title.

## Non-goals

Payments (tier is a flag admins flip), email verification, OAuth, multi-node queue workers, GPU rendering.
