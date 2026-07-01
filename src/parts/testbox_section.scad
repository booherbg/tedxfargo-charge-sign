// Visual QA (NOT for print): lengthwise cut through the channel centerline.
include <../config.scad>
include <../collar.scad>
include <../testbox.scad>
difference() {
    union() {
        color([0.85,0.85,0.85]) testbox_white();
        color([0.55,0.8,1.0,0.4]) testbox_clear();
    }
    translate([-50,0,-50]) cube([250,120,120]);  // remove y>0 -> expose the y=0 section
}
