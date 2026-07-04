// One C1 bolt-board plate, one color body. Same cross-section as the letters.
//   openscad -D PIECE=<1|2> -D COL=<1|2|3> -o out.stl src/parts/bolt_piece.scad
//   PIECE: 1 = bottom plate (y 0..seam), 2 = top plate. COL: 1 black, 2 white, 3 clear.
// Paths are pre-split at the seam with 13mm pullbacks (styled neon breaks), so the
// straight seam never crosses a channel. Fuzz: fuzz_board_<PIECE>.dat (dead-banded).
include <../config.scad>
include <../collar.scad>
include <board_layout.scad>

PIECE = 1;
COL   = 1;

pb_ch_in    = 18;
pb_wall_wh  = 0.8;
pb_wall_bk  = 1.2;
pb_band_out = pb_ch_in + 2*(pb_wall_wh + pb_wall_bk);
pb_liner_t  = 0.4;
pb_wall_h   = dome_clear + 15;
pb_lens_t   = 1.2;
pb_fuse     = 0.1;
pb_seam     = 0.06;
pb_scr_d    = 4.5;
pb_tie_d    = 3.2;

y0 = PIECE == 1 ? 0 : bb_seam;
y1 = PIECE == 1 ? bb_seam : bb_face[1];
pxs  = [for (p = bb_px)  if (p[1] >= y0 && p[1] < y1) p];
scrs = [for (p = bb_scr) if (p[1] >= y0 && p[1] < y1) p];
ties = [for (p = bb_tie) if (p[1] >= y0 && p[1] < y1) p];

module path_stroke(pts, w) {
    for (i = [0 : len(pts)-2])
        hull() { translate(pts[i]) circle(d=w); translate(pts[i+1]) circle(d=w); }
}
module band(w) { for (p = bb_paths) path_stroke(p, w); }
module clip() {                       // plate window with seam clearance
    intersection() {
        children(0);
        translate([0, y0 + (PIECE == 1 ? 0 : pb_seam), -1])
            cube([bb_face[0], y1 - y0 - pb_seam, 60]);
    }
}

module body_black() {
    clip() union() {
        difference() {
            linear_extrude(plate_t) square([bb_face[0], bb_face[1]]);
            for (p = pxs)  translate([p[0], p[1], -0.1]) cylinder(h=plate_t+0.2, d=collar_od);
            for (p = scrs) translate([p[0], p[1], -0.1]) cylinder(h=plate_t+0.2, d=pb_scr_d);
            for (p = ties) translate([p[0], p[1], -0.1]) cylinder(h=plate_t+0.2, d=pb_tie_d);
            translate([bb_face[0]/2, y0 + 14, -0.1]) linear_extrude(0.9) mirror([1,0,0])
                text(str("B", PIECE), size=8, halign="center", valign="center");
        }
        translate([0,0,plate_t]) linear_extrude(pb_wall_h)
            difference() { band(pb_band_out); band(pb_band_out - 2*pb_wall_bk); }
    }
}
module body_white() {
    clip() union() {
        difference() {
            translate([0,0,plate_t]) linear_extrude(pb_liner_t) band(pb_ch_in);
            for (p = pxs) translate([p[0], p[1], -0.1])
                cylinder(h=plate_t+pb_liner_t+0.2, d=pixel_through);
        }
        translate([0,0,plate_t]) linear_extrude(pb_wall_h)
            difference() { band(pb_ch_in + 2*pb_wall_wh); band(pb_ch_in); }
        for (p = pxs) place_collar(p[0], p[1]);
    }
}
module body_clear() {
    z0  = plate_t + pb_wall_h - pb_fuse;
    top = plate_t + pb_wall_h + pb_lens_t;
    clip() union() {
        translate([0,0,z0]) linear_extrude(top - z0) band(pb_band_out);
        intersection() {
            translate([bb_face[0]/2, y0 + (y1-y0)/2, top-0.1504]) scale([1.5,1.5,1])
                surface(file = str("fuzz_board_", PIECE, ".dat"), center = true, convexity = 8);
            translate([0,0,top-0.3]) linear_extrude(3) band(pb_band_out);
        }
    }
}

if (COL == 1) body_black();
else if (COL == 2) body_white();
else body_clear();
