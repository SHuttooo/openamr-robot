#!/bin/bash
# Cleanly stops the current navigation (cancels the navigate_to_pose goal).
# The robot stops and navigation stays ACTIVE (ready for a new goal), unlike
# the "Pause" button on the Nav2 panel which pauses the whole lifecycle.
#
#   bash ~/Documents/openamr/scripts/stop.sh
#
# Tip: create an alias in ~/.bashrc ->  alias stop='bash ~/Documents/openamr/scripts/stop.sh'
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
echo "Cancelling the current goal..."
# empty uuid + stamp => cancels ALL active goals
ros2 service call /navigate_to_pose/_action/cancel_goal action_msgs/srv/CancelGoal "{}" \
  2>/dev/null | grep -q "return_code=0" && echo "OK: robot stopped, nav still active." \
  || echo "No goal to cancel (or nav not running)."
