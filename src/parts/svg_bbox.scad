// Measure a letter SVG footprint. -D 'F="../../assets/svg/X.svg"'
include <../config.scad>
F = "../../assets/svg/C.svg";
linear_extrude(1) import(F, center=true);
