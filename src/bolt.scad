bolt_pts  = [[155.0,300.0], [75.0,180.0], [130.0,180.0], [45.0,30.0]];
pixel_pts = [[155.0,300.0], [142.8,281.7], [130.6,263.3], [118.3,245.0], [106.1,226.7], [93.9,208.3], [81.7,190.0], [96.7,180.0], [118.8,180.0], [119.7,161.9], [108.9,142.8], [98.1,123.6], [87.2,104.5], [76.4,85.3], [65.5,66.2], [54.7,47.1], [45.0,30.0]];

// ===== CHARGE lightning-bolt test piece — option C (~18mm channel) =====
bolt_inner     = 18;                       // channel interior (collar O16 fits)
bolt_wall      = 2;                         // wall thickness
bolt_outer     = bolt_inner + 2*bolt_wall; // 22mm outer stroke
bolt_gap       = 15;                       // LED-tip -> lens
bolt_ch_h      = dome_clear + bolt_gap;    // wall height above plate
bolt_lens_t    = 1.5;                       // lens face thickness
bolt_lip_h     = 2;                         // lens locating lip depth
bolt_lip_clear = 0.6;                       // lip clearance into channel
bolt_lip_t     = 1.2;                       // lip wall thickness

module bolt_stroke(w) {
    for (i = [0 : len(bolt_pts) - 2])
        hull() {
            translate(bolt_pts[i])     circle(d = w);
            translate(bolt_pts[i + 1]) circle(d = w);
        }
}

module bolt_shell() {
    difference() {
        union() {
            linear_extrude(plate_t) bolt_stroke(bolt_outer);
            translate([0, 0, plate_t]) linear_extrude(bolt_ch_h)
                difference() { bolt_stroke(bolt_outer); bolt_stroke(bolt_inner); }
        }
        for (p = pixel_pts)
            translate([p[0], p[1], -0.1]) cylinder(h = plate_t + 0.2, d = pixel_through);
    }
    for (p = pixel_pts) place_collar(p[0], p[1]);
}

module bolt_lens() {
    union() {
        linear_extrude(bolt_lens_t) bolt_stroke(bolt_outer);
        translate([0, 0, bolt_lens_t]) linear_extrude(bolt_lip_h)
            difference() {
                bolt_stroke(bolt_inner - bolt_lip_clear);
                bolt_stroke(bolt_inner - bolt_lip_clear - 2 * bolt_lip_t);
            }
    }
}
