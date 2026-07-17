#!/bin/sh
# Build a node-target wasm of the effect suite and run the full QA (sim/qa.mjs).
# Run from the repo root: sh sim/qa.sh
set -e
emcc sim/sim_main.cpp sim/wled_shim.cpp \
  -std=c++17 -O1 \
  -s MODULARIZE=1 -s EXPORT_NAME=ChargeSim -s ENVIRONMENT=node \
  -s EXPORTED_RUNTIME_METHODS='["HEAPU8","HEAPU32","UTF8ToString"]' \
  -o sim/charge_sim_node.js
node sim/qa.mjs
