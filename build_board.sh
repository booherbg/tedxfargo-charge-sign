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
  python3 tools/make_3mf.py "stl/board${P}_black.stl" "stl/board${P}_white.stl" \
    "stl/board${P}_clear.stl" "stl/board${P}_3color.3mf"
done
python3 tools/stl_stats.py stl/board?_black.stl stl/board?_white.stl stl/board?_clear.stl
