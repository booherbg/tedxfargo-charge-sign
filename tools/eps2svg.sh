#!/usr/bin/env bash
# Convert Illustrator EPS art -> SVG for OpenSCAD (true vector via gs + pdftocairo).
# Usage: tools/eps2svg.sh [file.eps ...]   (default: all of assets/letters/*.eps)
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:$PATH"
mkdir -p assets/svg

files=("$@")
[ ${#files[@]} -eq 0 ] && files=(assets/letters/*.eps)

for f in "${files[@]}"; do
  name=$(basename "$f" .eps)
  gs -q -dSAFER -dBATCH -dNOPAUSE -dEPSCrop -sDEVICE=pdfwrite -o "/tmp/$name.pdf" "$f"
  pdftocairo -svg "/tmp/$name.pdf" "assets/svg/$name.svg"
  echo "  ✓ assets/svg/$name.svg"
done
