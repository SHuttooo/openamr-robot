#!/bin/bash
# Wheel test, WHEELS OFF THE GROUND. Open-loop equal PWM on both wheels, count non-zero rpm.
# Needs the agent already running (agentup.sh or bringall.sh). Run detached on the Pi.
# Healthy = both L and R report continuous rpm. Left=0/intermittent => left faux-contact.
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
exec > /tmp/wtest.log 2>&1
timeout 9 ros2 topic echo /debug/left  --qos-reliability best_effort --field y > /tmp/L.txt 2>/dev/null &
timeout 9 ros2 topic echo /debug/right --qos-reliability best_effort --field y > /tmp/R.txt 2>/dev/null &
sleep 1
echo "### openloop 300 (both wheels) ~6s"
ros2 topic pub -t 60 -r 10 /debug/openloop geometry_msgs/msg/Vector3 "{x: 300.0, y: 300.0, z: 0.0}" >/dev/null 2>&1
sleep 1; wait
echo "L non-zero: $(grep -cE '[1-9]' /tmp/L.txt) | vals: $(grep -E '[1-9]' /tmp/L.txt | head -6 | tr '\n' ' ')"
echo "R non-zero: $(grep -cE '[1-9]' /tmp/R.txt) | vals: $(grep -E '[1-9]' /tmp/R.txt | head -6 | tr '\n' ' ')"
echo "### DONE"
