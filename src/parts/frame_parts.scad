// Backer-frame small parts (spec 2026-07-21). WHITE PETG.
//   openscad -D PART=<n> [-D GLAND=<7|9|11>] [-D SEG=<1..4>] -o out.stl \
//       src/parts/frame_parts.scad
//   PART: 1=handle(x2) 2=foot(x2) 3=leg(x3) 4=gland plate 5=dovetail key(x4)
//         6=trim strip (per SEG, x4) 7=tray-pattern coupon (print FIRST)
include <frame_layout.scad>

PART = 1;
GLAND = 9;
SEG = 1;

module rrect(w, h, r) offset(r = r) offset(delta = -r)
    square([w, h], center = true);

// ---- 1: carry/hang handle — bolts M4 at 80 apart, back face flush ----
module handle() {
    difference() {
        linear_extrude(15) rrect(120, 44, 8);           // z = thickness (15)
        translate([0, 4, -0.1]) linear_extrude(15.2) rrect(96, 24, 7);
        for (s = [-1, 1]) translate([s * 40, -16, 0]) {
            translate([0, 0, -0.1]) cylinder(h = 15.4, d = 4.5);
        }
    }
}
// bolt holes run through the 12 mm base (y -22..-10); heads sit in the grip:
// drilled above as plain Ø4.5 through z — the M4 self-taps the rail pad, the
// head + washer bear on the handle base inside the grip opening.

// ---- 2: snap-in foot — arrowhead tab, blade 90 fore-aft ----
module foot() {
    translate([-12, -45, 0]) cube([24, 90, 6]);         // blade on the floor
    translate([-7, -1.5, 5.9]) cube([14, 3, 12.1]);     // tab riser
    difference() {
        union() {
            translate([-7, -1.5, 12]) cube([14, 3, 6]);
            for (s = [-1, 1])                            // barbs at the tips
                translate([s * 7, -1.5, 15]) scale([1, 1, 1]) hull() {
                    translate([s * -0.1, 0, 0]) cube([0.2, 3, 3]);
                    translate([s * 1.6, 0, 2.9]) cube([0.2, 3, 0.1]);
                }
        }
        translate([-1, -2, 10]) cube([2, 4, 8.2]);      // spring slit
    }
}

// ---- 3: leg for the S1/S2 sockets ----
module leg() {
    cylinder(h = 13, d = 10.0);                          // socket pin
    translate([0, 0, 13]) cylinder(h = 2, d = 14);       // shoulder on boss
    translate([0, 0, 15]) difference() {
        cylinder(h = fr_cavity - 15, d = 10);            // column to panel
        translate([0, 0, fr_cavity - 22.9]) cylinder(h = 8, d = 2.8);
    }
}

// ---- 4: gland plate (2.5 thick = PG clamp-safe seat) ----
gd = GLAND == 7 ? 12.5 : GLAND == 11 ? 18.6 : 15.2;
module gland_plate() difference() {
    linear_extrude(2.5) rrect(45, 30, 3);
    translate([0, 0, -0.1]) cylinder(h = 2.7, d = gd);
    for (s = [-1, 1]) translate([s * 20, 0, -0.1]) cylinder(h = 2.7, d = 3.4);
}

// ---- 5: dovetail key (KEEP IN SYNC with frame.scad bowtie) ----
module bowtie(cl = 0) {
    hull() { translate([-12 - cl, -7 - cl]) square([3 + cl, 14 + 2*cl]);
             translate([-1.5, -4 - cl]) square([3, 8 + 2*cl]); }
    hull() { translate([9, -7 - cl]) square([3 + cl, 14 + 2*cl]);
             translate([-1.5, -4 - cl]) square([3, 8 + 2*cl]); }
}
module key() difference() {
    linear_extrude(4) bowtie(0);
    for (s = [-1, 1]) translate([s * 8, 0, -0.1]) cylinder(h = 4.2, d = 2.4);
}

// ---- 6: snap-on trim strip (corner-L, per SEG like frame.scad) ----
ox0 = -fr_clr - fr_wall;  ox1 = fr_face[0] + fr_clr + fr_wall;
oy0 = -fr_clr - fr_wall;  oy1 = fr_face[1] + fr_clr + fr_wall;
module toring(grow, w) difference() {     // band outside->inboard, grown out
    translate([ox0 - grow, oy0 - grow])
        square([ox1 - ox0 + 2*grow, oy1 - oy0 + 2*grow]);
    translate([ox0 + w, oy0 + w])
        square([ox1 - ox0 - 2*w, oy1 - oy0 - 2*w]);
}
module trim_body() {
    // face leg: covers wall edge + clearance + 2 mm reveal onto the plate
    translate([0, 0, -3.6]) linear_extrude(1.6)
        toring(1.6, fr_wall + fr_clr + fr_reveal);
    // skirt down the outer face with an inward snap bead into the groove
    translate([0, 0, -3.6]) linear_extrude(11.6) toring(1.6, 0.01);
    translate([0, 0, 5.7]) linear_extrude(1.6) toring(0.01, 0.7);
}
clipx = [[ox0 - 2, fr_joint[0]], [fr_joint[0], ox1 + 2],
         [fr_joint[0], ox1 + 2], [ox0 - 2, fr_joint[0]]][SEG - 1];
clipy = [[oy0 - 2, fr_joint[1]], [oy0 - 2, fr_joint[1]],
         [fr_joint[1], oy1 + 2], [fr_joint[1], oy1 + 2]][SEG - 1];
module trim() rotate([180, 0, 0])          // face-leg down for printing
    translate([-clipx[0], -clipy[0], 0]) intersection() {
        trim_body();
        translate([clipx[0], clipy[0], -5])
            cube([clipx[1] - clipx[0], clipy[1] - clipy[0], 20]);
    }

// ---- 7: chirality coupon — verify BEFORE printing rails ----
// PSU pattern relative to the engraved case corner; Elite diagonals A and B
// from the marked center. Offer up to the physical units; whichever Elite
// diagonal matches sets ctl_diag in tools/boltframe.py.
module coupon() difference() {
    linear_extrude(1.2) translate([-5, -5]) square([110, 150]);
    // PSU: slots (LRS-50/75) + rounds (LRS-100), case corner at (0,0)
    for (l = [20.5, 75.5]) translate([0, 0, -0.1]) linear_extrude(1.4) hull() {
        translate([40.5, l]) circle(d = 3.2);
        translate([45.5, l]) circle(d = 3.2);
    }
    for (w = [34, 67]) translate([w, 78, -0.1]) cylinder(h = 1.4, d = 3.2);
    translate([0, 0, 0.6]) linear_extrude(0.7) {        // case edge engraves
        square([97, 0.8]); square([0.8, 129]);
        translate([81.6, 0]) square([0.8, 99]);          // LRS-50 width line
    }
    // Elite diagonals about center (48.5, 64.5): A = probed, B = mirror
    for (dm = [[1, "A", 10], [-1, "B", -22]]) {
        for (s = [-1, 1])
            translate([48.5 + s * 13 * dm[0], 64.5 + s * 61, -0.1])
                cylinder(h = 1.4, d = 4.6);
        translate([48.5 + dm[2], 64.5, 0.6]) linear_extrude(0.7)
            text(dm[1], size = 8, halign = "center", valign = "center");
    }
}

if (PART == 1) handle();
else if (PART == 2) foot();
else if (PART == 3) leg();
else if (PART == 4) gland_plate();
else if (PART == 5) key();
else if (PART == 6) trim();
else if (PART == 7) coupon();
