#!/usr/bin/env bash
# Regenerate every STL from src/parts/*.scad into ./stl/
set -euo pipefail
cd "$(dirname "$0")"
OSCAD="${OPENSCAD:-openscad}"
mkdir -p stl

PARTS=(coupon_body cap_1mm cap_2mm cap_3mm collar_harness collar_v2)

echo "Rendering CHARGE coupon STLs with $OSCAD ..."
for p in "${PARTS[@]}"; do
  "$OSCAD" -q -o "stl/$p.stl" "src/parts/$p.scad" && echo "  ✓ stl/$p.stl"
done
echo "Done. STLs in ./stl/"
