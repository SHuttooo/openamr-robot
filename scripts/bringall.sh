#!/bin/bash
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
for p in micro_ros_agent rplidar camera_node scan_body_filter ekf_node amcl map_server \
  controller_server planner_server bt_navigator behavior_server smoother_server \
  waypoint_follower lifecycle_manager collision_monitor goal_relay slam_toolbox "ros2 launch"; do
  pkill -9 -f "$p"
done
sleep 5

echo "### BRINGUP"
ros2 launch /home/botshare/openamr_real_bringup.launch.py > /tmp/bringup.log 2>&1 &
sleep 20

echo "### LIDAR CHECK (must actually stream /scan)"
LIDAR_OK=0
for i in 1 2 3; do
  if timeout 4 ros2 topic echo /scan --qos-reliability best_effort --once >/dev/null 2>&1; then
    LIDAR_OK=1; echo "lidar OK"; break
  fi
  echo "lidar muet (try $i) — RPLidar timeout connu"; sleep 4
done
[ $LIDAR_OK -eq 0 ] && echo "!!! LIDAR MORT -> DEBRANCHE/REBRANCHE l'USB du lidar puis relance ~/bringall.sh"

echo "### LOCALIZATION"
ros2 launch openamrobot_nav2 localization_launch.py map:=/home/botshare/maps/coin_ok.yaml use_sim_time:=false > /tmp/loc.log 2>&1 &
sleep 10

echo "### INITIAL POSE ($PX $PY yaw=$PYAW) — affiner dans RViz (2D Pose Estimate)"
QZ=$(python3 -c "import math;print(math.sin($PYAW/2.0))")
QW=$(python3 -c "import math;print(math.cos($PYAW/2.0))")
for k in 1 2 3; do
  ros2 topic pub -1 /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
"{header: {frame_id: 'map'}, pose: {pose: {position: {x: $PX, y: $PY, z: 0.0}, orientation: {z: $QZ, w: $QW}}, covariance: [0.25,0,0,0,0,0, 0,0.25,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.07]}}" >/dev/null 2>&1
  sleep 1
done

echo "### WAIT map->odom (sinon costmaps vides)"
MAPODOM=0
for i in $(seq 1 20); do
  if timeout 2 ros2 run tf2_ros tf2_echo map odom 2>/dev/null | grep -q Translation; then
    MAPODOM=1; echo "map->odom OK"; break
  fi
  sleep 1
done
[ $MAPODOM -eq 0 ] && echo "!!! map->odom absent (lidar mort ? sinon fais un 2D Pose Estimate dans RViz)"

echo "### NAVIGATION"
ros2 launch openamrobot_nav2 navigation_launch.py use_sim_time:=false > /tmp/nav.log 2>&1 &
sleep 18

echo "### GOAL RELAY"
python3 /home/botshare/goal_relay.py > /tmp/relay.log 2>&1 &
sleep 3

echo "### STATUS"
ros2 node list | grep -iE "amcl|controller_server|planner_server|bt_navigator|goal_relay" | sort
echo -n "scan_filtered "; ros2 topic info /scan_filtered 2>/dev/null | grep -i "publisher count"
echo -n "global costmap occ: "; timeout 8 ros2 topic echo /global_costmap/costmap --field data --once 2>/dev/null | tr "," "\n" | grep -vE "^0$|^-1$|^$" | wc -l
echo "### UP"
sleep 3600
