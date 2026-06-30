// Fit test: inner-lens lip clearance 0.0mm (5 dots). Lip == channel; with print
// tolerance this is the gentle end of a press fit.
include <../config.scad>
include <../collar.scad>
include <../bolt.scad>
lens_chunk(0.0, 5, label="0.0");
