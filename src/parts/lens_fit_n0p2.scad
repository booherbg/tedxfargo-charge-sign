// Fit test: inner-lens lip clearance -0.2mm (7 dots). 0.2mm interference -- the
// firm/snap end. If even this drops out, the channel is printing oversize and the
// right fix is crush ribs (consistent grip) rather than more rungs.
include <../config.scad>
include <../collar.scad>
include <../bolt.scad>
lens_chunk(-0.2, 7, label="-0.2");
