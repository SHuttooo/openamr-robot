#!/bin/bash
# Ground drive test (loaded), ROBOT ON THE GROUND with ~2 m clear ahead.
# Closed-loop forward 0.10 m/s ~4s, then stop; reports odom displacement + L/R rpm.
# Needs the agent running. Run detached on the Pi. Healthy = moves, L/R equalised (PID), left holds.
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
exec > /tmp/gtest.log 2>&1
timeout 12 ros2 topic echo /debug/left  --qos-reliability best_effort --field y > /tmp/L.txt 2>/dev/null &
timeout 12 ros2 topic echo /debug/right --qos-reliability best_effort --field y > /tmp/R.txt 2>/dev/null &
timeout 5 ros2 topic echo /odom/unfiltered --once --field pose.pose.position > /tmp/odo_s.txt 2>/dev/null
sleep 1
echo "### forward closed-loop 0.10 m/s ~4s"
ros2 topic pub -t 40 -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.10}, angular: {z: 0.0}}" >/dev/null 2>&1
ros2 topic pub -t 6 -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}" >/dev/null 2>&1
sleep 1
timeout 5 ros2 topic echo /odom/unfiltered --once --field pose.pose.position > /tmp/odo_e.txt 2>/dev/null
wait
echo "--- odom START:"; grep -E "x:|y:" /tmp/odo_s.txt 2>/dev/null | head -2
echo "--- odom END:";   grep -E "x:|y:" /tmp/odo_e.txt 2>/dev/null | head -2
echo "L non-zero: $(grep -cE '[1-9]' /tmp/L.txt) | vals: $(grep -E '[1-9]' /tmp/L.txt | head -8 | tr '\n' ' ')"
echo "R non-zero: $(grep -cE '[1-9]' /tmp/R.txt) | vals: $(grep -E '[1-9]' /tmp/R.txt | head -8 | tr '\n' ' ')"
echo "### DONE"
