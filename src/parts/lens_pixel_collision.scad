// QA only: intersect an oversized pixel envelope (ABOVE the plate, skipping the
// intended collar press-fit) with every cell. If the result is EMPTY, all pixels
// clear the interior optics. barrel O12.4, dome O8.4 -> tip ~z=6.4.
include <../config.scad>
include <../collar.scad>
include <../lens_cell.scad>

module pixel_env() {
    translate([0,0,plate_t+0.001]) cylinder(h=0.8, d=12.4, $fn=48);
    translate([0,0,plate_t+0.8])   cylinder(h=3.6, d1=8.4, d2=1.0, $fn=48);
}
intersection() {
    union() { matrix_white(); matrix_clear(); }
    union() { for (idx=[0:len(lc_cells)-1]) translate([lc_pos(idx)[0], lc_pos(idx)[1], 0]) pixel_env(); }
}
