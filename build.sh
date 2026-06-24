#!/usr/bin/env bash
# Regenerate every STL from src/parts/*.scad into ./stl/
set -euo pipefail
cd "$(dirname "$0")"
OSCAD="${OPENSCAD:-openscad}"
mkdir -p stl

PARTS=(coupon_body panel_1mm panel_2mm panel_3mm)

echo "Rendering CHARGE coupon STLs with $OSCAD ..."
for p in "${PARTS[@]}"; do
  "$OSCAD" -q -o "stl/$p.stl" "src/parts/$p.scad" && echo "  ✓ stl/$p.stl"
done
echo "Done. STLs in ./stl/"
