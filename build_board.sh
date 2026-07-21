#!/usr/bin/env bash
# Element-6 bolt board: 4 plates x 3 colors -> STLs -> per-plate 3-color 3MFs.
# Regenerate inputs first if the design changed:
#   python3 tools/bolt_compose6.py && python3 tools/boltboard.py --pitch 20
set -euo pipefail
cd "$(dirname "$0")"
OSCAD="${OPENSCAD:-openscad}"
mkdir -p stl
for P in 1 2 3 4; do
  for C in 1 2 3; do
    case $C in 1) N=black;; 2) N=white;; 3) N=clear;; esac
    "$OSCAD" -D PIECE=$P -D COL=$C -o "stl/board${P}_${N}.stl" \
      src/parts/bolt_piece.scad 2>"stl/b${P}${N:0:1}.log" && echo "  ok board${P}_${N}"
  done
done
for P in 1 2 3 4; do
  # filament order: 1=black (right/AMS + backup), 2=clear (right/AMS), 3=white (left/ext)
  python3 tools/make_3mf.py "stl/board${P}_black.stl" "stl/board${P}_clear.stl" \
    "stl/board${P}_white.stl" "stl/board${P}_3color.3mf"
done
# seam straps (single-color WHITE, plain STLs) + pixel pusher tool.
# S1/S2 = as-built (hex pockets, 8 mm rails); S3/S4 = backer-frame variants
# (rails 32, flat nut seats — needs M4x10/12 + washer/nut)
for S in 1 2; do
  "$OSCAD" -D STRAP=$S -o "stl/strap_s${S}.stl" src/parts/bracket.scad \
    2>"stl/strap${S}.log" && echo "  ok strap_s${S}"
done
for S in 3 4; do
  "$OSCAD" -D STRAP=$S -D bk_rail_h=32 -D bk_nut_pocket=0 \
    -o "stl/strap_s${S}.stl" src/parts/bracket.scad \
    2>"stl/strap${S}.log" && echo "  ok strap_s${S} (tall)"
done
"$OSCAD" -o stl/pusher.stl src/parts/pusher.scad 2>/dev/null && echo "  ok pusher"

# backer frame (spec 2026-07-21): layout -> segments, panels, trim, parts.
# PRINT GATE: frame_coupon.stl first — verify the PSU/Elite hole patterns on
# the physical units (sets ctl_diag in tools/boltframe.py) BEFORE rails print.
python3 tools/boltframe.py
for G in 1 2 3 4; do
  "$OSCAD" -D SEG=$G -o "stl/frame_seg${G}.stl" src/parts/frame.scad \
    2>"stl/frameseg${G}.log" && echo "  ok frame_seg${G}"
  "$OSCAD" -D PART=6 -D SEG=$G -o "stl/frame_trim${G}.stl" \
    src/parts/frame_parts.scad 2>/dev/null && echo "  ok frame_trim${G}"
done
for P in 1 2 3 4; do
  "$OSCAD" -D PANEL=$P -o "stl/frame_panel${P}.stl" src/parts/frame_panel.scad \
    2>"stl/framepanel${P}.log" && echo "  ok frame_panel${P}"
done
for N in 1:handle 2:foot 3:leg 4:gland_pg9 5:key 7:coupon; do
  "$OSCAD" -D PART=${N%%:*} -o "stl/frame_${N##*:}.stl" \
    src/parts/frame_parts.scad 2>/dev/null && echo "  ok frame_${N##*:}"
done

python3 tools/stl_stats.py stl/board?_black.stl stl/board?_white.stl stl/board?_clear.stl \
  stl/strap_s?.stl stl/pusher.stl stl/frame_seg?.stl stl/frame_panel?.stl
