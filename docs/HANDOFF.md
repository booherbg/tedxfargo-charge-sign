# TEDxFargo CHARGE — Sign Build Handoff (refreshed 2026-07-04)

**What this is:** a 3D-printed, LED-lit replica of the TEDxFargo CHARGE 2026 neon-billboard logo
(`assets/tedxfargo-full-logo.png`). White-reflector channels + frosted clear lenses, lit from
behind by 12 mm bullet pixels. Read top-to-bottom for full context; numeric truth lives in
`docs/locked-specs.md`; print/assembly steps in `docs/assembly-charge.md`.

## 0. State at a glance
- **CHARGE word: DONE and sliceable.** Six 3-color pieces (`stl/piece1..6_3color.3mf`), all
  bed-validated, mesh-audit clean, 2,189 g total, **454 pixels**. User has successfully sliced;
  first prints pending white PETG delivery. Do not regenerate unless design changes.
- **Bolt board: IN FLIGHT, geometry NOT final.** Decisions locked: separate 2-plate board
  (300×590), C1 look (yellow outline + red inner bolt), 20 mm pixel pitch, straight seam with
  13 mm neon-break pullbacks. **BLOCKER: we composed from the WRONG vector** — see §10.
- **PETG fuzz bake-off** (testboxes v3–v6, picks the lens texture): ready to print on the
  ~100 g white remnant; a texture change is a one-line .dat swap + clear-body re-render.
- Wood frame, wiring, mounting: user-built later; interface specs in the assembly card.

## 1. Locked build facts (never re-derive)
- Cap 250 mm uniform; face 1597×295; 6 pieces, corridor cuts through black only; auto-kern
  applied (A|R +1.2, R|G +5.9 — R/G bands would physically overlap at true kerning).
- Cross-section: black 2 mm plate + 1.2 black outer wall / 0.4 white liner + 0.8 white inner
  wall / 19 mm channel (18 interior) / 1.2 clear lens + baked V3 fuzz (dead-banded ±50 µm
  around the lens plane — see §9). ALL-PETG, 3 colors.
- Pixels: Ø12 bullets, flange Ø13.6 (**14.5 mm min spacing; 13.0–14.5 = snug/flange-snip**),
  collar `assets/bullet-collar.stl`, letters @17 mm pitch, bolt @20 mm. 4-inch strings.
- Bed truth (H2D, validated with `stl/bedcheck_316x295.stl`): both-nozzle zone fits 316×295;
  place 295 across, long side deep. Multi-color parts must sit between the nozzle bands.
- Slicing: 0.20 Standard + card overrides; clear shares the WHITE nozzle (only swap ≈ z21);
  prime tower in the right-nozzle column or OFF + flush-into-objects; skirt/brim OFF; the
  fuzzy-top shell islands are killed by the layer stack at 0.20 (historic +1-bottom fix).
- Power: 585 px ≈ full-white edge of the 150 W PSU → cap ~80% or add PSU.

## 2. Pipeline (all committed, reproducible)
`tools/centerline.py` EPS/PGM → tube centerlines (graph decomposition; pairs crossings by
straightest continuation; `--target-h` for raster assets) → `tools/panelize.py` (clearance
field, auto-kern, corridor cuts, chord-aware pixel relaxation, `--labels/--pitch`) →
`tools/gen_pieces.py` (per-piece data + dead-banded fuzz + build scripts) →
`src/parts/piece.scad` (numeric `-D PIECE/COL`; string -D unreliable) → `build_pieces.sh` →
`tools/make_3mf.py` (N STLs → Bambu 3MF, **built-in manifold audit**). `tools/stl_stats.py`
for volume/grams. Letter pixel layout truth: `src/parts/word_cuts.json`.

## 10. BOLT BOARD — current sprint, exact pickup point
**Locked decisions:** separate board left of CHARGE, 300×590, 2 plates (B1 bottom/B2 top),
straight seam at y=295 through engineered 13 mm pullback breaks (provably legal — no router
needed); C1 composition = yellow outline bolt + red inner bolt (colors via pixel zones, same
3-filament print); 20 mm pitch → ~131 px → **sign total ~585 of 600 ✓**.

