#!/bin/bash
# Link PC -> Pi: push the platform-sw source you edited on the PC to the robot and rebuild.
# Run this on the PC after editing under openamr-platform-sw. One-way (PC is the source of truth).
#
#   bash ~/Documents/openamr/scripts/deploy_to_pi.sh            # sync + build everything
#   bash ~/Documents/openamr/scripts/deploy_to_pi.sh nav2 docking   # sync all, build only these pkgs
#
# Protects robot-specific data on the Pi: it does NOT overwrite the maps or the camera calibration
# (those live only on the Pi). Excludes build artifacts.
set -e

PC_SRC="$HOME/Documents/openAMRobot/openamr-platform-sw/ros2/src/"
PI="botshare@172.17.201.29"
PI_WS="openamr-platform-sw/ros2"

echo "### rsync  PC -> Pi  (code only; maps + camera calib preserved)"
rsync -a --info=stats1 -e "ssh -o BatchMode=yes" \
  --exclude '__pycache__' --exclude 'build' --exclude 'install' --exclude 'log' \
  --exclude '*.bak' \
  --exclude 'openamrobot_nav2/maps/' \
  --exclude 'openamrobot_perception/config/camera_info.yaml' \
  "$PC_SRC" "$PI:$PI_WS/src/"

# Build: all packages, or only the ones named as args (faster).
if [ "$#" -gt 0 ]; then
  SEL="--packages-select"
  for p in "$@"; do SEL="$SEL openamrobot_$p"; done
else
  SEL=""
fi

echo "### colcon build on the Pi  ($([ -n "$SEL" ] && echo "$*" || echo "all"))"
ssh -o BatchMode=yes "$PI" "cd ~/$PI_WS && source /opt/ros/jazzy/setup.bash && \
  colcon build --symlink-install $SEL 2>&1 | tail -4"

echo "### Done — PC and Pi are in sync."
