// Visual-QA cross-section (NOT for printing). Set ROW=0 to cut the A row through
// the cell centers (y=0); ROW=1 to cut the back row (R/B/C) at y=lc_pitch.
include <../config.scad>
include <../collar.scad>
include <../lens_cell.scad>
ROW = 0;
cy  = ROW * lc_pitch;
difference() {
    union() {
        color("white") matrix_white();
        color([0.6,0.8,1.0,0.4]) matrix_clear();
    }
    translate([-200, cy-200, -50]) cube([400,200,200]);  // expose y=cy section
}
