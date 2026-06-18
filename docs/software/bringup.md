# Real-hardware bring-up

*Last updated: 2026-06-18.*

## One command
Everything needed for the hardware base starts from a single launch file on the Pi. **Source the camera
overlay too** (it provides the RPi libcamera + `camera_ros`):

```bash
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash          # RPi libcamera fork + camera_ros (see hardware/camera.md)
ros2 launch /home/botshare/openamr_real_bringup.launch.py
```
(An interactive SSH shell sources the first two automatically via `~/.bashrc`; add the camera one.)

## What it starts
| Node | Provides |
|---|---|
| micro-ROS agent (Teensy) | `/cmd_vel`, `/odom/unfiltered`, `/imu/data`, `/debug/*` |
| `rplidar_composition` (Standard, 115200, frame `lidar_link`) | `/scan` |
| `scan_body_filter` (`~/scan_body_filter.py`) | `/scan_filtered` (robot body masked) |
| **`ekf_node`** (`robot_localization`, `~/ekf.yaml`) | `/odom` + TF `odom→base_link` (wheels + IMU gyro Z) |
| `camera_node` (`camera_ros`) | `/camera/image_raw`, `/camera/camera_info` |
| `static_transform_publisher` ×4 | TF `base_link→{lidar_link, imu_link, base_footprint, camera_link→camera_optical_frame}` |

Result — the full ROS "contract" for Nav2 (we now also provide `map→odom` once SLAM runs, and
`/scan_filtered`):
```
/cmd_vel  /odom  /imu/data  /scan  /scan_filtered  /camera/image_raw
TF: (map →) odom → base_link → {lidar_link, imu_link, camera_link → camera_optical_frame}
```

## Verify it's up (from the Ubuntu dev PC, ROS_DOMAIN_ID=0)
```bash
ros2 topic list | grep -E 'scan|/odom|imu|cmd_vel|camera'
ros2 topic echo /scan_filtered --once --qos-reliability best_effort   # body-filtered scan
ros2 run tf2_ros tf2_echo odom base_link                              # from the EKF
ros2 topic echo /camera/image_raw --once | grep -E 'width|encoding'   # 1280x720 bgr8
```

## Odometry — now fused (EKF), no longer wheel-only
The old `odom_tf_relay` is **replaced** by a `robot_localization` **EKF** (`~/ekf.yaml`) that fuses the
wheel odometry (`/odom/unfiltered`: `vx` + `vyaw`) with the IMU **gyro Z only** (`/imu/data`
`angular_velocity.z`). The IMU orientation is invalid (zero quaternion) and its accel is tilted, so they
are **not** used. `two_d_mode: true`. Output: `/odom` (remapped from `odometry/filtered`) + TF
`odom→base_link`. Result: much less heading drift in turns. See [ros-architecture.md](ros-architecture.md).

The EKF needs the `/odom/unfiltered` child frame (`base_footprint`) and the IMU frame (`imu_link`) in TF,
hence the two extra identity static TFs in the launch.

## LiDAR scan filter (`/scan_filtered`)
The LiDAR sees the robot's own chassis. `scan_body_filter.py` republishes `/scan` → `/scan_filtered`,
masking (in the LiDAR frame; LiDAR is mounted rotated 180°, so 0° = robot rear):
- **rear shell** (−45°…+49°): masked at **all distances** (the shell blocks the view; e.g. a 0.72 m
  return dead-centre is the shell, not a wall).
- **side posts** (±73°…±96°): masked **only < 0.40 m** (thin posts) → real walls farther out are kept.

Measured 2026-06-18 (robot body ≤ 0.30 m, first real wall ≥ 0.63 m). SLAM consumes `/scan_filtered`.
Edit the sector lists at the top of `scan_body_filter.py` to refine.

## LiDAR mount (measured)
TF `base_link→lidar_link` = **x=0.335, y=0, z=0.18, yaw=π (180°)**. 33.5 cm in front of the wheel axle,
centered, **mounted rotated 180°** (its 0° points to the rear; robot front = LiDAR 180°).

## Gotchas
- **`pkill` self-match**: `pkill -f scan_body_filter` (or `micro_ros_agent`, `slam_toolbox`) matches its
  OWN command line and kills the SSH session (exit 255). Use the bracket trick: `pkill -f "[s]can_body_filter.py"`.
- LiDAR node `respawn`s on failure. If the LiDAR is **stuck** (`80008000` after a brutal kill), respawn
  just hammers it — power-cycle / unplug-replug the LiDAR USB, relaunch once. A battery power-cycle also
  resets it cleanly. See [../hardware/lidar.md](../hardware/lidar.md).
- LiDAR sometimes goes silent (node alive, `/scan` mute) → `pkill -f "[r]plidar_composition"`, respawn brings it back.
- No topics from the Teensy → agent didn't connect (baud 115200, LED, USB path).
- Camera "no cameras available" → you didn't source `~/camera_ws` (RPi libcamera). See [../hardware/camera.md](../hardware/camera.md).

## Source of the launch file
`~/openamr_real_bringup.launch.py` (mirrored in the dev repo at `launch/`). Plain ROS 2 Python launch
combining `ExecuteProcess` (agent, scan filter) and `Node` (rplidar, ekf, camera, static TFs).
Config files: `~/ekf.yaml`, `~/scan_body_filter.py`, `~/slam_params.yaml` (mirrored in `scripts/`).