**THE BLOCKER — wrong source vector:** everything so far used **element 5** (pointed-top slim
bolt) from `assets/TEDxFargo CHARGE Graphics and Assets/RedNeon/`. The user correctly flagged
the logo's bolt has a **flat top**. `docs/img/bolt-element-compare.png` (logo crop vs elements
4/6/13) shows **element 6 IS the logo's left panel**: the flat-top bolt and the X are ONE fused
yellow outline, with a slim red bolt laid inside. The deployed-aspect measurement (~0.45 w/h vs
element-5's 0.239) was really telling us "wrong element."

**Open design question for the user first:** element 6 fuses bolt+X. Board options:
(a) whole element-6 composition (bolt+X, yellow) + red inner — the literal logo panel (may want
a wider/taller board or cropping); (b) isolate just the bolt portion of element 6.

**Then the build steps:**
1. Extract from `RedNeon/TEDx_RedNeon_6.psd` (and/or the YellowNeon twin — same geometry):
   `magick ... -channel R -separate -resize 200% -threshold 65% -negate → .pgm`, then
   `tools/centerline.py <pgm> --target-h <H> --name BOLTX --out ...` (65% threshold proven;
   50% bridges glow). The red inner bolt: slim element inside the logo — likely element 5 at
   small scale as INNER (single tube), or trace element 6's inner if present.
2. Clearance audit inner↔outer ≥26 mm (band edge-to-edge +4) or accept only crisp
   point-crossings (merged amber pockets like the A letter — long parallel overlaps looked
   like mush and were rejected by the user).
3. `tools/boltboard.py --pitch 20` (machinery is GOOD: relaxation pixels, 3-rail screws
   ×12, ties, dead-banded fuzz, `bolt_pixmap.json` color zones) — it reads
   `src/parts/bolt_final2.json` key `c1` {yellow:[...], red:[...]} paths pre-split at the
   seam; regenerate that JSON from the new extraction (seam-split helper in git history:
   `bolt_compose.py` / composer snippets in commits).
4. `src/parts/bolt_piece.scad` -D PIECE=1|2 COL=1|2|3 → 6 bodies → `make_3mf` (audit inline).
5. Update `docs/sign-preview/full-sign.html` (composition + board detail page) + assembly card.

**OBSOLETE — do not use/slice:** current `stl/board*_c*.stl` + `board1/2_3color.3mf` (tangled
element-5 geometry), `bolt_final2.json` c1/c2 paths, `bolt_c1_clean.json` (optimizer run had a
scoring bug and a hacked spine width; best clearance found was only 4.4 mm). The el-5
extractions (`bolt5_data/bolt5s_data.scad`) are geometrically fine, just the wrong bolt.

## 9. Non-obvious gotchas (hard-won)
- Skeleton tips have no degree-1 endpoints (ZS clumps) → open/closed by walk behavior.
- Letters are OPEN neon tube runs; art paints breaks as notches; slivers can bridge shapes.
- Fuzz heightfields near the lens plane make CGAL micro-slivers → 0.02 floor + off-lattice
  base (0.1504) + ±50 µm dead-band; `make_3mf.py` audits every mesh now.
- Bambu: "filament change times" on H2D = free per-layer nozzle swaps, not purges. Prepare-
  stage tower warnings that vanish after slicing are safe. 3MF-imported filaments are unbound
  until synced; verify mapping in the send dialog. AMS backup = identical preset+color in two
  slots on the SAME side. Left nozzle has no AMS (external spool; weigh before big blacks).
- Nesting two 22 mm channels needs ≥26 mm centerline gap — most "outline + inner" art only
  supports this at large scale or with crossings.
- Chiral flip-mirror rule is moot for everything current (all parts print in use orientation).
