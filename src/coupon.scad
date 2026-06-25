// Stackup test coupon: one shared rear plate (on the bed) + N chimneys of
// different heights (the depth ladder). Every face is on the bed or an open
// top, so it prints support-free. Collars are merged into the plate.

module one_chimney(i, j) {
    H = chimney_H(i);
    // plain open box; the diffuser lid sits on top of the cell_inner opening
    translate([cell_x(i), cell_y(j), 0])
        difference() {
            translate([0, 0, plate_t])
                linear_extrude(H - plate_t)
                    square([cell_pitch, cell_pitch], center = true);
            translate([0, 0, plate_t - 0.01])
                linear_extrude(H - plate_t + 0.02)
                    square([cell_inner, cell_inner], center = true);
        }
}

// rows = number of identical depth-ladder rows (1 = original coupon, 3 = 3x3 grid)
module coupon_body(rows = 1) {
    difference() {
        union() {
            linear_extrude(plate_t) square([plate_w, rows * cell_pitch]);
            for (j = [0 : rows - 1], i = [0 : n_cells - 1]) one_chimney(i, j);
        }
        // pixel clearance holes through the plate
        for (j = [0 : rows - 1], i = [0 : n_cells - 1])
            translate([cell_x(i), cell_y(j), -0.1])
                cylinder(h = plate_t + 0.2, d = pixel_through);
    }
    // merge the calibrated collars (added after the difference so the bore survives)
    for (j = [0 : rows - 1], i = [0 : n_cells - 1])
        place_collar(cell_x(i), cell_y(j));
}
