# AMR robot commands — cheat sheet (PC + Pi)

All the commands we use to drive/test the real robot. See also
[docs/software/navigation.md](../docs/software/navigation.md) and the `amr-pi-ros-commands` memory.

## Environment (source in EVERY terminal)
**Ubuntu PC** *(default FastDDS/domain 42 → doesn't see the robot, these exports are REQUIRED)*:
```bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
```
**Pi** (non-interactive SSH does not source ROS) — prefix the same way + the desired workspaces:
```bash
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
# +for Nav2 : source ~/camera_ws/install/setup.bash ; source ~/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ; export ROS_DOMAIN_ID=0
```
SSH: `ssh botshare@172.17.201.29` (key OK, no password).

## Power
- **Mains without battery** (recommended for testing): the 24 V AC/DC brick and the battery are in
  parallel → the robot runs directly off mains (on a leash). 24 V stiff = no "low battery" variable.
  Drive slowly (no reserve → the supply may trip on peaks).
- **Battery**: aim for **≥ 25 V at rest** before any nav test (≤ 23.5 V = too low, soft torque → collides).
- ⚠️ A Pi reboot **clears `/tmp`** → recopy the scripts (`scp scripts/*.sh botshare@…:/tmp/`).

## Launch the full Nav2 STACK (on the Pi)
```bash
scp scripts/bringall.sh botshare@172.17.201.29:/tmp/                 # from the PC, once
ssh botshare@172.17.201.29 'nohup setsid bash /tmp/bringall.sh >/dev/null 2>&1 </dev/null &'
ssh botshare@172.17.201.29 'for i in $(seq 1 24); do grep -q "### UP" /tmp/bringall.log && break; sleep 4; done; cat /tmp/bringall.log'
```
→ bring-up (agent+lidar+EKF+filter+camera+TF) + AMCL on `~/maps/coin_ok.yaml` + Nav2 + goal_relay.

## RViz (on the PC)
```bash
# ready Nav2 config (map, costmaps, scan, global+local paths, footprint=robot, 2D Pose/Goal tools) :
source /opt/ros/jazzy/setup.bash && export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && export ROS_DOMAIN_ID=0 && rviz2 -d /home/matthieu/Documents/openamr/scripts/openamr_nav.rviz
# (separate SLAM config : scripts/openamr_slam.rviz)
```
Fixed Frame=`map`. Shown automatically: Map `/map`, local+global Costmap, LaserScan `/scan_filtered` (Best
Effort), Path `/plan` (red) + `/local_plan` (cyan), Polygon `/local_costmap/published_footprint`
(**= the robot**, magenta). Tools: **2D Pose Estimate** (localize, DO THIS FIRST) → **2D Goal Pose**
(goal; NOT "Nav2 Goal"). Optional 3D model = `robot_state_publisher` (risk of duplicate TF).

## Checks (bounded — NEVER run `ros2 topic hz` over SSH, it blocks)
```bash
ros2 node list
ros2 lifecycle get /controller_server          # active
ros2 topic echo /amcl_pose --once              # localized?
ros2 topic info /scan_filtered                 # publisher count == 1
# costmaps NOT empty (otherwise blind robot, cf gotcha #8) :
ros2 topic echo /global_costmap/costmap --field data --once | tr ',' '\n' | grep -vE '^0$|^-1$|^$' | wc -l
ros2 topic echo /local_costmap/costmap  --field data --once | tr ',' '\n' | grep -vE '^0$|^-1$|^$' | wc -l
ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap "{}"
```

## Live Nav2 tuning (local + global)
```bash
ros2 param set /local_costmap/local_costmap inflation_layer.inflation_radius 0.20
ros2 param set /controller_server FollowPath.max_vel_x 0.16
# footprint enlarged +12cm (hard avoidance margin) :
ros2 param set /local_costmap/local_costmap footprint "[[0.535,0.31],[0.535,-0.31],[0.435,-0.41],[-0.385,-0.41],[-0.485,-0.31],[-0.485,0.31],[-0.385,0.41],[0.435,0.41]]"
```

## Motor / encoder tests (scripts in `scripts/`, scp to /tmp then launch detached)
- **`agentup.sh`** — starts the agent alone (checks the Teensy, **does not move**).
- **`wtest.sh`** — wheels **IN THE AIR**: openloop 300 on both wheels, counts L/R rpm (left faux-contact?).
- **`gtest.sh`** — **ON THE GROUND**, clear space ahead: drives 0.10 m/s 4 s, measures odom displacement + L/R.
- Launch: `ssh … 'nohup setsid bash /tmp/XXX.sh >/dev/null 2>&1 </dev/null &'` then read `/tmp/XXX.log`.

### Direct firmware debug (without Nav2)
```bash
# openloop : x = left PWM, y = right PWM (-1023..1023), publish continuously (200ms watchdog) :
ros2 topic pub -r 10 /debug/openloop geometry_msgs/msg/Vector3 "{x: 200.0, y: 200.0, z: 0.0}"
# wheel rpm (BEST_EFFORT) : x=target, y=measured, z=counts :
ros2 topic echo /debug/left  --qos-reliability best_effort
ros2 topic echo /debug/right --qos-reliability best_effort
# closed-loop drive :
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.10}, angular: {z: 0.0}}"
```

## Maps
```bash
# save the current map (on the Pi) :
ros2 run nav2_map_server map_saver_cli -f ~/maps/NOM --ros-args -p save_map_timeout:=20.0
```
Maps: `~/maps/coin_ok.*` (good, 2026-06-20), `coin2.*` (+ `.bak`).

## Gotchas (summary — details in navigation.md)
- **2D Pose Estimate BEFORE anything** otherwise empty costmaps → blind robot.
- Duplicate scan filter removed from the launch; **"2D Goal Pose"** + goal_relay (not "Nav2 Goal").
- `pkill` always with the bracket trick: `pkill -f "[m]icro_ros_agent"`.
- No `topic hz` over SSH. Pi reboot = `/tmp` cleared.
