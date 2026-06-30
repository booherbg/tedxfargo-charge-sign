// ===== Integrated lit-cell test matrix =====
// Single-print, dual-material (white body + clear optic) diffuser cells to find
// the best "even, sourceless glow" recipe -- the optical coupon for the eventual
// TEDxFargo letter strokes. The winning cross-section (depth/mask/material split)
// transfers to the letterforms later.
//
// PRINT PLATE-DOWN (collar on the bed, optic on top): no flip, no chirality
// issue; the pixel inserts from the back after printing. Co-printed two-material:
//   WHITE  = body (plate + walls + masks/reflectors)   -> filament/nozzle 1
//   CLEAR  = optic (face / fill / puck)                 -> filament/nozzle 2
// Export two co-registered STLs (same origin): matrix_white + matrix_clear, load
// both in Bambu Studio, assign materials, print as one job.
//
// Families (research-tuned, see 2026-06-29 spec for sources):
//   A  masked reflector cavity  (white walls + PERFORATED hotspot dot + clear face)
//   R  reflector cone           (white volcano around LED + clear face)
//   B  volumetric scatter       (clear fill; slice this cell with ~15% GYROID infill)
//   C  TIR puck                 (solid clear + center cone refractor)

include <config.scad>
include <collar.scad>

// ---- cell shell geometry ----
lc_inner = cell_inner;            // 30mm interior square (reuse config)
lc_wall  = 2.0;                   // white wall thickness
lc_outer = lc_inner + 2*lc_wall;  // 34mm outer
lc_pitch = lc_outer + 6;          // 40mm grid spacing (6mm gap between cells)
lc_fuse  = 0.1;                   // white/clear overlap so the slicer fuses them
led_void = 13.0;                  // keep-out diameter for the LED dome (>12mm)

// wall height above the plate for a chosen LED-tip -> face gap
function lc_wall_h(gap) = dome_clear + gap;

// ===== test matrix =====  [code, type, gap, p1, p2]
//   A: p1 = mask diameter (0 = none), p2 = mask standoff (mm above the dome tip)
//   R / B: no extra params
//   C: p1 = cone included-angle (deg)
lc_cells = [
    ["A0", "A", 15,  0,  0],   // 1: baseline, no mask (expect a center hotspot)
    ["A1", "A", 15, 14,  5],   // 2: perforated dot d14, 5mm above dome
    ["A2", "A", 15, 16,  5],   // 3: perforated dot d16 (more "white around bulb")
    ["A3", "A", 18, 14,  6],   // 4: deeper cavity + dot
    ["R1", "R", 15,  0,  0],   // 5: reflector cone (volcano), no mask
    ["B1", "B", 15,  0,  0],   // 6: clear fill  -> slice with 15% gyroid infill
    ["C1", "C", 15, 90,  0],   // 7: TIR puck, 90deg cone
    ["C2", "C", 15, 60,  0],   // 8: TIR puck, 60deg cone (steeper, more sideways)
];
lc_cols = 4;

function lc_pos(idx) = [ (idx % lc_cols) * lc_pitch, floor(idx / lc_cols) * lc_pitch ];

// ---------------- WHITE body ----------------
module lc_walls(gap) {
    translate([0,0,plate_t])
        linear_extrude(lc_wall_h(gap))
            difference() { square(lc_outer, center=true); square(lc_inner, center=true); }
}

// approach-A: a PERFORATED white dot on 3 legs, floated close to the LED. The
// perforations make it semi-transparent (soft penumbra, no hard dark disc) while
// the white struts reflect/recycle the central peak. Self-supporting: legs are
// vertical, and the perforated disc bridges only ~1.7mm hole-to-hole.
module lc_mask(gap, mask_d, stand_mm) {
    if (mask_d > 0) {
        mt = 1.5;                                      // disc thickness
        zb = plate_t + dome_clear + stand_mm;          // disc bottom height
        rl = max(mask_d/2 - 0.8, 7.0);                 // leg radius (>=7 clears the dome)
        difference() {
            translate([0,0,zb]) cylinder(h=mt, d=mask_d);
            for (x=[-mask_d/2:2.6:mask_d/2], y=[-mask_d/2:2.6:mask_d/2])  // ~43% open
                translate([x,y,zb-0.1]) cylinder(h=mt+0.2, d=1.7, $fn=12);
        }
        for (a=[0:120:359])
            rotate(a) translate([rl,0,plate_t]) cylinder(h=zb-plate_t+0.01, d=1.8);
    }
}

// approach-R: a white "volcano" around the LED, open top, walls narrowing upward
// (self-supporting), throwing side light out to the cavity walls.
module lc_reflector(gap) {
    h = min(lc_wall_h(gap)-1, dome_clear + gap*0.6);
    translate([0,0,plate_t])
        difference() {
            cylinder(h=h, d1=led_void+6, d2=led_void+1);
            translate([0,0,-0.1]) cylinder(h=h+0.2, d1=led_void+2.5, d2=led_void-2.5);
        }
}

module lc_body_optic(spec) {
    type = spec[1]; gap = spec[2];
    if (type == "A") lc_mask(gap, spec[3], spec[4]);
    if (type == "R") lc_reflector(gap);
}

