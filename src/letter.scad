// ===== CHARGE letter tiles: 3-color neon-channel construction =====
// Per-letter data comes from tools/centerline.py: <L>_paths (tube centerlines, mm,
// open or closed), <L>_closed flags, <L>_pixels (collar centers), <L>_bbox.
// Cross-section (locked specs): BLACK tile base + outer channel wall / WHITE floor
// liner + inner wall + collars / CLEAR welded lens with baked fuzzy top.
// Prints tile-down lens-UP in use orientation, no supports; pixels plug in from behind.
// Filaments: 1=black 2=white 3=clear (tools/make_3mf.py black white clear out.3mf).

lt_ch_in    = 18;     // channel interior width (= bolt_inner; collar Ø16 fits)
lt_wall_wh  = 0.8;    // white inner lining wall
lt_wall_bk  = 1.2;    // black outer structural wall
lt_band_out = lt_ch_in + 2 * (lt_wall_wh + lt_wall_bk);  // 22mm outer stroke (= bolt_outer)
lt_liner_t  = 0.4;    // white reflective floor lining over the tile
lt_gap      = 15;     // LED-tip -> lens air gap (A0 winner)
lt_wall_h   = dome_clear + lt_gap;   // channel wall height above the tile (19mm)
lt_lens_t   = 1.2;    // clear lens thickness (testbox-validated)
lt_fuse     = 0.1;    // clear/wall overlap so the slicer welds them
lt_margin   = 2.5;    // tile margin beyond the band outer edge (kept tight: bed limits)

// stroke a tube centerline with width w (stadium chain; closed paths wrap)
module path_stroke(pts, w, closed = 0) {
    n = len(pts);
    for (i = [0 : n - (closed ? 1 : 2)])
        hull() {
            translate(pts[i])           circle(d = w);
            translate(pts[(i + 1) % n]) circle(d = w);
        }
}

module letter_band(paths, closedv, w) {
    for (k = [0 : len(paths) - 1]) path_stroke(paths[k], w, closedv[k]);
}

function lt_tile0(bbox)  = [-lt_band_out/2 - lt_margin, -lt_band_out/2 - lt_margin];
function lt_tile_sz(bbox) = [bbox[0] + lt_band_out + 2*lt_margin,
                             bbox[1] + lt_band_out + 2*lt_margin];

// BLACK: tile plate (with collar pockets) + outer channel wall
module letter_black(paths, closedv, pixels, bbox, label = "") {
    difference() {
        translate(lt_tile0(bbox)) linear_extrude(plate_t) square(lt_tile_sz(bbox));
        for (p = pixels)
            translate([p[0], p[1], -0.1]) cylinder(h = plate_t + 0.2, d = collar_od);
        if (label != "")            // letter label, debossed on the bed face (reads from behind)
            translate([lt_tile0(bbox)[0] + 14, lt_tile0(bbox)[1] + 12, -0.1])
                linear_extrude(0.9) mirror([1, 0, 0])
                    text(label, size = 10, halign = "center", valign = "center");
    }
    translate([0, 0, plate_t]) linear_extrude(lt_wall_h)
        difference() {
            letter_band(paths, closedv, lt_band_out);
            letter_band(paths, closedv, lt_band_out - 2 * lt_wall_bk);
        }
}

// WHITE: reflective floor liner + inner lining wall + collars
module letter_white(paths, closedv, pixels, bbox) {
    difference() {
        translate([0, 0, plate_t]) linear_extrude(lt_liner_t)
            letter_band(paths, closedv, lt_ch_in);
        for (p = pixels)
            translate([p[0], p[1], -0.1]) cylinder(h = plate_t + lt_liner_t + 0.2, d = pixel_through);
    }
    translate([0, 0, plate_t]) linear_extrude(lt_wall_h)
        difference() {
            letter_band(paths, closedv, lt_ch_in + 2 * lt_wall_wh);
            letter_band(paths, closedv, lt_ch_in);
        }
    for (p = pixels) place_collar(p[0], p[1]);
}

// CLEAR: welded lens roof + baked fuzzy top (datfile from tools/make_fuzz.py,
// sized to cover the band bbox; centered on the centerline bbox)
module letter_clear(paths, closedv, bbox, datfile, cell = 1.5) {
    z0  = plate_t + lt_wall_h - lt_fuse;
    top = plate_t + lt_wall_h + lt_lens_t;
    union() {
        translate([0, 0, z0]) linear_extrude(top - z0)
            letter_band(paths, closedv, lt_band_out);
        intersection() {
            translate([bbox[0]/2, bbox[1]/2, top - 0.1]) scale([cell, cell, 1])
                surface(file = datfile, center = true, convexity = 8);
            translate([0, 0, top - 0.3]) linear_extrude(3)
                letter_band(paths, closedv, lt_band_out);
        }
    }
}
