// One billboard piece, one color body. Build via -D (numeric only — string -D is
// unreliable on OpenSCAD 2021.01):
//   openscad -D PIECE=<1..6> -D COL=<1|2|3> -o out.stl src/parts/piece.scad
//   COL: 1 = BLACK (plate + outer walls), 2 = WHITE (liner + inner walls + collars),
//        3 = CLEAR (welded lens + baked fuzzy top, fuzz_piece_N.dat)
// Cross-section per docs/locked-specs.md; construction identical to the proven
// letter_C tile, clipped to the piece mask (corridor cuts) with seam clearance.
include <../config.scad>
include <../collar.scad>
include <word_layout.scad>

PIECE = 1;
COL   = 1;

pc_ch_in    = 18;      // channel interior (= bolt_inner)
pc_wall_wh  = 0.8;     // white lining wall
pc_wall_bk  = 1.2;     // black outer wall
pc_band_out = pc_ch_in + 2*(pc_wall_wh + pc_wall_bk);   // 22
pc_liner_t  = 0.4;
pc_gap      = 15;
pc_wall_h   = dome_clear + pc_gap;      // 19
pc_lens_t   = 1.2;
pc_fuse     = 0.1;
pc_seam     = 0.06;    // per-face seam clearance (0.12 per joint)
pc_scr_d    = 4.5;     // rail screws
pc_tie_d    = 3.2;     // zip-tie holes

segs   = wl_piece_segs[PIECE-1];
pxs    = wl_piece_px[PIECE-1];
mask   = wl_piece_mask[PIECE-1];
scr    = wl_piece_scr[PIECE-1];
ties   = wl_piece_tie[PIECE-1];
ctr    = wl_centers[PIECE-1];
fx0 = wl_face[0]; fy0 = wl_face[1]; fx1 = wl_face[2]; fy1 = wl_face[3];

module path_stroke(pts, w) {
    n = len(pts);
    for (i = [0 : n-2])
        hull() { translate(pts[i]) circle(d=w); translate(pts[i+1]) circle(d=w); }
}
module band(w) { for (s = segs) path_stroke(wl_paths[s], w); }
module piece_mask() { offset(delta = -pc_seam) polygon(mask); }
module clip() { intersection() { children(0); linear_extrude(60, center=true) piece_mask(); } }

module body_black() {
    clip() union() {
        difference() {
            translate([fx0, fy0]) linear_extrude(plate_t) square([fx1-fx0, fy1-fy0]);
            for (p = pxs)  translate([p[0], p[1], -0.1]) cylinder(h=plate_t+0.2, d=collar_od);
            for (s = scr)  translate([s[0], s[1], -0.1]) cylinder(h=plate_t+0.2, d=pc_scr_d);
            for (t = ties) translate([t[0], t[1], -0.1]) cylinder(h=plate_t+0.2, d=pc_tie_d);
            translate([ctr[0], fy0+11, -0.1]) linear_extrude(0.9) mirror([1,0,0])
                text(wl_labels[PIECE-1], size=8, halign="center", valign="center");
        }
        translate([0,0,plate_t]) linear_extrude(pc_wall_h)
            difference() { band(pc_band_out); band(pc_band_out - 2*pc_wall_bk); }
    }
}

module body_white() {
    clip() union() {
        difference() {
            translate([0,0,plate_t]) linear_extrude(pc_liner_t) band(pc_ch_in);
            for (p = pxs) translate([p[0], p[1], -0.1])
                cylinder(h=plate_t+pc_liner_t+0.2, d=pixel_through);
        }
        translate([0,0,plate_t]) linear_extrude(pc_wall_h)
            difference() { band(pc_ch_in + 2*pc_wall_wh); band(pc_ch_in); }
        for (p = pxs) place_collar(p[0], p[1]);
    }
}

module body_clear() {
    z0  = plate_t + pc_wall_h - pc_fuse;
    top = plate_t + pc_wall_h + pc_lens_t;
    clip() union() {
        translate([0,0,z0]) linear_extrude(top - z0) band(pc_band_out);
        intersection() {
            // base offset 0.1504: OFF the 3-decimal height lattice, so no bump top
            // can be exactly coplanar with the lens top (CGAL emits non-manifold
            // micro-slivers at such tangencies — Bambu flags them)
            translate([ctr[0], ctr[1], top-0.1504]) scale([0.6667, 0.6667, 1])  // V8: dat sampled at cell/3 = 0.667mm
                surface(file = str("fuzz_piece_", PIECE, ".dat"), center = true, convexity = 8);
            translate([0,0,top-0.3]) linear_extrude(3) band(pc_band_out);
        }
    }
}

if (COL == 1) body_black();
else if (COL == 2) body_white();
else body_clear();
