#!/bin/bash
# Reproducible firmware overlay (Raj review PR5): clone the PINNED upstream Linorobot2 firmware and
# copy this overlay over it. Run on the Pi (or any build host). Idempotent.
set -e

UPSTREAM_URL="https://github.com/linorobot/linorobot2_hardware.git"
UPSTREAM_BRANCH="jazzy"
UPSTREAM_COMMIT="aaf9d59"
DEST="$HOME/linorobot2_hardware"
OVERLAY="$(cd "$(dirname "$0")" && pwd)"   # this firmware/ directory

if [ ! -d "$DEST/.git" ]; then
  echo "### cloning upstream $UPSTREAM_URL ($UPSTREAM_BRANCH)"
  git clone --branch "$UPSTREAM_BRANCH" "$UPSTREAM_URL" "$DEST"
fi

echo "### checking out pinned commit $UPSTREAM_COMMIT"
git -C "$DEST" fetch --all --quiet || true
git -C "$DEST" checkout "$UPSTREAM_COMMIT"

echo "### applying overlay from $OVERLAY"
cp "$OVERLAY/config/lino_base_config.h" "$DEST/firmware/config/lino_base_config.h"
cp "$OVERLAY/lib/encoder/encoder.h"     "$DEST/firmware/lib/encoder/encoder.h"
cp "$OVERLAY/lib/pid/pid.h"             "$DEST/firmware/lib/pid/pid.h"
cp "$OVERLAY/lib/pid/pid.cpp"           "$DEST/firmware/lib/pid/pid.cpp"
cp "$OVERLAY/src/firmware.ino"          "$DEST/firmware/src/firmware.ino"

echo "### done. Build:  cd $DEST/firmware && ROS_DISTRO=jazzy ~/.platformio/penv/bin/pio run -e teensy40"
