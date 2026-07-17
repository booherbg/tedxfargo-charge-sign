#!/bin/sh
# Native sanitizer soak of the shared effect code. Run from repo root.
set -e
OUT=$(mktemp -d)/charge_fx_test
# ASan is broken on this macOS/Apple-clang combo (init CHECK failure), so the
# test carries its own guard bands around the grid buffer for OOB detection;
# UBSan (trap-on-error) covers overflow/shift/misalignment. Effect code
# allocates nothing, so there is no leak surface.
# vendored fastled_slim.cpp: WLED's own code contains a formally-UB negative
# left-shift (two's-complement in practice, ships on the device as-is) — keep
# UBSan's shift check off for THAT file only; everything of ours gets the works.
clang++ -std=c++17 -O1 -g -Isim/vendor -c sim/vendor/fastled_slim.cpp \
  -fsanitize=undefined -fno-sanitize=shift -fno-sanitize-recover=all \
  -o "$(dirname "$OUT")/fastled_slim.o"
clang++ -std=c++17 -O1 -g -Wall -Wextra -Isim/vendor \
  -fsanitize=undefined -fno-sanitize-recover=all \
  sim/test_native.cpp sim/wled_shim.cpp "$(dirname "$OUT")/fastled_slim.o" -o "$OUT"
"$OUT"
