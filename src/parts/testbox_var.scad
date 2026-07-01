// Parametric entry for the 4 fuzzy-texture variations (fine -> chunky). Build with:
//   openscad -D VAR=<1..4> -D 'PART="white"' (or 'PART="clear"') -o out.stl testbox_var.scad
// Needs fuzz_v1..v4.dat in this dir (tools/make_fuzz.py). Pair white+clear -> 3MF.
include <../config.scad>
include <../collar.scad>
include <../testbox.scad>
VAR  = 1;
PART = "white";
// [cell size (mm), dat file, label]
tb_vars = [ [0.6, "fuzz_v1.dat", "1"],
            [1.0, "fuzz_v2.dat", "2"],
            [1.5, "fuzz_v3.dat", "3"],
            [2.2, "fuzz_v4.dat", "4"] ];
v = tb_vars[VAR-1];
if (PART == "white") testbox_white(v[2]);
else                 fuzzy_lens(v[1], v[0]);
