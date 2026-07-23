// Backer-frame corner-L rail segments (spec 2026-07-21). WHITE PETG.
//   openscad -D SEG=<1|2|3|4> -o frame_segN.stl src/parts/frame.scad
//   SEG: 1=bottom-left 2=bottom-right 3=top-right 4=top-left
// Board coords, z=0 = plate BACK, +z into the cavity. Prints FLANGE-DOWN
// (flange + tray floors on the bed); the 2 mm reveal is a snap-on trim
// strip (frame_parts PART=6), not part of this body.
include <frame_layout.scad>

SEG = 1;

ox0 = -fr_clr - fr_wall;  ox1 = fr_face[0] + fr_clr + fr_wall;
oy0 = -fr_clr - fr_wall;  oy1 = fr_face[1] + fr_clr + fr_wall;
inx0 = ox0 + fr_wall;  inx1 = ox1 - fr_wall;   // wall inner faces (-0.5 / +.5)
iny0 = oy0 + fr_wall;  iny1 = oy1 - fr_wall;
wz1 = fr_cavity + fr_panel_t;            // wall top (38.4) = panel back plane
lz0 = fr_cavity - fr_ledge_t;            // ledge underside (32)
chw = fr_ledge_w + fr_clr;               // chamfer reach inboard of the wall

module oring(w) difference() {           // perimeter band, width w inboard
    translate([ox0, oy0]) square([ox1 - ox0, oy1 - oy0]);
    translate([ox0 + w, oy0 + w]) square([ox1 - ox0 - 2*w, oy1 - oy0 - 2*w]);
}

// 45-degree support wedge under the ledge ring (per side, corners overlap):
// hull of a hairline strip on the wall inner face (z lz0-chw) and the
// ledge-width strip at the ledge underside (z lz0)
module ledge_chamfer() {
    hull() {  // left
        translate([inx0, iny0, lz0 - chw]) cube([0.1, iny1 - iny0, 0.1]);
        translate([inx0, iny0, lz0]) cube([chw, iny1 - iny0, 0.1]);
    }
    hull() {  // right
        translate([inx1 - 0.1, iny0, lz0 - chw]) cube([0.1, iny1 - iny0, 0.1]);
        translate([inx1 - chw, iny0, lz0]) cube([chw, iny1 - iny0, 0.1]);
    }
    hull() {  // bottom
        translate([inx0, iny0, lz0 - chw]) cube([inx1 - inx0, 0.1, 0.1]);
        translate([inx0, iny0, lz0]) cube([inx1 - inx0, chw, 0.1]);
    }
    hull() {  // top
        translate([inx0, iny1 - 0.1, lz0 - chw]) cube([inx1 - inx0, 0.1, 0.1]);
        translate([inx0, iny1 - chw, lz0]) cube([inx1 - inx0, chw, 0.1]);
    }
}

