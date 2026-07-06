# Lessons from CHARGE

The TEDxFargo CHARGE sign (this repo's parent project) was built over 13 days, 65 commits, and many physical prints. **Every constant below was set by a printed test, and every automated check exists because a defect once shipped past a preview.** This document is the distilled evidence base for signforge's defaults and gates. Sources: git history, `docs/locked-specs.md`, `docs/HANDOFF.md`, design specs, and session transcripts.

## A. How the pipeline evolved (7 phases)

1. **Stackup coupons** — depth-ladder proved the air gap dominates diffusion: 35/50 mm "too dim/washed", **~15 mm wins** (ladder re-shifted to 10/15/20). Four diffuser attachments tried in 24 h; flanged plug won, later obsoleted.
2. **Bolt test piece + fit war** — every positive lens clearance fell out; a **labeled fit ladder of small slices** (user's idea — never dial fits on full parts) found **-0.2 mm interference** = perfect snap. The **chiral flip disaster**: a print-face-down flip-to-use cap "won't register in ANY rotation" — flip = mirror.
3. **Optics matrix** — 8-cell dual-material experiment + Monte-Carlo sim. Physics prediction lost: **bare cavity (A0) won**; masks spaghetti'd (support-needing geometry in sealed cavities is unprintable); **white interior recycles light** (same brightness, ~5 fewer LEDs); clear PETG > clear PLA.
4. **Integrated lens + baked fuzz V1→V9** — slicer fuzzy skin can't texture top faces → texture must be **baked geometry** (pure heightfield → no supports). V3 random (1.5/0.8) won on PLA; PETG re-opened the contest; **V8 jittered pyramid facets (2.0 mm cell / 0.6 mm peak) final winner**. Slicer haze levers (flow/temp/fan/layer height) tested and refuted: "didn't really do anything noticeable."
5. **Letters pipeline** — EPS → raster → Zhang-Suen skeleton → ordered tube centerlines → pixels at pitch. Cap height negotiated against the bed (270 single-letter ceiling; 250 final because widened H = 331 mm).
6. **Whole-word billboard panelization** — one continuous face, corridor cuts through dark field only (seams never cross a lit tube), auto-kern where widened bands collide, relaxation pixel solver after the user spotted a greedy-stack end gap in a slicer screenshot. First **sliver war** (heightfield ∪ plane tangencies).
7. **Bolt board + production hardening** — wrong brand element built once (verify against the deployed composition!); approved-design bridging incident → full revert; zip-tie holes removed (lit pinpricks); the **A-glyph amputation** discovered after 3 days → `qa_coverage.py` born: *the extractor validated its own graph, not the art.*

## B. The laws (problem → rule signforge encodes)

**Fit & tolerance**
1. Positive clearances fall out; snap fits start at ~0.1–0.2 mm **interference**. Ship a **fit-ladder coupon generator** (labeled slices of the real joint) as a feature.
2. Flip-to-use = mirror. Pre-mirror chiral parts; prefer use-orientation printing (then it never arises). Symmetric test chunks don't prove chiral fits.
3. Model the LED as an **insertion envelope** (barrel+dome+travel: led_void 14.0, led_clear 2.5), not a point; run collision audits on emitted parts.

**Optics**
4. Baseline recipe: **white shell + ~15 mm air gap + 1.2 mm clear lens**; internal optics are opt-in experiments; never require supports inside sealed cavities.
5. Always line channel floor + inner walls **white** ("never a dark interior") — it buys pitch/budget headroom.
6. Diffusion is **geometry, not print settings**. Baked heightfield textures only (no overhangs).
7. Texture winner is **material-dependent** — keep textures swappable one-liners.
8. **No through-holes in a lit face** (zip-tie holes = lit pinpricks). Audit for accidental apertures.

**Mesh robustness (the sliver war)**
9. Never let generated geometry kiss a boolean partner's plane: **≥0.02 mm standoff**, avoid C0 cliffs (max-union neighboring tents), off-lattice offsets. The ±50 µm dead-band fix *created* a coplanar sliver plane for pyramids and was replaced by floating the field proud.
10. **Hard-fail manifold audit at build time** — warn-only let V8 pinches ship. A slicer warning is a build failure. Naive degenerate-dropping healers punch holes (deleted); repair must be topology-aware (weld only through clean 2-side edges).
11. When a defect class is consciously accepted, **write down the class, evidence, and affected parts** — or every re-encounter costs a re-investigation.

**Extraction / art fidelity**
12. Close the loop **source-art → final geometry** with an automated ink-coverage diff (>100 mm² uncovered = FAIL) + rendered visual checks. Intermediate representations always lie eventually.
13. **The vector is the authority**; raster mockups can confirm but never introduce geometry (the phantom "mid dash" was a PSD glow highlight).
14. Skeleton gotchas: Zhang-Suen leaves 2×2 tip clumps (no degree-1 endpoints — detect open/closed by walk behavior); ink may be light (threshold high, not 128); always emit a **debug overlay** and eyeball it.
15. Multi-element brand files: overlay-verify the chosen element against the deployed composition before building (element-5 vs element-6 cost a full panelization).

**Layout physics**
16. Stroke widening changes the art's collision rules: **auto-kern** kissing letters (+1.2, +5.9 mm on CHARGE); two 22 mm bands need **≥26 mm centerline gap**; crisp crossings exempt; long parallel sub-clearance "mush" is a hard reject.
17. Seam placement is a **constraint solver**: dark-field-only, ≥5 mm from walls, graze/corner/tangent-apex rejection, pixels ≥12.5 mm off seams; expect piecewise seams on real art.
18. Pixel placement: **pinned-end relaxation, chord-measured** (raster skeletons inflate arc length), flange floor 14.5 mm, report snug pairs + worst gap.
19. **Hardware inventory is a hard budget** (600 purchased was the law, not a suggestion). Show running totals on every preview; overruns block on sign-off.

**Printer/slicer integration**
20. Bambu ignores standard 3MF materials: part→filament = `Metadata/model_settings.config` extruder metadata, parts grouped under a parent components object. Headless CLI silently no-ops geometry-only 3MFs. **File→Import, not Open.**
21. The real bed is smaller than the bed: multi-material envelope (H2D both-nozzle zone **316×295**) validated with a physical bedcheck part, not the spec sheet.
22. Filament-change economics shape design: order the color stack so dual-nozzle swaps are free; surface the flush volumes (~700–800 mm³ black→clear).
23. Pair geometry features with their slicer interactions in the print card (baked-fuzz lens → bottom shells +1 kills internal-island artifacts).

**Process**
24. **Approved designs are frozen**; scope feedback narrowly; when a change creates a new problem, revert rather than engineer on top (the bridging incident).
25. Archive approved previews before regenerating.
26. Numeric truth lives in one regenerated place; weights from rendered meshes, not estimates (est. 1 kg vs real 3.1 kg).
27. Label every piece (debossed, mirrored on the back) — and show the labels in previews so nobody asks "wtf is 1C?"

## C. Calibrated constants (provenance: printed tests)

| Constant | Value | Note |
|---|---|---|
| Bullet pixel | dome Ø8, barrel Ø12, flange Ø13.6×2, tip→flange 5.5 | measured datasheet |
| dome_clear / plate bore | 4.0 / **12.3** | collar bore Ø12.19 |
| Collar | OD 16 × h 2.0, bore 12.19→11.44 lip, 0.5 mm 45° lead-in | press-fit, calibrated |
| led_void / led_clear | 14.0 / 2.5 | 13 jammed pixels |
| Pixel pitch | **17** (solid-glow) / 20 (board) | chord-measured |
| Pixel floors | flange 14.5; snug 13.0–14.5; seam keepout 12.5 | |
| Lens press fit | **-0.2 mm** interference | 0.6→0.0 all failed |
| Lid plug fit | 0.2 mm total | 0.5 loose |
| Channel | **18 interior / 22 outer** (0.8 white + 1.2 black walls) | tube ~11.8 widened +3/side |
| Stack | 2.0 plate + 0.4 liner floor + 19 wall height + **1.2 lens** | |
| Air gap | ~15 mm | 35/50 washed out |
| Nesting clearance | ≥26 mm centerline (=band+4); crossings ≥25° exempt | |
| Corridor cuts | ≥5 mm from walls; seam relief 0.06/face | |
| Bed (H2D dual) | **316×295** both-nozzle zone | bedcheck-validated |
| Fuzz V3 / V8 | 1.5/0.8 random / **2.0/0.6 pyramid-jitter** (0.6–1.0×h, ±0.25 cell, max-union) | |
| Anti-sliver | floor 0.02; base 0.1504 off-lattice; field min 0.1704; sample cell/3 | |
| Print | 0.16–0.20 layer, 2 walls, 10% gyroid, 6 top/**7 bottom**, concentric top, no supports | |
| Power | 0.25 W/px @24 V; PSU cap ~80%; strings of 50 | 150 W PSU for 591 px |
| Screws | Ø4.5, corners @12 mm inset, mid-span >160 mm | zip-ties removed |
| QA | uncovered ink >100 mm² = FAIL (60 mm² note) | |

## D. Abandoned (do not resurrect without new evidence)

Locating lips, drop-in panels, slide-over caps, flanged lids (superseded), 35/50 mm gaps, perforated masks, gyroid fill, TIR cones, separate press-fit production lens, striped 2-color lens, slicer-settings haze, Bambu fuzzy skin on tops, per-letter tiles, letter splitting for +40 mm, element-5 board, 45% outline bolt (channels collide — physics), straight full-height seams, neon-break seam pullbacks, bridging approved letterforms (reverted at user direction), greedy pixel stacking, dead-band for pyramid textures, S=4 sampling, degenerate-dropping mesh healer, Bambu headless CLI, zip-tie holes, 8" strings with coiled slack, raster-sourced "mid dash".
