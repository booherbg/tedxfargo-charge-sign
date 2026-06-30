// Fit test: inner-lens lip clearance -0.1mm (6 dots). NEGATIVE = interference:
// lip is 0.1mm WIDER than the channel -> presses/snaps in.
include <../config.scad>
include <../collar.scad>
include <../bolt.scad>
lens_chunk(-0.1, 6, label="-0.1");
