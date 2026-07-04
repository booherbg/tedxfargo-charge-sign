// Assembled preview of the INTEGRATED bolt (new style): white shell + welded fuzzy lens.
// Preview/render only — print from bolt2_white + bolt2_clear via the 3MF.
include <../config.scad>
include <../collar.scad>
include <../bolt.scad>
color("white") bolt_shell();
color("#bfdfff") bolt_lens_integrated("fuzz_bolt.dat", 1.5);