// ---------------- CLEAR optic ----------------
module lc_face(gap, face_t) {     // clear top, overlapping wall tops for a fused seam
    translate([0,0,plate_t+lc_wall_h(gap)-lc_fuse])
        linear_extrude(face_t+lc_fuse) square(lc_inner+lc_wall, center=true);
}

module lc_fill(gap) {             // B: solid clear fill (slice with ~15% gyroid infill)
    wh = lc_wall_h(gap);
    difference() {
        translate([0,0,plate_t]) linear_extrude(wh) square(lc_inner+2*lc_fuse, center=true);
        translate([0,0,plate_t-0.1]) cylinder(h=dome_clear+0.1, d=led_void);
    }
    lc_face(gap, 1.0);
}

module lc_puck(gap, cone_ang) {   // C: solid clear + center cone refractor (TIR)
    wh = lc_wall_h(gap);
    cone_r = led_void/2 + 1;
    cone_h = cone_r / tan(cone_ang/2);
    difference() {
        translate([0,0,plate_t]) linear_extrude(wh) square(lc_inner+2*lc_fuse, center=true);
        union() {
            translate([0,0,plate_t-0.1]) cylinder(h=dome_clear+0.1, d=led_void);
            translate([0,0,plate_t+dome_clear-0.01]) cylinder(h=cone_h, r1=cone_r, r2=0.2);
        }
    }
    lc_face(gap, 1.2);
}

module lc_clear_optic(spec) {
    type = spec[1]; gap = spec[2];
    if (type == "A" || type == "R") lc_face(gap, 1.2);
    if (type == "B") lc_fill(gap);
    if (type == "C") lc_puck(gap, spec[3]);
}

// ---------------- matrix assembly ----------------
module lc_label(idx) {            // (idx+1) debossed dots on the plate bottom, front-left
    n = idx + 1;
    for (k=[0:n-1])
        translate([-lc_outer/2+5+k*3, -lc_outer/2+4, -0.1]) cylinder(h=0.9, d=1.8, $fn=16);
}

module matrix_white() {
    rows = ceil(len(lc_cells)/lc_cols);
    difference() {
        union() {
            // one base slab tying all cells into a handleable tray
            translate([-lc_outer/2, -lc_outer/2, 0])
                linear_extrude(plate_t)
                    square([(lc_cols-1)*lc_pitch + lc_outer, (rows-1)*lc_pitch + lc_outer]);
            for (idx=[0:len(lc_cells)-1]) {
                p = lc_pos(idx);
                translate([p[0],p[1],0]) { lc_walls(lc_cells[idx][2]); lc_body_optic(lc_cells[idx]); }
            }
        }
        for (idx=[0:len(lc_cells)-1]) {
            p = lc_pos(idx);
            translate([p[0],p[1],0]) {
                translate([0,0,-0.1]) cylinder(h=plate_t+0.2, d=pixel_through);
                lc_label(idx);
            }
        }
    }
    for (idx=[0:len(lc_cells)-1]) { p = lc_pos(idx); place_collar(p[0], p[1]); }
}

module matrix_clear() {
    for (idx=[0:len(lc_cells)-1]) {
        p = lc_pos(idx);
        translate([p[0],p[1],0]) lc_clear_optic(lc_cells[idx]);
    }
}

// ================== SINGLE-MATERIAL "just print it" test ==================
// One STL, one filament (print in CLEAR/natural PETG, gyroid infill ~15%, 1-2
// top layers). Drops the white-reflector + perforated mask (those need a 2nd
// nozzle); tests the core diffusion: open-cavity face vs volumetric fill vs cone.
// Connected strip on a shared base; debossed labels on the bottom.
solo_cells = [
    ["AIR",  15, "air"],    // air cavity + thin clear diffuser face (closest to your coupon)
    ["FILL", 15, "fill"],   // clear solid -> gyroid infill = volumetric diffuser
    ["CONE", 15, "cone"],   // clear + center cone spreads the beam sideways
];

module lens_solo(gap, kind) {
    union() {
        difference() {
            union() {
                linear_extrude(plate_t) square(lc_outer, center=true);
                lc_walls(gap);
            }
            translate([0,0,-0.1]) cylinder(h=plate_t+0.2, d=pixel_through);
        }
        place_collar(0, 0);
        if (kind == "air")  lc_face(gap, 1.2);
        if (kind == "fill") lc_fill(gap);
        if (kind == "cone") lc_puck(gap, 90);
    }
}

module lens_test_strip() {
    n = len(solo_cells);
    difference() {
        union() {
            // shared base ties the strip into one handleable piece
            translate([-lc_outer/2, -lc_outer/2, 0])
                linear_extrude(plate_t) square([(n-1)*lc_pitch + lc_outer, lc_outer]);
            for (i=[0:n-1])
                translate([i*lc_pitch,0,0]) lens_solo(solo_cells[i][1], solo_cells[i][2]);
        }
        for (i=[0:n-1])
            translate([i*lc_pitch, -lc_outer/2+4, -0.1]) linear_extrude(0.9)
                mirror([1,0,0]) text(solo_cells[i][0], size=3.5, halign="center", valign="center");
    }
}
