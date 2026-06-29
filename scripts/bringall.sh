#!/bin/bash
# ⚠️ LEGACY (2026-06-26) — manual orchestration of the old real system. The target is the
#    single command:  ros2 launch openamrobot_bringup bringup.launch.py sim:=false
#    This script will be repointed/removed once that launch is validated on the robot (steps 3-4,
#    docs/ARCHITECTURE.md §6). IMPORTANT note: the sequence below WAITS for map->odom before
#    launching nav (anti-empty-costmaps) — reproduce in the new launch if needed.
#
# Robust full Nav2 stack on the real robot. Keep this copy in ~ on the Pi (survives reboot; /tmp does not).
# Run on the Pi:           bash ~/bringall.sh
#   detached:              nohup setsid bash ~/bringall.sh >/dev/null 2>&1 </dev/null &   then watch /tmp/bringall.log
#   custom start pose:     bash ~/bringall.sh <x> <y> <yaw>     (defaults 0 0 0; refine in RViz anyway)
# Order: clean-kill -> bring-up -> LIDAR health check -> localization -> AUTO initial pose
#        -> WAIT map->odom -> navigation (costmaps activate clean) -> goal relay.
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
exec > /tmp/bringall.log 2>&1

PX=${1:-0.0}; PY=${2:-0.0}; PYAW=${3:-0.0}    # default initial pose (map frame)

echo "### KILL"
# Only THIS project's nodes/launches — never a bare "ros2 launch" (that would kill any unrelated
# ros2 launch on the machine). SIGTERM first (lets serial ports be released), then SIGKILL.
KILL_PATTERNS="micro_ros_agent rplidar camera_node scan_body_filter ekf_node amcl map_server \
controller_server planner_server bt_navigator behavior_server smoother_server waypoint_follower \
lifecycle_manager collision_monitor velocity_smoother goal_relay slam_toolbox \
openamr_real_bringup localization_launch navigation_launch"
for p in $KILL_PATTERNS; do pkill -f "$p"; done
sleep 2
for p in $KILL_PATTERNS; do pkill -9 -f "$p"; done
sleep 3

echo "### BRINGUP"
BRINGUP=/home/botshare/openamr_real_bringup.launch.py
[ -f "$BRINGUP" ] || { echo "!!! MISSING $BRINGUP — aborting"; exit 1; }
ros2 launch "$BRINGUP" > /tmp/bringup.log 2>&1 &
sleep 20

echo "### LIDAR CHECK (must actually stream /scan)"
LIDAR_OK=0
for i in 1 2 3; do
  if timeout 4 ros2 topic echo /scan --qos-reliability best_effort --once >/dev/null 2>&1; then
    LIDAR_OK=1; echo "lidar OK"; break
  fi
  echo "lidar silent (try $i) — known RPLidar timeout"; sleep 4
done
[ $LIDAR_OK -eq 0 ] && echo "!!! LIDAR DEAD -> UNPLUG/REPLUG the lidar USB then re-run ~/bringall.sh"

echo "### LOCALIZATION"
MAP=/home/botshare/maps/coin_ok.yaml
[ -f "$MAP" ] || { echo "!!! MISSING MAP $MAP — costmaps would be empty; aborting"; exit 1; }
ros2 launch openamrobot_nav2 localization_launch.py map:="$MAP" use_sim_time:=false > /tmp/loc.log 2>&1 &
sleep 10

echo "### INITIAL POSE ($PX $PY yaw=$PYAW) — refine in RViz (2D Pose Estimate)"
QZ=$(python3 -c "import math;print(math.sin($PYAW/2.0))")
QW=$(python3 -c "import math;print(math.cos($PYAW/2.0))")
for k in 1 2 3; do
  ros2 topic pub -1 /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
"{header: {frame_id: 'map'}, pose: {pose: {position: {x: $PX, y: $PY, z: 0.0}, orientation: {z: $QZ, w: $QW}}, covariance: [0.25,0,0,0,0,0, 0,0.25,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.07]}}" >/dev/null 2>&1
  sleep 1
done

echo "### WAIT map->odom (otherwise empty costmaps)"
MAPODOM=0
for i in $(seq 1 20); do
  if timeout 2 ros2 run tf2_ros tf2_echo map odom 2>/dev/null | grep -q Translation; then
    MAPODOM=1; echo "map->odom OK"; break
  fi
  sleep 1
done
[ $MAPODOM -eq 0 ] && echo "!!! map->odom missing (lidar dead? otherwise do a 2D Pose Estimate in RViz)"

echo "### NAVIGATION"
ros2 launch openamrobot_nav2 navigation_launch.py use_sim_time:=false > /tmp/nav.log 2>&1 &
sleep 18

echo "### GOAL RELAY"
RELAY=/home/botshare/goal_relay.py
if [ -f "$RELAY" ]; then python3 "$RELAY" > /tmp/relay.log 2>&1 &
else echo "!!! MISSING $RELAY (skipping forwarder — RViz goals won't reach Nav2)"; fi
sleep 3

echo "### STATUS"
ros2 node list | grep -iE "amcl|controller_server|planner_server|bt_navigator|goal_relay" | sort
echo -n "scan_filtered "; ros2 topic info /scan_filtered 2>/dev/null | grep -i "publisher count"
echo -n "global costmap occ: "; timeout 8 ros2 topic echo /global_costmap/costmap --field data --once 2>/dev/null | tr "," "\n" | grep -vE "^0$|^-1$|^$" | wc -l
echo "### UP"
sleep 3600
