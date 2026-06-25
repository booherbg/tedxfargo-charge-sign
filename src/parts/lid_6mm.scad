// Build target: 6mm flanged-plug lid — thick enough for a real infill core.
// Slice with 1 bottom layer (smooth spiral viewer face), 0 top layers (open to
// the LED so light enters the gyroid), ~50% gyroid.
include <../config.scad>
include <../diffuser.scad>
diffuser_lid(6);
