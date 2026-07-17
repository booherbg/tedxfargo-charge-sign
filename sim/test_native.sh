#!/bin/sh
# Native sanitizer soak of the shared effect code. Run from repo root.
set -e
OUT=$(mktemp -d)/charge_fx_test
# ASan is broken on this macOS/Apple-clang combo (init CHECK failure), so the
# test carries its own guard bands around the grid buffer for OOB detection;
# UBSan (trap-on-error) covers overflow/shift/misalignment. Effect code
# allocates nothing, so there is no leak surface.
clang++ -std=c++17 -O1 -g -Wall -Wextra \
  -fsanitize=undefined -fno-sanitize-recover=all \
  sim/test_native.cpp sim/wled_shim.cpp -o "$OUT"
"$OUT"
