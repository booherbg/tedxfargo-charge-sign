// Letter C tile — CLEAR welded lens, baked V3 fuzzy top (filament 3).
// Needs fuzz_C.dat (tools/make_fuzz.py ... 1.5 0.8 7 0 0 310 296).
include <../config.scad>
include <../collar.scad>
include <../letter.scad>
include <letter_C_data.scad>
letter_clear(C_paths, C_closed, C_bbox, "fuzz_C.dat", 1.5);
