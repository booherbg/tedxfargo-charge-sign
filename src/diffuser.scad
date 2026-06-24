// Swappable diffuser panel. Thickness is the STL knob; the diffusing structure
// (gyroid/grid, density, top/bottom solid layers = 0) is set in the slicer.

module diffuser_panel(t) {
    linear_extrude(t) square([panel_side, panel_side], center = true);
}
