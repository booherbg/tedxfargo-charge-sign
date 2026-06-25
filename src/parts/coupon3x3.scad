// Build target: 3x3 grid coupon — 3 depth-ladder rows mounted together.
// 9 wells = 3 distances (20/35/50) x 3 rows, so you can light a full matrix of
// lens combinations at once. ~105 x 105mm, support-free.
include <../config.scad>
include <../collar.scad>
include <../coupon.scad>
coupon_body(3);
