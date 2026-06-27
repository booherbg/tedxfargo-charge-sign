// Build target: snap-over bolt lens (wraps the whole bolt). Print top-face-down,
// skirt up; flip in use. One filament to start; or clear top + white skirt via a
// slicer height color-change at z = cap_top_t.
include <../config.scad>
include <../collar.scad>
include <../bolt.scad>
bolt_overcap();
