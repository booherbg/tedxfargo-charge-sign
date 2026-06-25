// Swappable diffuser panel. Thickness is the STL knob; the diffusing structure
// (gyroid/grid, density, top/bottom solid layers = 0) is set in the slicer.

module diffuser_panel(t) {
    linear_extrude(t) square([panel_side, panel_side], center = true);
}

// Slide-over diffuser CAP: a diffuser top + a skirt that slides over the OUTSIDE
// of a chimney. Easy on/off, and one cap fits any chimney (same outer size).
// Modeled diffuser-face-down (z=0..t) = print orientation (smooth side on bed);
// flip it in use so the smooth face points at the viewer and the skirt hangs down.
module diffuser_cap(t) {
    si = cell_pitch + cap_fit_clear;      // skirt inner — slides over the chimney outer
    so = si + 2 * cap_skirt_t;            // skirt outer
    union() {
        linear_extrude(t) square([so, so], center = true);          // diffuser face
        translate([0, 0, t])
            linear_extrude(cap_skirt_h)                             // skirt
                difference() {
                    square([so, so], center = true);
                    square([si, si], center = true);
                }
    }
}
