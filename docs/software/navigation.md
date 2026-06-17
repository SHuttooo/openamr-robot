# Navigation (OpenAMR / Nav2) — plan

*Last updated: 2026-06-17.*

> **Status: not started yet.** This sheet is the plan to bring the OpenAMR navigation onto the real robot.

## The package: `openamr-platform-sw`
Cloned at `~/openamr-platform-sw` (not built yet). ROS 2 packages (`ros2/src/`):

| Package | Role |
|---|---|
| `openamrobot_description` | URDF (`robo_urdf.urdf.xacro`): frames `base_link`, `lidar_link`, `camera_link`, wheels |
| `openamrobot_gazebo` | Gazebo simulation |
| `openamrobot_nav2` | Nav2 config (`nav2_params.yaml`), SLAM, localization, navigation launches, scan filter |
| `openamrobot_docking` | AprilTag docking + the sim bring-up |

There is **no hardware/bridge package** — the real robot must provide the same ROS interface the sim
provides, then the **same** Nav2 runs with `use_sim_time:=false`.

## The contract Nav2 expects (read from `nav2_params.yaml`)
- Frames: **`map → odom → base_link`** (+ sensors). AMCL/Nav2 use `base_link`, `odom`, `map`.
- Topics it consumes: **`/odom`** and **`/scan_filtered`** (Nav2's body filter turns `/scan` → `/scan_filtered`).
- Topic it publishes: **`/cmd_vel`**.

## What we already provide (real bring-up) vs what's missing
| Need | Status |
|---|---|
| `/cmd_vel` (to Teensy) | ✅ |
| `/odom` + TF `odom→base_link` | ✅ (wheel-only; EKF upgrade planned) |
| `/imu/data` | ✅ (real MPU6500) |
| `/scan` (frame `lidar_link`) | ✅ |
| TF `base_link→lidar_link` | ✅ (placeholder offset — **measure it**) |
| robot_state_publisher + URDF (full TF, joint_states) | ⏳ |
| `/scan_filtered` (body filter) | ⏳ |
| `map→odom` (SLAM then AMCL) | ⏳ |
| `/rgb_image` (camera) | ⏳ |

## Suggested order (incremental, validate each step)
1. **Install + build**: `ros-jazzy-navigation2`/`nav2-bringup`, `ros-jazzy-slam-toolbox`,
   `ros-jazzy-robot-localization`; build `openamr-platform-sw` (sequential, it's a 4 GB Pi).
2. **TF & description**: `robot_state_publisher` with the OpenAMR URDF (adjust wheel geometry to
   Ø0.2/0.45 and the real LiDAR mount).
3. **Scan filter**: configure `scan_body_filter` for the ~170° usable FOV → `/scan_filtered`.
4. **SLAM**: run `slam_toolbox` (`use_sim_time:=false`), drive with teleop → build & save a map.
5. **Localization + Nav2**: AMCL with the saved map, then the navigation launch; send goals in RViz.
6. **(Optional) EKF**: fuse IMU into `/odom` (less drift) before relying on long trajectories.
7. **Docking** (later): needs the camera + calibration + AprilTags.

## Reference
The provided guide `~/openamr_hardware_bringup_guide/README_OPENAMR_HARDWARE_BRINGUP.md` documents the
contract, the safety limits (max 0.05 m/s to start), the calibration procedures, and the SLAM→Nav2→docking
flow in detail.
