// Fuzz bake-off extras: V7 uniform pyramid facets / V8 jittered pyramids
// (user idea 2026-07-05: "uniform but scattered" deterministic texture).
// dats sampled at CELL/4 = 0.5mm -> fuzzy_lens scale 0.5.
//   openscad -D V=7 -D COL=1|2  (COL 1 = white body w/ label, 2 = clear faceted lens)
include <testbox.scad>
V   = 7;
COL = 1;
if (COL == 1) testbox_white(str("V", V));
else fuzzy_lens(str("fuzz_v", V, ".dat"), 0.5);
