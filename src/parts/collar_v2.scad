// Build target: the v2 collar (lead-in chamfer) as a standalone STL, centered
// at origin with the bore along Z, z = 0..collar_h. Drop-in for merging later.
include <../config.scad>
include <../collar.scad>
include <../collar_v2.scad>
collar_v2_solid();
