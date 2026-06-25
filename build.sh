#!/usr/bin/env bash
# Regenerate every STL from src/parts/*.scad into ./stl/
set -euo pipefail
cd "$(dirname "$0")"
OSCAD="${OPENSCAD:-openscad}"
mkdir -p stl

PARTS=(coupon_body coupon3x3 lid_0p6mm lid_1mm lid_2mm lid_3mm lid_6mm collar_harness collar_v2)

echo "Rendering CHARGE coupon STLs with $OSCAD ..."
for p in "${PARTS[@]}"; do
  "$OSCAD" -q -o "stl/$p.stl" "src/parts/$p.scad" && echo "  ✓ stl/$p.stl"
done
echo "Done. STLs in ./stl/"
