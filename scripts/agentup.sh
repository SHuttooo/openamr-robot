#!/bin/bash
# Start ONLY the micro-ROS agent (verifies the Teensy talks; moves nothing).
# Run on the Pi, detached: nohup setsid bash /tmp/agentup.sh >/dev/null 2>&1 </dev/null &
# Expected topics after: /debug/*, /odom/unfiltered, /imu/data, /cmd_vel
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
exec > /tmp/agentup.log 2>&1
pkill -9 -f "[m]icro_ros_agent"; sleep 1
nohup ros2 run micro_ros_agent micro_ros_agent serial -b 115200 \
  -D /dev/serial/by-id/usb-Teensyduino_USB_Serial_16778200-if00 > /tmp/agent.log 2>&1 &
sleep 10
echo "### topics:"; ros2 topic list | grep -E "debug|odom|imu|cmd_vel" | sort
echo "### UP"
sleep 3600
