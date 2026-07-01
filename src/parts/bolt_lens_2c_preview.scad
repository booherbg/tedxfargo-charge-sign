// Visual QA (NOT for print): white (opaque) + clear (translucent) for a variation.
// -D V=1 (white center stripe) or -D V=2 (white edges).
include <../config.scad>
include <../collar.scad>
include <../bolt.scad>
V = 1;
color("white")           { if (V==1) bolt_lens_v1_white(); else bolt_lens_v2_white(); }
color([0.55,0.8,1,0.35]) { if (V==1) bolt_lens_v1_clear(); else bolt_lens_v2_clear(); }
