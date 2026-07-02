// Web-view visuals. -D MODE: 1=full CHARGE outline, 2=C tube + Ø12 pixel (problem),
// 3=C tube WIDENED so pixel fits (faithful outline preserved?).
include <../config.scad>
S = 300/13.339;                     // scale imported art to 300mm cap height
module imp(f) scale([S,S]) import(f, center=true);
module pixels(pts) for (p=pts) translate([p[0]*S,p[1]*S,2]) {
    color([0.4,0.4,0.4,0.5]) linear_extrude(1.0) circle(d=16, $fn=40);   // collar
    color("red")             linear_extrude(1.6) circle(d=12, $fn=40);   // pixel Ø12
}
MODE = 1;
if (MODE == 1)
    color([0.3,0.82,0.86]) linear_extrude(2) imp("../../assets/svg/CHARGE.svg");
else if (MODE == 2) {
    color([0.3,0.82,0.86]) linear_extrude(2) imp("../../assets/svg/C.svg");
    pixels([[-6.8,0],[-4.7,4.3],[-4.7,-4.3]]);
} else {
    color([0.3,0.82,0.86]) linear_extrude(2) offset(r=3) imp("../../assets/svg/C.svg");  // +3mm/side
    pixels([[-6.8,0],[-4.7,4.3],[-4.7,-4.3]]);
}
