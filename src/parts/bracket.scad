// Seam splice straps for the bolt board (spec 2026-07-10). WHITE PETG.
//   openscad -D STRAP=<1|2|3|4> -o strap.stl src/parts/bracket.scad
// Local printed frame: z=0 = FRONT face, printed ON THE BED (mates flush
// against the plate backs; an embedded collar lands in the same first-2mm
// orientation as the plate collars, so the calibrated press-fit transfers).
// Feature coords come PRE-MIRRORED from boltboard.py — the part is flipped
// about the u axis to install (chirality baked in the generator; see the
// flip-to-use gotcha).
include <../config.scad>
include <../collar.scad>
include <bracket_layout.scad>

STRAP = 1;

bk_web_t    = 4.0;    // web (= 2 flange pocket + 2 embedded collar)
bk_rail_h   = 8.0;    // stiffening rails above the web
bk_rail_w   = 5.0;
bk_pass_d   = 17.0;   // pixel pass-through (flange Ø13.6 + fingers)
bk_cham_d   = 21.0;   // insertion-guide chamfer mouth at the back face
bk_nut_af   = 7.2;    // M4 nut across-flats + fit
bk_nut_t    = 3.2;
bk_scr_d    = 4.5;
bk_flange_d = 14.5;   // flange pocket over an embedded collar
bk_boss_d   = 16.0;   // leg-socket boss
bk_boss_h   = 10.0;
bk_leg_d    = 10.2;   // friction-fit Ø10 leg pin

i  = STRAP - 1;
u0 = bk_span[i][0];
u1 = bk_span[i][1];
W2 = bk_strap_w / 2;

module web2d() {                       // rounded-corner strap outline
    offset(r = 4) offset(delta = -4)
        translate([u0, -W2]) square([u1 - u0, bk_strap_w]);
}

union() {
    difference() {
        union() {
            linear_extrude(bk_web_t) web2d();
            for (s = [-1, 1])          // edge rails, inset from the ends
                translate([u0 + 6, s > 0 ? W2 - bk_rail_w : -W2, bk_web_t])
                    cube([u1 - u0 - 12, bk_rail_w, bk_rail_h]);
            for (q = bk_socket[i])
                translate([q[0], q[1], 0])
                    cylinder(h = bk_web_t + bk_boss_h, d = bk_boss_d);
        }
        for (q = bk_pass[i]) {
            if (abs(q[1]) > W2 - 1 - bk_cham_d/2) {
                // hole (or its chamfer) breaks the strap edge: cut a SLOT out
                // through the edge so no sliver survives between hole and rim
                sgn = q[1] > 0 ? 1 : -1;
                translate([0, 0, -0.1]) linear_extrude(2.2) hull() {
                    translate([q[0], q[1]]) circle(d = bk_pass_d);
                    translate([q[0], sgn * (W2 + 12)]) circle(d = bk_pass_d);
                }
                translate([0, 0, 2]) linear_extrude(bk_rail_h + bk_web_t - 1.9) hull() {
                    translate([q[0], q[1]]) circle(d = bk_cham_d);
                    translate([q[0], sgn * (W2 + 12)]) circle(d = bk_cham_d);
                }
            } else translate([q[0], q[1], 0]) {
                translate([0, 0, -0.1]) cylinder(h = 2.2, d = bk_pass_d);
                translate([0, 0, 2]) cylinder(h = 2.01, d1 = bk_pass_d, d2 = bk_cham_d);
                translate([0, 0, bk_web_t])  // continue through a rail if hit
                    cylinder(h = bk_rail_h + 0.1, d = bk_cham_d);
            }
        }
        for (q = bk_collar[i]) translate([q[0], q[1], 0]) {
            translate([0, 0, -0.1]) cylinder(h = 2.1, d = 15.8);  // collar seat, 0.1 weld
            translate([0, 0, 2]) cylinder(h = bk_web_t, d = bk_flange_d);
        }
        for (q = bk_nut[i]) translate([q[0], q[1], 0]) {
            translate([0, 0, -0.1])
                cylinder(h = bk_web_t + 0.2, d = bk_scr_d);
            translate([0, 0, bk_web_t - bk_nut_t])
                cylinder(h = bk_nut_t + 0.1, d = bk_nut_af / cos(30), $fn = 6);
        }
        for (q = bk_socket[i])         // blind leg bore (1mm front floor)
            translate([q[0], q[1], 1])
                cylinder(h = bk_web_t + bk_boss_h, d = bk_leg_d);
    }
    for (q = bk_collar[i])             // calibrated press-fit, front 2mm,
        translate([q[0], q[1], 0])     // welded into the seat AFTER the cuts
            collar_solid();
}
