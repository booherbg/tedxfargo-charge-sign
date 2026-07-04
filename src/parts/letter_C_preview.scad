// Assembled 3-color preview of the letter C tile. Render/preview only —
// print from the letter_C_{black,white,clear} STLs via the 3-color 3MF.
include <../config.scad>
include <../collar.scad>
include <../letter.scad>
include <letter_C_data.scad>
color([0.15, 0.15, 0.15]) letter_black(C_paths, C_closed, C_pixels, C_bbox, "C");
color("white")            letter_white(C_paths, C_closed, C_pixels, C_bbox);
color("#bfdfff")          letter_clear(C_paths, C_closed, C_bbox, "fuzz_C.dat", 1.5);
