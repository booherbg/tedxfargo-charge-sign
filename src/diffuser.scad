// Swappable diffuser panel. Thickness is the STL knob; the diffusing structure
// (gyroid/grid, density, top/bottom solid layers = 0) is set in the slicer.

module diffuser_panel(t) {
    linear_extrude(t) square([panel_side, panel_side], center = true);
}

// Diffuser LID = flanged plug. The plug drops INTO the opening (locates it, light
// grip so it won't slide); the flange overhangs by ~the wall width and rests on
// the rim so it can't fall through. Lifts straight off for swapping, and works on
// touching chimneys (the plug uses the open hole, not the side walls). The flange
// is the diffuser face (thickness t). Set lid_plug_h = 0 for a plain flat tile.
// Modeled diffuser-face-down (z=0..t) = print orientation; flip in use.
module diffuser_lid(t) {
    fside = cell_inner + 2 * lid_flange_cover - lid_flange_gap;  // flange (rests on the rim)
    pside = cell_inner - lid_plug_clear;                          // plug (drops into the opening)
    union() {
        linear_extrude(t) square([fside, fside], center = true); // flange / diffuser face
        if (lid_plug_h > 0)
            translate([0, 0, t])
                linear_extrude(lid_plug_h)
                    difference() {
                        square([pside, pside], center = true);
                        square([pside - 2 * lid_plug_wall, pside - 2 * lid_plug_wall], center = true);
                    }
    }
}

// Slide-over diffuser CAP: a diffuser top + a skirt that slides over the OUTSIDE
// of a chimney. Only works on an ISOLATED column (needs side clearance for the
// skirt) — kept for possible use on the real letters, NOT the touching coupon.
// Modeled diffuser-face-down (z=0..t) = print orientation.
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
