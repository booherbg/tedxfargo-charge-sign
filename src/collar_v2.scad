// Collar v2: the calibrated original with a 45-deg lead-in chamfer cut into both
// faces. Eases the press start and self-centers the barrel. The retention lip
// (mid-height) is untouched, so the grip is identical to the original — the
// chamfer is the only change. Subtractive on collar_solid(), so the calibrated
// STL stays the source of truth.

module collar_v2_solid() {
    eps = 0.05;
    difference() {
        collar_solid();
        // bottom-face lead-in (mouth at z=0, blends to bore at z=chamfer_depth)
        translate([0, 0, -eps])
            cylinder(h = chamfer_depth + eps, r1 = mouth_r + eps, r2 = bore_face_r);
        // top-face lead-in (mouth at z=collar_h)
        translate([0, 0, collar_h - chamfer_depth])
            cylinder(h = chamfer_depth + eps, r1 = bore_face_r, r2 = mouth_r + eps);
    }
}

module place_collar_v2(x, y) {
    translate([x, y, 0]) collar_v2_solid();
}
