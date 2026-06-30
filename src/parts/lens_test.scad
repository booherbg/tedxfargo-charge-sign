// SINGLE-FILE, SINGLE-MATERIAL diffuser test. Just print this one STL in
// CLEAR/natural PETG (gyroid infill ~15%, 1-2 top layers). Insert a pixel from
// the back of each cell and light it. 3 cells: AIR (cavity+thin face),
// FILL (volumetric gyroid), CONE (center beam-spreader).
include <../config.scad>
include <../collar.scad>
include <../lens_cell.scad>
lens_test_strip();
