// Collar A/B test tile: original collar (1 dot) vs chamfered v2 (2 dots) in one
// flat square. Press a pixel into each and compare insertion + retention.
// Prints flat, collars on the bed, support-free.

module _dots(n) {
    for (i = [0 : n - 1])
        translate([i * 3.2, 0, harness_t - 0.4])
            cylinder(h = 0.6, d = 1.6);
}

module collar_harness() {
    difference() {
        translate([-harness_w / 2, -harness_d / 2, 0])
            cube([harness_w, harness_d, harness_t]);
        // pixel clearance holes
        translate([-harness_pitch / 2, 0, -0.1]) cylinder(h = harness_t + 0.2, d = pixel_through);
        translate([ harness_pitch / 2, 0, -0.1]) cylinder(h = harness_t + 0.2, d = pixel_through);
        // ID dots, debossed: 1 = original (left), 2 = chamfered v2 (right)
        translate([-harness_pitch / 2,       -harness_d / 2 + 4, 0]) _dots(1);
        translate([ harness_pitch / 2 - 1.6, -harness_d / 2 + 4, 0]) _dots(2);
    }
    place_collar(   -harness_pitch / 2, 0);  // original calibrated collar
    place_collar_v2( harness_pitch / 2, 0);  // v2 with lead-in chamfer
}
