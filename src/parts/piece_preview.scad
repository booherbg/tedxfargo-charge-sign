// Assembled 3-color preview of one billboard piece (render/eyeball only).
//   openscad -D PIECE=<1..6> --viewall -o piece_preview.png src/parts/piece_preview.scad
include <../config.scad>
include <../collar.scad>
include <word_layout.scad>

PIECE = 1;
COL   = 0;   // unused here; piece.scad's modules are re-included via its file

// re-use piece.scad by inclusion would double-declare params; simplest: mirror the
// three bodies via children of one include using COL switching is overkill for a
// preview — render the three exported STLs instead if they exist, else nothing.
color([0.16,0.16,0.16]) import(str("../../stl/piece", PIECE, "_black.stl"));
color("white")          import(str("../../stl/piece", PIECE, "_white.stl"));
color("#bfdfff")        import(str("../../stl/piece", PIECE, "_clear.stl"));
