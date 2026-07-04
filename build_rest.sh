#!/usr/bin/env bash
# Render pieces 2-6 (3 color bodies each, in parallel per piece) + 3MFs.
set -euo pipefail
cd "$(dirname "$0")"
OSCAD="${OPENSCAD:-openscad}"
for P in 2 3 4 5 6; do
  "$OSCAD" -D PIECE=$P -D COL=1 -o stl/piece${P}_black.stl src/parts/piece.scad 2>stl/p${P}black.log &
  "$OSCAD" -D PIECE=$P -D COL=2 -o stl/piece${P}_white.stl src/parts/piece.scad 2>stl/p${P}white.log &
  "$OSCAD" -D PIECE=$P -D COL=3 -o stl/piece${P}_clear.stl src/parts/piece.scad 2>stl/p${P}clear.log &
  wait
  echo "piece $P rendered"
done
for P in 1 2 3 4 5 6; do
  python3 tools/make_3mf.py stl/piece${P}_black.stl stl/piece${P}_white.stl \
    stl/piece${P}_clear.stl stl/piece${P}_3color.3mf
done
echo ALL PIECES DONE
