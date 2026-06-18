# Navigation (OpenAMR / Nav2) — plan

*Last updated: 2026-06-18.*

> **Status: SLAM works.** `slam_toolbox` (online_async) runs on `/scan_filtered` and builds/saves maps
> (first map `~/maps/coin1.{pgm,yaml}` + serialized `coin1.{posegraph,data}`). Odometry is now EKF-fused.
> Remaining for full autonomy: AMCL localization + Nav2 (`openamr-platform-sw` now built on the Pi).

## The package: `openamr-platform-sw`
Cloned at `~/openamr-platform-sw`, **built on the Pi** (2026-06-18). ROS 2 packages (`ros2/src/`): ROS 2 packages (`ros2/src/`):

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
| `/odom` + TF `odom→base_link` | ✅ **EKF-fused** (wheels + IMU yaw rate) — done 2026-06-18 |
| `/imu/data` | ✅ (real MPU6500, gyro Z fused) |
| `/scan` (frame `lidar_link`) | ✅ |
| TF `base_link→lidar_link` | ✅ measured (x=0.335, z=0.18, yaw=180°) |
| `/scan_filtered` (body filter) | ✅ **done** (`scan_body_filter.py`, angular + range mask) |
| `map→odom` (SLAM) | ✅ **done** (`slam_toolbox` on `/scan_filtered`; map saved) |
| camera `/camera/image_raw` (+ TF) | ✅ **done** (IMX708 via RPi libcamera fork; uncalibrated) |
| robot_state_publisher + URDF (full TF, joint_states) | ⏳ |
| AMCL localization (re-use saved map) | ⏳ |
| Nav2 stack (`openamr-platform-sw`) | ✅ built on Pi (config/launch TODO) |
| camera **calibration** (for AprilTag/docking) | ⏳ |

## SLAM — how we run it (working)
```bash
# on the Pi, after the bring-up is up (provides /scan_filtered + TF odom→base_link)
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=false \
  slam_params_file:=/home/botshare/slam_params.yaml
```
`~/slam_params.yaml`: mode mapping, `scan_topic:=/scan_filtered`, `base_frame:=base_link`,
`min_laser_range:=0.35`, `max_laser_range:=10`, `minimum_travel 0.2`. Then **drive SLOWLY** with teleop
(0.1 m/s, gentle turns, no in-place spins, close the loop by returning to start).

**Save the map:**
```bash
mkdir -p ~/maps && cd ~/maps
ros2 run nav2_map_server map_saver_cli -f coin1 -p save_map_timeout:=15.0      # coin1.pgm + coin1.yaml
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
  "{filename: '/home/botshare/maps/coin1'}"                                    # coin1.posegraph + .data
```
**Reload a saved map** (deserialize, e.g. to continue or for localization):
```bash
ros2 service call /slam_toolbox/deserialize_map slam_toolbox/srv/DeserializePoseGraph \
  "{filename: '/home/botshare/maps/coin1', match_type: 1}"
```
> ⚠️ SLAM quality caveats: the LiDAR is low-res (~270 pts/rev) and the map is sparse — **drive slowly**.
> Fast driving / in-place spins cause the scan-matcher to lose tracking and the map to drift. Reloading a
> sparse map and continuing relocalizes poorly; for a clean result, prefer a fresh slow mapping pass.

## Remaining order (incremental, validate each step)
1. ✅ **Install + build**: slam_toolbox, nav2-map-server, robot_localization done. `openamr-platform-sw`
   cloned (`~/openamr-platform-sw`), **not built yet**.
2. **TF & description**: `robot_state_publisher` with the OpenAMR URDF (adjust to Ø0.2/0.45, real mounts).
3. ✅ **Scan filter** → `/scan_filtered` (done).
4. ✅ **SLAM** → map built & saved (done).
5. ✅ **EKF** (IMU fused into `/odom`) (done).
6. **Localization + Nav2**: AMCL with the saved map, then the navigation launch; send goals in RViz.
7. **Docking** (later): needs the camera (✅ streaming) + **calibration** + AprilTags.

## Docking (real robot) — plan & status

The `openamrobot_docking` package works in **simulation** (Gazebo + Nav2 + AprilTag; validated by the
author). Porting it to the **real robot** is a multi-step effort.

**Status 2026-06-18:**
- ✅ `openamr-platform-sw` **built on the Pi** (`~/openamr-platform-sw/ros2`, packages `description`,
  `nav2`, `gazebo`, `docking`). To build docking, `openamrobot_gazebo` must be built too (build-order dep)
  even though gazebo's `ros_gz` runtime deps aren't on the headless Pi.
- ✅ Full stack installed on the Pi: `ros-jazzy-navigation2`, `nav2-bringup`, `apriltag-ros`, `image-proc`,
  `rmw-cyclonedds-cpp`, `laser-filters`, `joint-state-publisher`.

**How the docking works (from the sim):** `apriltag_ros` detects a 3-tag 36h11 bundle (IDs 0/1/2) on
`/rgb_image` + `camera_info` → TF per tag; `detected_dock_pose_publisher` → `/detected_dock_pose` (centre
tag); `dock_trigger.py` waits on `/dock_trigger` → `NavigateToPose` to a staging zone, then approaches.

**⚠️ Hard requirements for real docking (gaps):**
1. **Camera calibration** (checkerboard) → real intrinsics + `image_proc` rectification (AprilTag needs it).
2. **A physical AprilTag dock** — print 3× 36h11 tags (IDs 0/1/2), measure size, config.
3. **Nav2 + AMCL on a real SLAM map** (the foundation — docking is NavigateToPose + approach).
4. ✅ **CycloneDDS across the WHOLE stack** — DONE 2026-06-18 (`dock_trigger.py` crashes on Fast DDS for
   Nav2 action goals). Bring-up + dev PC now run Cyclone (Pi `~/.bashrc` exports it).
5. **robot_state_publisher + URDF** (openamrobot_description, geometry Ø0.2/0.45) for the Nav2 footprint.
6. **Topic remaps**: our camera is `/camera/image_raw`; docking expects `/rgb_image` + synced `camera_info`.
   Our `/scan_filtered` (scan_body_filter.py) can replace the package's `laser_filters` chain.

**⚠️ Isolation gotcha (learned):** running the docking **sim** on the **same `ROS_DOMAIN_ID` (0)** as the
real robot makes them interfere — the real robot's base_link TF (wall-time) collides with the sim's
(sim-time) → `TF_OLD_DATA` flood → `NavigateToPose` aborts. Run the sim on a **separate domain** (e.g. 5).

**Suggested order:** (1) Nav2 real: CycloneDDS + URDF + real map + AMCL → validate a `NavigateToPose`;
(2) camera calibration + AprilTag detection on the real camera; (3) docking trigger end-to-end.

## Reference
The provided guide `~/openamr_hardware_bringup_guide/README_OPENAMR_HARDWARE_BRINGUP.md` documents the
contract, the safety limits (max 0.05 m/s to start), the calibration procedures, and the SLAM→Nav2→docking
flow in detail. The docking package's own docs are excellent: `~/openamr-platform-sw/ros2/src/openamrobot_docking/docs/`
(quickstart, apriltag, camera_calibration, tf_frames, troubleshooting…).
