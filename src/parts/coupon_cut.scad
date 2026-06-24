// Preview only: coupon sectioned through the collar centerline.
include <../config.scad>
include <../collar.scad>
include <../diffuser.scad>
include <../coupon.scad>
difference() {
    coupon_body();
    translate([-1, cell_pitch / 2, -5])
        cube([plate_w + 2, cell_pitch, 300]);
}