module body() {
    linear_extrude(wz1) oring(fr_wall);                  // walls
    linear_extrude(fr_flange_t)
        oring(fr_wall + fr_clr + fr_flange_w);           // flange
    translate([0, 0, lz0]) linear_extrude(fr_ledge_t)
        oring(fr_wall + fr_clr + fr_ledge_w);            // panel ledge
    ledge_chamfer();
    // equipment tray floors (merge into wall + flange; z 0..flange_t)
    translate([inx0, fr_tray_psu[1], 0])
        cube([fr_tray_psu[2] - inx0, fr_tray_psu[3] - fr_tray_psu[1],
              fr_flange_t]);
    translate([fr_tray_ctl[0], fr_tray_ctl[1], 0])
        cube([inx1 - fr_tray_ctl[0], fr_tray_ctl[3] - fr_tray_ctl[1],
              fr_flange_t]);
    // ledge-boss columns (rise from flange to ledge, pilots cut later)
    for (q = fr_ledge_boss)
        translate([q[0], q[1], fr_flange_t])
            cylinder(h = fr_cavity - fr_flange_t, d = 7);
    // handle pads under the top face, gland pilot pads, exterior ctl pads
    for (h = fr_handle) for (bx = [h[2], h[3]])
        translate([bx - 10, iny1 - 12, wz1 - 12]) cube([20, 12, 12]);
    if (fr_gland_plate)
        for (gy = [fr_gland[0] - 20, fr_gland[0] + 20])
            translate([inx0, gy, fr_gland[1]]) rotate([0, 90, 0])
                cylinder(h = 6, d = 7);
    for (q = fr_ctl_ext)
        translate([inx0, q[0], q[1]]) rotate([0, 90, 0])
            cylinder(h = 6, d = 10);
    // zip-tie fin inboard of the cable hole: saddle at hole height cradles
    // the cable, tie threads the slot below and lashes it (strain relief)
    if (!fr_gland_plate) difference() {
        translate([5, fr_gland[0] - 8, 4]) cube([3, 16, 22]);
        translate([4.9, fr_gland[0], fr_gland[1]]) rotate([0, 90, 0])
            cylinder(h = 3.2, d = 6.8);                   // saddle root
        translate([4.9, fr_gland[0] - 3.4, fr_gland[1]])
            cube([3.2, 6.8, 22]);                         // open the top
        translate([4.9, fr_gland[0] - 4, 6]) cube([3.2, 8, 6]);  // tie slot
    }
    // feet pads on the bottom wall inner face
    for (fx = fr_feet)
        translate([fx - 18, iny0 - 0.1, 0]) cube([36, 12.1, 14]);
    // dovetail joint pads (inner face, spanning each segment boundary)
    translate([fr_joint[0] - 15, iny0 - 0.1, 4]) cube([30, 8.1, 30]);
    translate([fr_joint[0] - 15, iny1 - 8, 4]) cube([30, 8.1, 30]);
    translate([inx0 - 0.1, fr_joint[1] - 15, 4]) cube([8.1, 30, 30]);
    translate([inx1 - 8, fr_joint[1] - 15, 4]) cube([8.1, 30, 30]);
}

module bowtie(cl = 0) {                   // dovetail key outline
    hull() { translate([-12 - cl, -7 - cl]) square([3 + cl, 14 + 2*cl]);
             translate([-1.5, -4 - cl]) square([3, 8 + 2*cl]); }
    hull() { translate([9, -7 - cl]) square([3 + cl, 14 + 2*cl]);
             translate([-1.5, -4 - cl]) square([3, 8 + 2*cl]); }
}

