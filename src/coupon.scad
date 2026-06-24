// Stackup test coupon: one shared rear plate (on the bed) + N chimneys of
// different heights (the depth ladder). Every face is on the bed or an open
// top, so it prints support-free. Collars are merged into the plate.

module one_chimney(i) {
    H  = chimney_H(i);
    cx = cell_x(i);
    translate([cx, cell_pitch / 2, 0]) {
        // four walls
        difference() {
            translate([0, 0, plate_t])
                linear_extrude(H - plate_t)
                    square([cell_pitch, cell_pitch], center = true);
            translate([0, 0, plate_t - 0.01])
                linear_extrude(H - plate_t + 0.02)
                    square([cell_inner, cell_inner], center = true);
        }
        // outer locating lip (panel rests on the seat, captured by this lip)
        translate([0, 0, H])
            linear_extrude(lip_h)
                difference() {
                    square([cell_pitch, cell_pitch], center = true);
                    square([cell_pitch - 2 * lip_t, cell_pitch - 2 * lip_t], center = true);
                }
    }
}

module coupon_body() {
    difference() {
        union() {
            linear_extrude(plate_t) square([plate_w, plate_d]);
            for (i = [0 : n_cells - 1]) one_chimney(i);
        }
        // pixel clearance holes through the plate
        for (i = [0 : n_cells - 1])
            translate([cell_x(i), cell_pitch / 2, -0.1])
                cylinder(h = plate_t + 0.2, d = pixel_through);
    }
    // merge the calibrated collars (added after the difference so the bore survives)
    for (i = [0 : n_cells - 1])
        place_collar(cell_x(i), cell_pitch / 2);
}
