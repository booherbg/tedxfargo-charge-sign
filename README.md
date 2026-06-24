# TEDxFargo CHARGE — LED Sign

Parametric OpenSCAD system for generating 3D-printable STLs for an illuminated
"CHARGE" sign: channel-letter shells lit from behind by 12mm bullet pixels
through a clear, swappable diffuser panel.

See [`docs/superpowers/specs/2026-06-24-charge-led-sign-design.md`](docs/superpowers/specs/2026-06-24-charge-led-sign-design.md)
for the full design.

## Build

```bash
./build.sh          # renders every part in src/parts/ to ./stl/
```

Requires [OpenSCAD](https://openscad.org/). Override the binary with
`OPENSCAD=/path/to/openscad ./build.sh`.

## Layout

```
src/config.scad     all tunable knobs (edit this, then rebuild)
src/collar.scad     imports the calibrated press-fit collar
src/diffuser.scad   swappable diffuser panel
src/coupon.scad     depth-ladder test coupon
src/parts/*.scad    build targets (open any in the OpenSCAD GUI)
assets/             bullet-collar.stl, letter EPS, logo
stl/                generated output (git-ignored)
```

## First print: the stackup coupon

`stl/coupon_body.stl` is a 3-cell test rig with LED-to-panel gaps of 20 / 35 /
50mm and three merged press-fit collars. Print it in **opaque** filament. Print
`panel_{1,2,3}mm.stl` in **clear** filament and vary slicer infill
(gyroid/grid, top & bottom solid layers = 0) to test the diffuser. Drop a panel
onto each chimney, press a pixel into each collar, and compare.

> Tune `dome_clear` in `config.scad` to your actual pixel's dome protrusion —
> the gap distances depend on it.
