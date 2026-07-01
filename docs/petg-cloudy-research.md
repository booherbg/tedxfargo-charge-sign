# Making transparent PETG print CLOUDY (for LED diffusion)

Research summary (2026-07-01). Goal: take on-hand *clear* PETG and make it milky/diffusing.

**Mechanism:** haze = light scattering at internal air↔plastic interfaces (unfused
bonding-neck gaps, micro-voids, moisture bubbles; air n≈1.0 vs PETG n≈1.57, same physics
as frosted glass). To make PETG cloudy you **maximize** those interfaces — the exact
inverse of every "crystal-clear PETG" recipe.

## Ranked methods (best → worst for an *even* milky glow)

| # | Method | Setting | New filament? | Notes |
|---|--------|---------|---------------|-------|
| 1 | **Textured PEI plate, face-DOWN** | use the H2D's textured plate; print diffuser face against it | **No** (own it) | Most *even*, zero tuning. Frosts only the face touching the plate — but our lens already prints face-down, so it's free. |
| 2 | **Under-extrude** | flow **~88–92%** (start 90%, lower = more haze) | **No** | Even *volumetric* haze through the whole wall; stacks with #1. Don't go so low layers fail/weaken. Test. |
| 3 | **Cooler nozzle** | **~225–235°C** (vs 240–260 for clarity) | **No** | Incomplete fusion → voids. Modest lever; non-monotonic (too hot also hazes). Too cold → blotchy. |
| 4 | **High part-cooling fan** | **80–100%** (vs 0% for clarity) | **No** | Locks in layer boundaries. Weak effect ("a bit milky") and can be uneven. |
| 5 | **Fast print speed** | above the ~20mm/s clarity setting | **No** | ⚠ Least reliable — the peer-reviewed study found faster = *clearer*, and it adds uneven ringing. Don't lead with it. |
| — | **Wet/undried PETG** | skip drying | No | ❌ Not recommended — real mechanism (steam microbubbles) but uncontrolled, blotchy, weakens the part. |

**Recommended starting recipe (H2D, clear PETG):** face-**down** on the textured plate +
flow **~90%** + nozzle **~230°C** + fan **~100%**; dial flow down further for more milk.

## Refuted / not a lever
- **Layer height** — NOT a reliable lever. The study found **0.2mm = peak clarity**; both
  thinner *and* thicker transmit less, so "thicker = cloudier" is false. Don't rely on it.

## Untested here (no verified evidence — treat as unknown)
- Infill pattern/gyroid volumetric scatter behind a thin skin; top/bottom/wall counts
- Fuzzy skin on the diffuser face
- Matte/frosted PETG or diffusion-additive filament
- Post-processing: sanding, bead/sand blasting, matte clear-coat spray, solvent vapor
  (note: PETG is largely **acetone-resistant**, so ABS-style vapor smoothing likely won't work)
- Bed temperature effect on face clarity

## How this fits our project
- If the **PLA heat test passes**, PLA is cloudy for free → this is moot.
- If heat forces **PETG**, two paths: (a) the **white-skin-over-clear** trick (V2 lens) —
  the white layer does the diffusing, so PETG's clarity no longer matters (likely simplest);
  or (b) make the PETG itself cloudy via the recipe above (no second filament needed).
- **Free win regardless of material:** the lens already prints face-down, so using the
  **textured plate** frosts the viewer face automatically.

Sources: [CNC Kitchen](https://www.cnckitchen.com/blog/transparent-fdm-3d-prints-are-clearly-stronger) ·
[Bambu wiki](https://wiki.bambulab.com/en/knowledge-sharing/transparent-petg) ·
[NCSU BioResources 2024](https://bioresources.cnr.ncsu.edu/resources/effect-of-slicing-parameters-on-the-light-transmittance-of-3d-printed-polyethylene-terephthalate-glycol-products/) ·
[3DBite](https://3dbite.com/transparent-glass-like-3d-prints-petg-pla-settings/) ·
[Hackaday](https://hackaday.com/2025/11/29/how-to-print-petg-as-transparently-as-possible/)
