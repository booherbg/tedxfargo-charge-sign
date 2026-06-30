bolt_pts  = [[155.0,300.0], [75.0,180.0], [130.0,180.0], [45.0,30.0]];
pixel_pts = [[155.0,300.0], [145.5,285.8], [136.0,271.5], [126.5,257.2], [117.0,243.0], [107.5,228.8], [98.0,214.5], [88.5,200.2], [79.0,186.0], [95.1,180.0], [112.3,180.0], [129.4,180.0], [121.4,164.8], [113.0,149.9], [104.5,135.1], [96.1,120.2], [87.6,105.3], [79.2,90.4], [70.8,75.5], [62.3,60.6], [53.9,45.7], [45.4,30.8]];

// ===== CHARGE lightning-bolt test piece — option C (~18mm channel) =====
bolt_inner     = 18;                       // channel interior (collar O16 fits)
bolt_wall      = 2;                         // wall thickness
bolt_outer     = bolt_inner + 2*bolt_wall; // 22mm outer stroke
bolt_gap       = 15;                       // LED-tip -> lens
bolt_ch_h      = dome_clear + bolt_gap;    // wall height above plate
bolt_lens_t    = 1.5;                       // lens face thickness  <-- TUNE (look/diffusion; = white-base layer count if 2-tone)
bolt_lip_h     = 2;                         // lens locating lip depth  <-- TUNE (how far the lip grips into the channel)
bolt_lip_clear = -0.2;                      // CONFIRMED: 0.2mm interference = perfect snap-in on the printed full lens (clear PETG lip on white-PLA base), 2026-06-30
bolt_lip_t     = 1.2;                       // lip wall thickness

module bolt_stroke(w) {
    for (i = [0 : len(bolt_pts) - 2])
        hull() {
            translate(bolt_pts[i])     circle(d = w);
            translate(bolt_pts[i + 1]) circle(d = w);
        }
}

// wall_h = channel wall height above the plate (gap = wall_h - dome_clear).
// The lens caps the cross-section, so the SAME lens fits any wall_h.
module bolt_shell(wall_h = bolt_ch_h) {
    difference() {
        union() {
            linear_extrude(plate_t) bolt_stroke(bolt_outer);
            translate([0, 0, plate_t]) linear_extrude(wall_h)
                difference() { bolt_stroke(bolt_outer); bolt_stroke(bolt_inner); }
        }
        for (p = pixel_pts)
            translate([p[0], p[1], -0.1]) cylinder(h = plate_t + 0.2, d = pixel_through);
    }
    for (p = pixel_pts) place_collar(p[0], p[1]);
}

module bolt_lens() {
    // Pre-mirror: same chirality-on-flip reason as bolt_overcap (this lens is
    // printed face-down and flipped lip-down to drop into the channel).
    mirror([1, 0, 0]) union() {
        linear_extrude(bolt_lens_t) bolt_stroke(bolt_outer);
        translate([0, 0, bolt_lens_t]) linear_extrude(bolt_lip_h)
            difference() {
                bolt_stroke(bolt_inner - bolt_lip_clear);
                bolt_stroke(bolt_inner - bolt_lip_clear - 2 * bolt_lip_t);
            }
    }
}

// ----- snap-OVER lens: a cap that wraps the WHOLE bolt outside (skirt grips the
// 22mm outer wall). Works because the bolt is a single isolated piece. Top = the
// diffuser face. Print top-down, flip in use; fits any bolt height.
// 2-filament: clear for the first cap_top_t (top), white above (skirt) via a
// slicer height color-change. 3-filament: also paint the skirt's outer wall black.
cap_clear   = 0.3;   // skirt-inner = bolt_outer + this (slide/snap over)
cap_wall    = 1.6;   // skirt wall thickness
cap_top_t   = 1.2;   // diffuser top thickness
cap_skirt_h = 9;     // how far the skirt wraps down the bolt sides

module bolt_overcap() {
    si = bolt_outer + cap_clear;
    so = si + 2 * cap_wall;
    // Pre-mirror: this cap prints skirt-up (top face on bed) and is FLIPPED to
    // seat. A flip mirrors the footprint, and the bolt is chiral, so without this
    // the flipped cap is a backwards bolt that won't register. Mirroring here means
    // the flipped part is just a rotation of the bolt footprint -> aligns by eye.
    mirror([1, 0, 0]) union() {
        linear_extrude(cap_top_t) bolt_stroke(so);
        translate([0, 0, cap_top_t]) linear_extrude(cap_skirt_h)
            difference() { bolt_stroke(so); bolt_stroke(si); }
    }
}

// Fit-test chunk: a short straight section of the over-cap at a chosen skirt
// clearance. Slide it onto a straight part of the printed bolt to feel the fit.
// `marks` debossed dots on the bed face = which one it is (more dots = tighter).
module cap_chunk(clear, marks, L = 45) {
    si = bolt_outer + clear;
    so = si + 2 * cap_wall;
    difference() {
        union() {
            linear_extrude(cap_top_t)
                hull() { translate([-L/2,0]) circle(d=so); translate([L/2,0]) circle(d=so); }
            translate([0,0,cap_top_t]) linear_extrude(cap_skirt_h)
                difference() {
                    hull() { translate([-L/2,0]) circle(d=so); translate([L/2,0]) circle(d=so); }
                    hull() { translate([-L/2,0]) circle(d=si); translate([L/2,0]) circle(d=si); }
                }
        }
        for (i = [0 : marks - 1])
            translate([-L/2 + 9 + i*4, 0, -0.1]) cylinder(h = 0.8, d = 1.8);
    }
}

// Fit-test slice of the INNER lens: a short STRAIGHT section of the lens face +
// locating lip at a chosen lip clearance. Press the lip into a straight run of
// the printed channel (the bolt's middle segment is ~55mm straight) to feel the
// fit -- no need to print a whole lightning bolt. `clear` = total lip clearance
// into the channel (lip outer = bolt_inner - clear); SMALLER = tighter. `marks`
// debossed dots on the bed/face = which one (more dots = tighter). Straight =>
// mirror-symmetric, so no chirality concern (unlike the full lens).
module lens_chunk(clear, marks, L = 40, label = "") {
    lip_o = bolt_inner - clear;          // lip outer width (drops into channel)
    lip_i = lip_o - 2 * bolt_lip_t;      // lip inner width
    difference() {
        union() {
            // face: full outer width, bed-face down
            linear_extrude(bolt_lens_t)
                hull() { translate([-L/2,0]) circle(d=bolt_outer); translate([L/2,0]) circle(d=bolt_outer); }
            // locating lip on top of the face
            translate([0,0,bolt_lens_t]) linear_extrude(bolt_lip_h)
                difference() {
                    hull() { translate([-L/2,0]) circle(d=lip_o); translate([L/2,0]) circle(d=lip_o); }
                    hull() { translate([-L/2,0]) circle(d=lip_i); translate([L/2,0]) circle(d=lip_i); }
                }
        }
        // dots = quick tightness order (more = tighter), at the centerline
        for (i = [0 : marks - 1])
            translate([-L/2 + 9 + i*4, 0, -0.1]) cylinder(h = 0.8, d = 1.8);
        // clearance value debossed on the bed face (mirrored to read from below)
        if (label != "")
            translate([0, -bolt_outer/2 + 4, -0.1]) linear_extrude(0.9)
                mirror([1,0,0]) text(label, size=4.5, halign="center", valign="center");
    }
}
