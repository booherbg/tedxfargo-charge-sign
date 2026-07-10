// Pixel pusher: seats a bullet pixel through a strap pass-hole or flange
// pocket (fingers don't fit Ø17/Ø14.5). Ring face bears on the flange rim
// around the wire exit; side slot lets the wires escape. Print upright.
$fn = 72;
difference() {
    cylinder(h = 60, d = 14.0);
    translate([0, 0, -0.1]) cylinder(h = 60.2, d = 9.0);
    translate([-2.5, -7.5, -0.1]) cube([5, 7.5, 60.2]);   // wire slot
}
