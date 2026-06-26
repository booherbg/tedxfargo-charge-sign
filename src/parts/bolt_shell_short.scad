// Build target: short (~10mm tall) lightning-bolt shell — a close ~4mm gap to
// compare against the tall (15mm-gap) bolt. The same bolt_lens fits both.
// wall_h = 8 -> total 10mm (plate 2 + walls 8); gap = 8 - dome_clear(4) = 4mm.
include <../config.scad>
include <../collar.scad>
include <../bolt.scad>
bolt_shell(8);
