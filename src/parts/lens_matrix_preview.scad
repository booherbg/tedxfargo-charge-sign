// Visual-QA preview only (NOT for printing): white body + translucent clear optic
// in one model so the two-material assembly can be eyeballed.
include <../config.scad>
include <../collar.scad>
include <../lens_cell.scad>
color("white") matrix_white();
color([0.6,0.8,1.0,0.35]) matrix_clear();
