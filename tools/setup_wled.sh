#!/bin/sh
# Rebuild the WLED firmware working tree from scratch — everything needed
# lives in THIS repo; the clone is disposable.
#
#   sh tools/setup_wled.sh            # clone + patch + sync usermod
#   sh tools/setup_wled.sh --build    # ...and compile GL-C-616WL
#   WLED_DIR=/elsewhere sh tools/setup_wled.sh
#
# What it does (idempotent — safe to re-run; also how you re-sync after
# editing wled/usermods/tedxfargo/* here):
#   1. clone GLEDOPTO/WLED and pin the EXACT base commit the sign runs
#      (branch gledopto-16.0.1 == stock WLED 16.0.1 + Gledopto board envs)
#   2. enable the usermod in [env:GL-C-616WL] — audioreactive MUST be
#      relisted: the child env REPLACES the inherited custom_usermods
#   3. copy wled/usermods/tedxfargo/ (the source of truth) into the clone
#
# Build env gotchas (see memory/wled-firmware-build-gotchas.md):
#   - PlatformIO needs Python <= 3.13 (pipx install --python python3.12)
#   - the pipx venv needs pip:  .../python -m ensurepip --upgrade
# OTA: upload build_output/release/WLED_16.0.1_GL-C-616WL.bin at
# http://<device-ip>/update (bin must stay under the 1,572,864-byte slot).
set -e
cd "$(dirname "$0")/.."                                   # repo root

WLED_DIR="${WLED_DIR:-$HOME/workspace/WLED-charge}"
BASE_SHA=0e009863            # "Modify for GLEDOPTO" — the exact firmware base
WORK_BRANCH=charge-tedxfargo

if [ ! -d "$WLED_DIR/.git" ]; then
  echo "==> cloning GLEDOPTO/WLED into $WLED_DIR"
  git clone --branch gledopto-16.0.1 https://github.com/GLEDOPTO/WLED.git "$WLED_DIR"
fi

cd "$WLED_DIR"
if ! git merge-base --is-ancestor "$BASE_SHA" HEAD 2>/dev/null; then
  echo "==> pinning base commit $BASE_SHA (upstream branch has moved)"
  git checkout "$BASE_SHA"
fi
git rev-parse --verify "$WORK_BRANCH" >/dev/null 2>&1 \
  || git checkout -b "$WORK_BRANCH" "$BASE_SHA"
git checkout "$WORK_BRANCH" >/dev/null 2>&1 || true
cd - >/dev/null

echo "==> enabling the usermod in [env:GL-C-616WL]"
python3 - "$WLED_DIR" <<'EOF'
import sys
p = sys.argv[1] + "/platformio_override.ini"
s = open(p).read()
if "custom_usermods = audioreactive tedxfargo" in s:
    print("    already enabled")
else:
    old = "[env:GL-C-616WL]\nextends = env:esp32_eth\n"
    assert old in s, "GL-C-616WL env not found — wrong WLED base?"
    new = (old +
           "; parent env:esp32_eth sets 'custom_usermods = audioreactive'; setting the\n"
           "; option here REPLACES the inherited value, so audioreactive must be relisted\n"
           "custom_usermods = audioreactive tedxfargo\n")
    open(p, "w").write(s.replace(old, new, 1))
    print("    patched")
EOF

echo "==> syncing usermod (source of truth: wled/usermods/tedxfargo/)"
mkdir -p "$WLED_DIR/usermods/tedxfargo"
cp wled/usermods/tedxfargo/tedxfargo.cpp \
   wled/usermods/tedxfargo/charge_fx.h \
   wled/usermods/tedxfargo/charge_geometry.h \
   wled/usermods/tedxfargo/library.json \
   "$WLED_DIR/usermods/tedxfargo/"

if [ "$1" = "--build" ]; then
  echo "==> building GL-C-616WL"
  ( cd "$WLED_DIR" && "${PIO:-$HOME/.local/bin/pio}" run -e GL-C-616WL )
  echo "==> OTA bin: $WLED_DIR/build_output/release/WLED_16.0.1_GL-C-616WL.bin"
else
  echo "==> done. Build with: sh tools/setup_wled.sh --build"
fi
