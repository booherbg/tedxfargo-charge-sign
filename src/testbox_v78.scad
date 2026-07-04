// Fuzz bake-off extras: V7 uniform pyramids / V8 jittered / V9 disco (big+steep).
// pyramid-mode dats are sampled at CELL/4 -> fuzzy_lens scale = CELL/4:
//   V7/V8: cell 2.0 -> 0.5     V9: cell 3.5 -> 0.875
//   openscad -D V=7|8|9 -D COL=1|2  (COL 1 = white body w/ label, 2 = clear lens)
include <testbox.scad>
V   = 7;
COL = 1;
tb_fscale = V == 9 ? 0.875 : 0.5;
if (COL == 1) testbox_white(str("V", V));
else fuzzy_lens(str("fuzz_v", V, ".dat"), tb_fscale);
