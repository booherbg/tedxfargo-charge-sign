// Visual QA (NOT for printing): matrix sectioned through a row with red pixel
// proxies in place, to eyeball that the pixel clears the interior optics.
// Set ROW=0 (A-row masks) or ROW=1 (R/B/C fills+cones).
include <../config.scad>
include <../collar.scad>
include <../lens_cell.scad>
ROW = 1;
cy  = ROW * lc_pitch;
module pixel_proxy() {
    color([1,0,0,0.85]) {
        translate([0,0,plate_t]) cylinder(h=0.8, d=12, $fn=48);
        translate([0,0,plate_t+0.8]) cylinder(h=3.2, d1=8, d2=1.2, $fn=48);
    }
}
difference() {
    union() {
        color([0.82,0.82,0.82]) matrix_white();
        color([0.6,0.8,1.0,0.35]) matrix_clear();
    }
    translate([-300, cy-300, -50]) cube([600,300,300]);   // expose y=cy section
}
for (i=[0:lc_cols-1]) translate([i*lc_pitch, cy, 0]) pixel_proxy();
