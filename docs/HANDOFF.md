# TEDxFargo CHARGE — Sign Build Handoff

**What this project is:** a 3D-printed, LED-lit **physical replica of the TEDxFargo CHARGE 2026
neon-billboard logo** (`assets/tedxfargo-full-logo.png`). We print the letters and lightning bolt as
**white-reflector channels capped with a chunky clear "fuzzy" diffuser lens**, lit from behind by
addressable 12mm bullet pixels, to recreate the neon look. Retro neon-billboard aesthetic.

> Read this top-to-bottom to get oriented. Canonical numeric params live in `docs/locked-specs.md`;
> this doc is the story, the decisions, and the plan. **We are faithfully replicating the logo**, not
> designing a new one.

---

## 0. Where we are
- **Validated:** the full diffusion/lens recipe (below) — via a printed 8-cell test matrix, a bolt, and
  a 4-way fuzzy-texture bake-off. The look is **locked and working**.
- **Current scope:** the **CHARGE** wordmark (6 letters) **+ the red lightning bolt**. The rest of the
  billboard (arrow, TEDxFargo badge, "2026", yellow border, truss) is later scope.
- **Next build step:** a **tube-centerline extractor** to auto-place pixels + generate the letter
  geometry from the SVGs. Everything upstream of that is done and proven.

## 1. Hardware
- **Printer:** Bambu **H2D** — dual nozzle, 300×320×325 build, **textured PEI plate**, 65°C chamber.
  The 3-color cross-section needs AMS or filament changes.
- **Pixels:** 12mm **24V bullet pixels** — dome **Ø8**, barrel **Ø12**, flange **Ø13.6×2mm**,
  dome-tip→flange **5.5mm**. **Own 300; buying 300 more (→600).** 150W/24V PSU.
- **Collar:** `assets/bullet-collar.stl` — calibrated press-fit ring for the pixel (bore ~Ø12.19).
- **Filament:** **black + white + clear.** Clear **PLA** is the diffuser (naturally cloudy = ideal);
  PLA also snaps/fits fine. PETG only if heat ever demands it.

## 2. Diffusion recipe — the core win (validated)
Every lit element uses the same cross-section, **printed lens-UP, no supports**:

**white reflective interior  →  ~15mm air gap  →  chunky clear lens with a BAKED fuzzy top**

- **Fuzzy skin = baked geometry** (a random height-field on the lens top). Bambu's fuzzy-skin only
  textures vertical walls, so we bake it. **Winner = V3: ~1.5mm bump cells, ~0.8mm height** — best
  balance of texture + brightness, **hides individual LEDs**, prints clean (no supports/spaghetti).
  Regenerate a grid: `tools/make_fuzz.py OUT <cell_mm> <height_mm>` (V3 = `1.5 0.8`).
- **White interior recycles light** → ~same brightness with fewer LEDs, and far more even. **Never a
  dark surface facing the LEDs.**
- **Top surface pattern: Concentric.** Print settings (Adafruit-derived, verified): 0.16mm layer,
  0.42 line, 2 walls, 10% gyroid, 6 top/bottom, supports off, brim, bridge fan on.

## 3. The 3-color letter/channel cross-section
1. **BLACK** — the tile base (billboard negative space) + the channel's outer structure.
2. **WHITE** — a couple of layers lining the channel **rear (floor) + inner walls** (the reflector).
3. **CLEAR** — the chunky lens on top with the **V3 baked fuzzy skin**.

So from the front: black frame/background, glowing white-lined channels, capped by a frosted clear lens.

## 4. Letters — how they're built
- The logo letters are **hollow neon outlines** — the neon tube traces **both edges** of every stroke.
  We keep this exactly. Source art: `assets/svg/{C,H,A,R,G,E,CHARGE}.svg` (converted from
  `assets/letters/*.eps` via `tools/eps2svg.sh`). **Both neon lines are lit.**
- **The one wrinkle is scale:** at ~250–300mm cap height each neon line is only **~12mm** wide — same
  as a Ø12 pixel, too thin to hold one. **Fix: widen each tube +3mm/side → ~18mm** (fits pixel +
  collar + walls) while **keeping the hollow-outline look** (the two lines stay separate — verified).
- **Size — NO letter splitting.** Cap height **270mm**; **rotate the wide letters 90°** so their width
  runs along the 320mm bed axis (at 270mm the widest, H, is ~320mm = the full bed). **Sign ≈ 1.6m wide.**
  Each letter = one rectangular tile. (Absolute max ~310mm, but that splits ~5 of 6 letters — not worth it.)
