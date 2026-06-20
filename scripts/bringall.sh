#!/bin/bash
# Full Nav2 stack on the real robot. Run on the Pi, detached:
#   nohup setsid bash /tmp/bringall.sh >/dev/null 2>&1 </dev/null &   then wait for "### UP"
# Order: clean-kill -> base bring-up -> localization (coin_ok) -> navigation -> goal relay.
# AFTER it is up: in RViz do "2D Pose Estimate" FIRST (gives map->odom) so the costmaps fill;
# otherwise the costmaps come up EMPTY and the robot navigates blind (see navigation.md gotcha #8).
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
exec > /tmp/bringall.log 2>&1
for p in micro_ros_agent rplidar camera_node scan_body_filter ekf_node amcl map_server \
  controller_server planner_server bt_navigator behavior_server smoother_server \
  waypoint_follower lifecycle_manager collision_monitor goal_relay slam_toolbox "ros2 launch"; do
  pkill -9 -f "$p"
done
sleep 5
ros2 launch /home/botshare/openamr_real_bringup.launch.py > /tmp/bringup.log 2>&1 &
sleep 20
echo "### BRINGUP"; ros2 topic list | grep -E "scan_filtered|/odom|/imu|camera" | sort
ros2 launch openamrobot_nav2 localization_launch.py map:=/home/botshare/maps/coin_ok.yaml use_sim_time:=false > /tmp/loc.log 2>&1 &
sleep 12
ros2 launch openamrobot_nav2 navigation_launch.py use_sim_time:=false > /tmp/nav.log 2>&1 &
sleep 18
python3 /home/botshare/goal_relay.py > /tmp/relay.log 2>&1 &
sleep 3
echo "### NODES"; ros2 node list | grep -iE "amcl|controller_server|planner_server|bt_navigator|goal_relay" | sort
echo "### scan_filtered pub:"; ros2 topic info /scan_filtered 2>/dev/null | grep -i "publisher count"
echo "### UP"
sleep 3600