module cuts() {
    for (q = fr_boss)                     // 14 plate screws: M4x12 self-tap
        translate([q[0], q[1], -0.1]) cylinder(h = fr_flange_t + 0.2, d = 3.4);
    for (q = fr_ledge_boss)               // panel M3x12 into ledge bosses
        translate([q[0], q[1], fr_cavity - 10.5]) cylinder(h = 10.7, d = 2.8);
    for (q = fr_psu_holes)                // LRS-100 rounds (M3, 3 mm max in)
        translate([q[0], q[1], -0.1]) cylinder(h = fr_flange_t + 0.2, d = 2.8);
    for (s = fr_psu_slots)                // LRS-50/75 shared slots
        translate([0, 0, -0.1]) linear_extrude(fr_flange_t + 0.2) hull() {
            translate([s[0], s[1]]) circle(d = 2.8);
            translate([s[2], s[3]]) circle(d = 2.8);
        }
    for (q = fr_ctl_holes)                // Elite shell end screws
        translate([q[0], q[1], -0.1]) cylinder(h = fr_flange_t + 0.2, d = 3.2);
    // gland: v1 = PG7 threaded straight into the 3.0 wall (Ø12.5 hole,
    // clamp limit 3.5); plate mode = outer recess + opening + 2 pilots
    if (fr_gland_plate) {
        translate([ox0 - 0.1, fr_gland[0] - 22.5, fr_gland[1] - 15])
            cube([1.6, 45, 30]);
        translate([ox0 - 0.1, fr_gland[0] - 18, fr_gland[1] - 11])
            cube([fr_wall + 6.2, 36, 22]);
        for (gy = [fr_gland[0] - 20, fr_gland[0] + 20])
            translate([ox0 - 0.1, gy, fr_gland[1]]) rotate([0, 90, 0])
                cylinder(h = fr_wall + 6.2, d = 2.8);
    } else
        translate([ox0 - 0.1, fr_gland[0], fr_gland[1]]) rotate([0, 90, 0])
            cylinder(h = fr_wall + 0.2, d = fr_gland_d);
    for (q = fr_ctl_ext)                  // exterior controller pilots
        translate([ox0 - 0.1, q[0], q[1]]) rotate([0, 90, 0])
            cylinder(h = fr_wall + 6.2, d = 3.4);
    for (h = fr_handle) for (bx = [h[2], h[3]])   // handle bolts: down (-y),
        translate([bx, oy1 + 0.1, wz1 - 7.5]) rotate([90, 0, 0])
            cylinder(h = fr_wall + 14.2, d = 3.4);  // 7.5 off the back plane
            // = the handle's mid-thickness -> back face lands flush
    for (fx = fr_feet) {                  // feet snap sockets, entered below:
        translate([fx - 7.3, oy0 - 0.1, 0.8])             // prong channel
            cube([14.6, fr_wall + 6.1, 3.6]);
        translate([fx - 9.3, iny0 + 1.5, 0.8])            // barb pocket
            cube([18.6, 3.0, 3.6]);
    }
    // dovetail pockets open at the pad inner faces + cross-screw pilots
    translate([fr_joint[0], iny0 + 8 + 0.1, 19]) rotate([90, 0, 0])
        linear_extrude(4.2) bowtie(0.15);
    translate([fr_joint[0], iny1 - 8 + 4.1, 19]) rotate([90, 0, 0])
        linear_extrude(4.2) bowtie(0.15);
    // side pockets: extrusion must run INTO the pads (rotate [90,0,90]
    // extrudes +x — that cut air on the left; caught on the seg1 slice)
    translate([inx0 + 8 + 0.1, fr_joint[1], 19]) rotate([90, 0, -90])
        linear_extrude(4.2) bowtie(0.15);
    translate([inx1 - 8 - 0.1, fr_joint[1], 19]) rotate([90, 0, 90])
        linear_extrude(4.2) bowtie(0.15);
    for (jx = [fr_joint[0] - 8, fr_joint[0] + 8]) {
        translate([jx, oy0 - 0.1, 19]) rotate([-90, 0, 0])
            cylinder(h = fr_wall + 8.2, d = 2.8);
        translate([jx, oy1 + 0.1, 19]) rotate([90, 0, 0])
            cylinder(h = fr_wall + 8.2, d = 2.8);
    }
    for (jy = [fr_joint[1] - 8, fr_joint[1] + 8]) {
        translate([ox0 - 0.1, jy, 19]) rotate([0, 90, 0])
            cylinder(h = fr_wall + 8.2, d = 2.8);
        translate([ox1 + 0.1, jy, 19]) rotate([0, -90, 0])
            cylinder(h = fr_wall + 8.2, d = 2.8);
    }
    // trim snap groove (only when trim strips are in use)
    if (fr_trim) translate([0, 0, 5.5]) linear_extrude(2) difference() {
        translate([ox0 - 0.01, oy0 - 0.01])
            square([ox1 - ox0 + 0.02, oy1 - oy0 + 0.02]);
        translate([ox0 + 0.8, oy0 + 0.8])
            square([ox1 - ox0 - 1.6, oy1 - oy0 - 1.6]);
    }
}

clipx = [[ox0, fr_joint[0]], [fr_joint[0], ox1],
         [fr_joint[0], ox1], [ox0, fr_joint[0]]][SEG - 1];
clipy = [[oy0, fr_joint[1]], [oy0, fr_joint[1]],
         [fr_joint[1], oy1], [fr_joint[1], oy1]][SEG - 1];

translate([-clipx[0], -clipy[0], 0]) intersection() {
    difference() { body(); cuts(); }
    translate([clipx[0], clipy[0], -1])
        cube([clipx[1] - clipx[0], clipy[1] - clipy[0], wz1 + 2]);
}
