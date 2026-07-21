// Backer-frame back panels (spec 2026-07-21). WHITE PETG, 4 quadrants.
//   openscad -D PANEL=<1|2|3|4> -o frame_panelN.stl src/parts/frame_panel.scad
//   PANEL: 1=bottom-left 2=bottom-right 3=top-left 4=top-right (fr_panels)
// Modeled in board coords, skin z 36..38.4; emitted rotated so the OUTSIDE
// face prints on the bed (rotation, not mirror — chirality preserved).
// Shared edges half-lap: the lower-indexed panel at a joint carries the
// cavity-side (front) half; laps extend 3 past the joint each way.
include <frame_layout.scad>

PANEL = 1;

p  = fr_panels[PANEL - 1];
z0 = fr_cavity;  z1 = fr_cavity + fr_panel_t;  zm = z0 + fr_panel_t/2;
e  = 0.3;                                   // edge clearance
JX = fr_joint[0];  JY = fr_joint[1];

// shared edges [right, top, left, bottom] and who carries the FRONT half
shr   = [PANEL == 1 || PANEL == 3, PANEL == 1 || PANEL == 2,
         PANEL == 2 || PANEL == 4, PANEL == 3 || PANEL == 4];
front = [true, true, false, false];         // r/t = front lap, l/b = back lap

ex0 = shr[2] ? JX - 3 + e : p[0] + e;
ex1 = shr[0] ? JX + 3 - e : p[2] - e;
ey0 = shr[3] ? JY - 3 + e : p[1] + e;
ey1 = shr[1] ? JY + 3 - e : p[3] - e;

module lap_cuts() {                         // remove the complementary half
    if (shr[0]) translate([JX - 3, ey0 - 1, zm])
        cube([6, ey1 - ey0 + 2, fr_panel_t]);              // right: cut back
    if (shr[1]) translate([ex0 - 1, JY - 3, zm])
        cube([ex1 - ex0 + 2, 6, fr_panel_t]);              // top: cut back
    if (shr[2]) translate([JX - 3, ey0 - 1, z0 - 0.1])
        cube([6, ey1 - ey0 + 2, zm - z0 + 0.1]);           // left: cut front
    if (shr[3]) translate([ex0 - 1, JY - 3, z0 - 0.1])
        cube([ex1 - ex0 + 2, 6, zm - z0 + 0.1]);           // bottom: cut front
}

// zones where nothing may protrude below the skin (rails, trays, bosses)
module keepout() {
    translate([100, 279, 0]) cube([54, 553 - 279, z0]);    // S3 raised rails
    translate([127, 0, 0]) cube([54, 231, z0]);            // S4 raised rails
    translate([fr_tray_psu[0] - 2, fr_tray_psu[1] - 2, 0])
        cube([fr_tray_psu[2] - fr_tray_psu[0] + 4,
              fr_tray_psu[3] - fr_tray_psu[1] + 4, z0]);
    translate([fr_tray_ctl[0] - 2, fr_tray_ctl[1] - 2, 0])
        cube([fr_tray_ctl[2] - fr_tray_ctl[0] + 4,
              fr_tray_ctl[3] - fr_tray_ctl[1] + 4, z0]);
    for (q = fr_leg) translate([q[0], q[1], 0]) cylinder(h = z0, d = 20);
    for (q = fr_ledge_boss) translate([q[0], q[1], 0]) cylinder(h = z0, d = 12);
}

module ribs() {                             // 3-wide stiffeners, 4 deep
    for (rx = [ex0 + 40 : 60 : ex1 - 20])
        translate([rx, ey0 + 10, z0 - 4]) cube([3, ey1 - ey0 - 20, 4.1]);
    for (ry = [ey0 + 40 : 60 : ey1 - 20])
        translate([ex0 + 10, ry, z0 - 4]) cube([ex1 - ex0 - 20, 3, 4.1]);
}

module hood(l = 22)                         // 45° louver visor, open downward
    translate([-l/2 - 1.5, 2.2, z0]) rotate([135, 0, 0])
        cube([l + 3, 4.4, 1.2]);

vrows = (PANEL <= 2) ? fr_vent_intake : fr_vent_exhaust;

module louver_slits() {
    for (vy = vrows) if (ey0 + 10 < vy && vy < ey1 - 10)
        for (sx = [ex0 + 24 : 42 : ex1 - 46])
            translate([sx, vy, z0 - 0.1])
                cube([22, 2.6, fr_panel_t + 0.2]);
    if (PANEL == 4)                          // mic aperture over the Elite
        for (mx = [-2 : 2], my = [-2 : 2])
            translate([fr_mic[0] + 6*mx, fr_mic[1] + 6*my, z0 - 0.1])
                cylinder(h = fr_panel_t + 0.2, d = 2.5);
}
module louver_hoods() {
    difference() {
        for (vy = vrows) if (ey0 + 10 < vy && vy < ey1 - 10)
            for (sx = [ex0 + 24 : 42 : ex1 - 46])
                translate([sx + 11, vy, 0]) hood();
        keepout();
    }
}

module screws() {                            // countersunk M3 into supports
    for (q = fr_panel_scr[PANEL - 1]) translate([q[0], q[1], 0]) {
        translate([0, 0, z0 - 0.1]) cylinder(h = fr_panel_t + 0.2, d = 3.4);
        translate([0, 0, z1 - 1.4]) cylinder(h = 1.5, d1 = 3.4, d2 = 6.6);
    }
}

rotate([180, 0, 0]) translate([-ex0, -ey1, -z1]) difference() {
    union() {
        translate([ex0, ey0, z0]) cube([ex1 - ex0, ey1 - ey0, fr_panel_t]);
        difference() { ribs(); keepout(); }
        louver_hoods();
    }
    lap_cuts();
    louver_slits();
    screws();
}
