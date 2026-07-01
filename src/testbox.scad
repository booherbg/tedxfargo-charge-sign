// ===== Straight 5-LED letter-stroke test box =====
// The A0 recipe (white reflector shell + integrated clear lens over an air gap) as a
// short straight stroke segment, at the bolt's pixel pitch. Purpose: try the
// INTEGRATED-lens path and see what fuzzy skin does on the lens face.
//
// PRINT AS-ORIENTED = plate on the bed, LENS UP. The lens top is the outer surface,
// so enable Fuzzy Skin on the clear part in the slicer. Pixels plug into the collars
// from the BOTTOM after printing. NO SUPPORTS: walls are vertical, and the clear lens
// is a ~18mm bridge anchored on both long walls (roof over the channel).
//
// Two-material: WHITE shell -> filament 1, CLEAR lens -> filament 2. Export both,
// combine with tools/make_3mf.py.

include <config.scad>
include <collar.scad>

tb_n      = 5;                      // number of pixels
tb_pitch  = 17;                    // bolt pixel pitch (mm)
tb_inner  = 18;                    // channel interior (= bolt); collar O16 fits
tb_wall   = 2;                     // white wall thickness
tb_outer  = tb_inner + 2*tb_wall; // 22mm outer
tb_gap    = 15;                    // LED-tip -> lens air gap (winning A0 value)
tb_wall_h = dome_clear + tb_gap;  // wall height above the plate (19mm)
tb_lens_t = 1.2;                  // clear lens thickness
tb_fuse   = 0.1;                  // white/clear overlap so the slicer fuses them

function tb_x(i) = i * tb_pitch;  // pixel x positions: 0 .. (n-1)*pitch

module tb_stroke(w) {             // straight stadium: rounded caps past the end pixels
    hull() { translate([tb_x(0),0]) circle(d=w); translate([tb_x(tb_n-1),0]) circle(d=w); }
}

module testbox_white() {          // plate + walls + collars (pixels plug in from below)
    difference() {
        union() {
            linear_extrude(plate_t) tb_stroke(tb_outer);
            translate([0,0,plate_t]) linear_extrude(tb_wall_h)
                difference() { tb_stroke(tb_outer); tb_stroke(tb_inner); }
        }
        for (i=[0:tb_n-1]) translate([tb_x(i),0,-0.1]) cylinder(h=plate_t+0.2, d=pixel_through);
    }
    for (i=[0:tb_n-1]) place_collar(tb_x(i), 0);
}

module testbox_clear() {          // integrated lens roof (bridges the channel), smooth top
    translate([0,0,plate_t+tb_wall_h-tb_fuse])
        linear_extrude(tb_lens_t+tb_fuse) tb_stroke(tb_outer);
}

// ---- baked "fuzzy skin": a random bumpy top on the lens to scatter/soften light ----
// Bambu's fuzzy skin only textures vertical walls, so we bake the noise into the top
// geometry. Heights from src/parts/fuzz.dat (regen: tools/make_fuzz.py). Print lens-UP.
fuzz_h = 0.55;   // peak bump height above the flat lens top
module testbox_clear_fuzzy() {
    z0  = plate_t + tb_wall_h - tb_fuse;                 // fused to walls
    top = plate_t + tb_wall_h + tb_lens_t;              // nominal flat top
    union() {
        translate([0,0,z0]) linear_extrude(top - z0) tb_stroke(tb_outer);   // flat lens body
        intersection() {                                                     // random bumps, clipped
            translate([tb_x(tb_n-1)/2, 0, top-0.1]) surface(file="fuzz.dat", center=true, convexity=8);
            translate([0,0,top-0.2]) linear_extrude(fuzz_h+0.6) tb_stroke(tb_outer);
        }
    }
}
