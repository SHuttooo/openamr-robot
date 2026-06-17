# Real-hardware bring-up

*Last updated: 2026-06-17.*

## One command
Everything needed for the hardware base starts from a single launch file on the Pi:

```bash
# in an interactive SSH shell (ROS already sourced via ~/.bashrc)
ros2 launch /home/botshare/openamr_real_bringup.launch.py
```

## What it starts
| Node | Provides |
|---|---|
| micro-ROS agent (Teensy) | `/cmd_vel`, `/odom/unfiltered`, `/imu/data`, `/debug/*` |
| `rplidar_composition` (Standard, 115200, frame `lidar_link`) | `/scan` |
| `odom_tf_relay` (`~/odom_tf_relay.py`) | `/odom` + TF `odom→base_link` |
| `static_transform_publisher` | TF `base_link→lidar_link` (placeholder offset) |

Result — the ROS "contract" needed by Nav2 (minus `map→odom` and `/scan_filtered`):
```
/cmd_vel  /odom  /imu/data  /scan     +  TF: odom → base_link → lidar_link
```

## Verify it's up
```bash
ros2 topic list | grep -E 'scan|/odom|imu|cmd_vel'
ros2 topic hz /scan          # ~7 Hz
ros2 run tf2_ros tf2_echo odom lidar_link
```

## LiDAR mount (measured)
TF `base_link→lidar_link` = **x=0.335, y=0, z=0.18, yaw=π (180°)**. The LiDAR is 33.5 cm in front of the
wheel axle, centered, and **mounted rotated 180°** (its 0° points to the rear; the robot front = the
LiDAR's 180°). Found empirically (object in front shows at ±180° in the LiDAR frame).

## Things still to refine
- Configure the `scan_body_filter` (in `openamrobot_nav2`): the robot's own frame/structure produces
  close returns in several directions (±20–50°, ±80–90° in the LiDAR frame) → mask them, and produce
  `/scan_filtered`.
- Odometry is wheel-only; plan to add an EKF fusing the IMU (see [ros-architecture.md](ros-architecture.md)).

## Gotchas
- The launch makes the LiDAR node `respawn` on failure. ⚠️ But if the LiDAR is in a **stuck** state
  (from a previous brutal kill), respawn just hammers it — **unplug/replug the LiDAR USB** to reset, then
  relaunch once. See [../hardware/lidar.md](../hardware/lidar.md).
- If `/cmd_vel`/`/odom` topics don't appear: the Teensy didn't connect (check baud 115200, the LED, the
  USB device path).

## Source of the launch file
`~/openamr_real_bringup.launch.py` (also mirrored in the dev repo under `projet/openamr/`). It is a plain
ROS 2 Python launch combining `ExecuteProcess` (agent, relay) and `Node` (rplidar, static TF).
