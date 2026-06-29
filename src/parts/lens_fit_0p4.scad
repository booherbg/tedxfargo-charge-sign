// Fit test: inner-lens lip clearance 0.4mm (1 dot). Loosest of the four
// (still tighter than the current bolt_lip_clear=0.6). Press lip into a straight
// run of the printed channel to feel the fit.
include <../config.scad>
include <../collar.scad>
include <../bolt.scad>
lens_chunk(0.4, 1);
