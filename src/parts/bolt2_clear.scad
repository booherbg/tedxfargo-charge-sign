// Integrated bolt v2 — CLEAR welded lens, baked V3 fuzzy top (filament 2).
// Needs fuzz_bolt.dat (tools/make_fuzz.py ... 1.5 0.8 7 0 0 134 294).
include <../config.scad>
include <../collar.scad>
include <../bolt.scad>
bolt_lens_integrated("fuzz_bolt.dat", 1.5);
