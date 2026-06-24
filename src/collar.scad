// Calibrated press-fit collar, merged into the rear wall at each pixel.
// The STL is symmetric top/bottom (retention lip at mid-height), so insertion
// direction does not matter. Native STL sits X-centered at collar_cx, Z 0..collar_h.

module collar_solid() {
    translate([-collar_cx, 0, 0])
        import(collar_stl, convexity = 6);
}

module place_collar(x, y) {
    translate([x, y, 0]) collar_solid();
}
