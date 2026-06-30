// Fit test: inner-lens lip clearance 0.1mm (4 dots). Tightest -- likely a press
// fit once print tolerance is added (channel prints undersize, lip oversize).
include <../config.scad>
include <../collar.scad>
include <../bolt.scad>
lens_chunk(0.1, 4, label="0.1");
