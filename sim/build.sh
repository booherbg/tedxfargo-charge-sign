#!/bin/sh
# Build the CHARGE effect simulator (wasm) into docs/sign-preview/simulator/.
# Run from the repo root: sh sim/build.sh
set -e
OUT=docs/sign-preview/simulator
mkdir -p "$OUT"

emcc sim/sim_main.cpp sim/wled_shim.cpp sim/vendor/fastled_slim.cpp \
  -std=c++17 -O2 -Isim/vendor \
  -s MODULARIZE=1 -s EXPORT_NAME=ChargeSim \
  -s ENVIRONMENT=web \
  -s ALLOW_MEMORY_GROWTH=0 -s INITIAL_MEMORY=16MB \
  -s EXPORTED_RUNTIME_METHODS='["HEAPU8","HEAPU32","UTF8ToString"]' \
  -o "$OUT/charge_sim.js"

# The sim page consumes the REAL artifacts, not copies of the algorithm:
#   ledmap.json     — the exact file flashed to the controller
#   word_pixmap.json — the wiring truth (physical mm positions per chain index)
#   word cuts       — tube centerline paths, drawn as the dark "glass" backdrop
# refresh palette data extracted from the WLED source (skip if no checkout)
if [ -d "${WLED:-$HOME/workspace/WLED-charge}" ]; then
  python3 sim/extract_palettes.py "${WLED:-$HOME/workspace/WLED-charge}" "$OUT/wled_palettes.json"
fi
# device custom palettes (from the backups) ride along for the palette picker
cp wled/backups/palette0.json wled/backups/palette1.json wled/backups/palette2.json "$OUT/" 2>/dev/null || true

cp wled/word-controller/ledmap.json "$OUT/ledmap.json"
cp src/parts/word_pixmap.json "$OUT/word_pixmap.json"
if [ -f src/parts/word_cuts_repairs.json ]; then
  cp src/parts/word_cuts_repairs.json "$OUT/word_cuts.json"
else
  cp src/parts/word_cuts.json "$OUT/word_cuts.json"
fi

echo "built $OUT (serve with: python3 sim/serve.py — no-cache, always fresh)"