- **Pixels — TIGHT ~17mm pitch** (smooth solid-tube glow): CHARGE + bolt ≈ **~510 pixels** at 270mm cap
  → within the 600 budget. (Sparser ~32mm ≈ 270px is the fallback.)
- **Each letter tile** = the 3-color cross-section (black base + white-lined channel + fuzzy clear lens),
  pixels plugged in from behind, tiles butt together on a rear rail/backer that hides the wiring.

## 5. The lightning bolt (already built)
- `src/bolt.scad` — `bolt_shell` (the channel + collars along `pixel_pts`) + `bolt_lens` (the lens).
  The bolt is a **solid-stroke** channel (the whole stroke lit), path from hand-placed `pixel_pts`
  (~22 px @ ~17mm). **Lens fit locked: `bolt_lip_clear = -0.2`** (0.2mm interference press-fit,
  material-robust). Letters reuse this exact channel construction along the neon path.

## 6. Repo map
- `src/config.scad` — global params (pixel datasheet, collar, plate, gaps).
- `src/bolt.scad` — bolt shell + lens + fit-test slices (`lens_chunk`) + 2-color stripe variants.
- `src/testbox.scad` — straight 5-LED stroke test box (white shell + integrated lens); `fuzzy_lens()`
  + `tools/make_fuzz.py` grids (`fuzz_v1..v4.dat`) — the fuzzy bake-off (V3 won).
- `src/lens_cell.scad` — the 8-cell diffusion test matrix (how we found the recipe).
- `src/collar.scad` — `place_collar()` (imports the calibrated collar STL).
- `src/parts/*.scad` — thin entry files (one per printable STL); `letter_viz.scad`/`svg_bbox.scad` are
  planning helpers.
- `tools/` — `eps2svg.sh` (letters), `make_3mf.py` (combine white+clear STLs → Bambu 2-color 3MF),
  `make_fuzz.py` (fuzzy height grids). **`make_3mf.py` writes Bambu's real `model_settings.config`
  part→extruder map — standard 3MF `<basematerials>` is ignored by Bambu.**
- `assets/` — `bullet-collar.stl`, `svg/` letters, `tedxfargo-full-logo.png`, EPS letters.
- `docs/` — `locked-specs.md`, `print-lens-matrix.md`, `petg-cloudy-research.md`,
  `superpowers/specs/2026-06-29-integrated-lens-design.md`; `sign-preview/index.html` (letter viz).
- `build.sh` — regenerate STLs into `stl/` (**gitignored** — artifacts). `openscad -o out.stl part.scad`.

## 7. Non-obvious decisions & gotchas
- **Chiral flip-mirror:** any part that prints face-down and is *flipped* to use must be **pre-mirrored**
  (`mirror([1,0,0])`) — the bolt is chiral, so an un-mirrored flip lands a backwards bolt. (Letters/testbox
  print in use-orientation, so this doesn't bite them.)
- **Widen the tubes, don't shrink the letters:** +3mm/side keeps the hollow-outline look at ~18mm.
- **White interior is mandatory** (recycling); black interior kills brightness + shows the source.
- **Fuzzy is baked** (Bambu can't texture tops); V3 texture won.
- **Pixel clearance:** any solid optic over the LED needs `led_void`=14 / `led_clear`=2.5 headroom
  (`lens_pixel_collision.scad` verifies). Open-cavity (A0-style) letters don't have this issue.

## 8. Next steps (priority order)
1. **Centerline extractor** — skeletonize each letter SVG → ordered path → resample at 17mm → pixel
   points; offset the path ±(tube/2) for the widened tube. Needs image libs (`numpy`/`pillow`/
   `scikit-image`) *or* a dependency-free Zhang-Suen thinner. **This unblocks everything.**
2. **Generate CHARGE** — per letter: 3-color tile (black base + white-lined channel + fuzzy clear lens),
   collars at pitch, sized to ~250mm cap (no split). Exact pixel count falls out.
3. **Integrate the bolt** into the layout.
4. **Mounting/wiring** — rear rail or black backer board; controller tucked behind. (Deferred, art shows a truss.)
5. **Full-billboard extras** — arrow, TEDxFargo badge, 2026, yellow border. (Later scope.)

## 9. How to sanity-check the build works
- `./build.sh` regenerates all STLs. Render a preview: `openscad -o out.png --viewall src/parts/<x>.scad`.
- Two-color test: `stl/testbox_fuzz_v3_2color.3mf` is the winning lens texture on a 5-LED stroke.
- The whole recipe is proven on printed parts — the remaining work is **geometry generation for the letters.**
