// Visual QA (NOT for print): white shell + translucent clear lens.
include <../config.scad>
include <../collar.scad>
include <../testbox.scad>
color([0.85,0.85,0.85]) testbox_white();
color([0.55,0.8,1.0,0.35]) testbox_clear();
