# Navigation (OpenAMR / Nav2)

*Last updated: 2026-06-19.*

> **Status: SLAM + Nav2 + AMCL WORK on the real robot (2026-06-19).** The robot localizes (AMCL on the
> saved map `coin2`) and navigates autonomously to goals (global plan + DWB controller + real-time obstacle
> avoidance). Full bring-up procedure, the exact launch commands, and the **many gotchas we hit** are in
> the section **"Nav2 + AMCL on the real robot"** below. Read it before relaunching — several non-obvious
> traps (duplicate scan filter, teleop/cmd_vel conflict, the RViz goal tool, lidar replug) will waste hours
> otherwise.

## ⚡ Quick reference — full autonomous-nav bring-up
On the Pi (one clean sequence; see details + troubleshooting below):
```bash
# 0. everything sourced: /opt/ros/jazzy + linorobot2_ws + camera_ws + openamr-platform-sw/ros2/install + Cyclone
# 1. base bring-up (agent, lidar, scan filter, EKF, camera, static TFs)
ros2 launch /home/botshare/openamr_real_bringup.launch.py
# 2. localization (map_server + AMCL on the saved map)
ros2 launch openamrobot_nav2 localization_launch.py map:=/home/botshare/maps/coin2.yaml use_sim_time:=false
# 3. navigation (planner, controller, bt_navigator, ...). The controller now outputs /cmd_vel_raw
#    (remapped) and the duplicate scan filter was REMOVED from this launch (no more pkill needed).
ros2 launch openamrobot_nav2 navigation_launch.py use_sim_time:=false
# 4. Collision Monitor (safety): /cmd_vel_raw -> [stop if footprint would hit] -> /cmd_vel
ros2 launch /home/botshare/collision_monitor_launch.py    # repo: launch/collision_monitor_launch.py
# 5. goal relay: RViz "2D Goal Pose" (/goal_pose) -> NavigateToPose action (see gotcha #3)
python3 ~/goal_relay.py   # repo: scripts/goal_relay.py
```
Then in RViz (dev PC): **2D Pose Estimate** (localize) → **2D Goal Pose** (navigate). **Not** "Nav2 Goal".
> cmd_vel chain: `controller_server → /cmd_vel_raw → collision_monitor → /cmd_vel → Teensy`. The
> Collision Monitor (`FootprintApproach`, source `/scan_filtered`) projects the real 78×58 footprint
> forward and **stops the robot before any part touches** an obstacle (the hard "never touch the violet").

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
| robot_state_publisher + URDF (full TF, joint_states) | ⏳ (static TFs used instead; would conflict with rsp) |
| AMCL localization (re-use saved map) | ✅ **done** (on `coin2`; publishes `map→odom`) — 2026-06-19 |
| Nav2 stack (`openamr-platform-sw`) | ✅ **WORKING** (localization + navigation launches, real footprint) — 2026-06-19 |
| Real robot **footprint** (0.78×0.58, rounded, base_link offset) | ✅ set in `nav2_params.yaml` |
| `/goal_pose` → `navigate_to_pose` relay (`goal_relay.py`) | ✅ (needed: use "2D Goal Pose" in RViz) |
| camera **calibration** (for AprilTag/docking) | ✅ done 2026-06-19 (see [hardware/camera.md](../hardware/camera.md)) |
| Collision Monitor / footprint padding (hard "never touch") | ⏳ next |

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

> Maps: `coin1` (first pass) and **`coin2`** (current, used for Nav2) are in `~/maps/` on the Pi and
> mirrored in this repo's `maps/`.

## Remaining order (incremental, validate each step)
1. ✅ **Install + build** `openamr-platform-sw` (done).
2. ⏳ **TF & description**: `robot_state_publisher` + URDF — *not used*; the bring-up's static TFs cover the
   tree, and rsp with the sim URDF would conflict. The real **footprint** is set directly in nav2_params.
3. ✅ **Scan filter** → `/scan_filtered` (done).
4. ✅ **SLAM** → map built & saved (`coin2`) (done).
5. ✅ **EKF** (IMU fused into `/odom`) (done).
6. ✅ **Localization + Nav2**: AMCL on `coin2` + navigation; goals via RViz "2D Goal Pose" + `goal_relay.py`
   (done — see "Nav2 + AMCL on the real robot").
7. ⏳ **Hard collision avoidance**: Collision Monitor or footprint padding (so the footprint never touches).
8. ⏳ **Docking**: camera ✅ calibrated; needs AprilTags + the docking pipeline.

## Nav2 + AMCL on the real robot (WORKING — 2026-06-19)

The standard nav2_bringup launches (copied into `openamrobot_nav2`) run on the real robot with
`use_sim_time:=false`. `nav2_params.yaml` was already wired for our topics/frames (`/scan_filtered`,
`/odom`, `/cmd_vel`, `map/odom/base_link`). What we changed/learned to make it actually work:

### Robot footprint (CRITICAL — was wrong)
The default config used `robot_radius: 0.22` (a 0.44 m circle). The **real robot is a 0.78 × 0.58 m
rectangle with rounded corners**, and `base_link` (wheel axle) is **not centered**: the **front is 0.415 m**
ahead of base_link (lidar at x=0.335 + 8 cm to the front edge), the **rear is −0.365 m**. With the
too-small circle, Nav2 planned paths too tight and the robot **clipped obstacles**. The correct footprint
(octagon ≈ rounded rectangle) is now set in both costmaps:
```yaml
footprint: "[[0.415, 0.19], [0.415, -0.19], [0.315, -0.29], [-0.265, -0.29], [-0.365, -0.19], [-0.365, 0.19], [-0.265, 0.29], [0.315, 0.29]]"
```

### Planner / controller / costmap (current real-robot tuning)
- **Planner**: `SmacPlanner2D` (NavFn also works and is faster; Smac warns it is slow with a non-circular
  footprint + small inflation — see gotcha #6).
- **Controller**: **DWB** (`max_vel_x 0.16`, `max_vel_theta 0.7`, `acc_lim_x 0.3`). DWB *weaves* a bit
  ("drunk") on diff-drive. We tried **Regulated Pure Pursuit** but it got **stuck rotating in place**
  (`rotate_to_heading` never converged; with it off, it drove but couldn't satisfy the yaw goal) → reverted
  to DWB, which reliably reaches goals. (To reduce DWB weave later: raise PathAlign/PathDist, lower
  vtheta_samples — without breaking what works.)
- **Costmap**: `inflation_radius` ≈ 0.15 (soft planning margin; tune to taste), `obstacle_min_range: 0.10`
  (see gotcha #5), goal checker `xy_goal_tolerance 0.35`.
- **`config/nav2_params_real.yaml`** in this repo is a snapshot of the working config (the live file is
  `~/openamr-platform-sw/ros2/src/openamrobot_nav2/config/nav2_params.yaml`).
- Most of these are **dynamically settable** without a restart, e.g.:
  `ros2 param set /controller_server FollowPath.max_vel_x 0.2`,
  `ros2 param set /local_costmap/local_costmap inflation_layer.inflation_radius 0.15`,
  `ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap "{}"`.

### Inflation vs reactive collision avoidance (important concept)
- **Inflation** (the blue halo) is a *soft planning cost* — the planner prefers to avoid it but the robot
  *can* traverse it. It does NOT, by itself, stop the robot from touching things.
- **Not touching obstacles** comes from the **controller checking the real footprint** against the **local
  costmap** in real time (which needs `obstacle_min_range` small enough to see close obstacles — #5).
- For a HARD "never touch" guarantee: ✅ **DONE — the Collision Monitor is active** (Option B). It sits in
  the cmd_vel chain (`controller → /cmd_vel_raw → collision_monitor → /cmd_vel`), uses a `FootprintApproach`
  zone on the **real footprint** + `/scan_filtered`, and **stops the robot before any part touches** an
  obstacle — independent of inflation (which is now low, 0.10, just for planning). Launch:
  `ros2 launch /home/botshare/collision_monitor_launch.py` (config in `nav2_params.yaml` `collision_monitor:`,
  `time_before_collision: 0.8`). Alternative not used: (A) padding the footprint.

### Gotchas we hit (read these!)
1. **Process duplicates from repeated launches** → multiple agents/lidars/EKFs fighting (serial/USB/TF
   conflicts → everything flaky). Always do a **clean kill + single launch**. Symptom: `pgrep` shows 2-3 of
   a node (note: `ros2 run` adds a wrapper process, so pgrep over-counts by 1 — check `ps -ef` to be sure).
2. **Duplicate `/scan_filtered`** (FIXED): `navigation_launch.py` used to start its OWN `laser_filters`
   scan filter (`scan_to_scan_filter_chain`) that conflicted with the bring-up's `scan_body_filter.py`
   → 2 publishers → bad obstacle data. **Now removed from `navigation_launch.py`** (permanent). If you ever
   see 2 publishers on `/scan_filtered` again: `pkill -9 -f scan_to_scan_filter_chain`.
3. **RViz "Nav2 Goal" does nothing**; use **"2D Goal Pose"**. The `nav2_rviz_plugins/GoalTool` needs the
   Navigation2 panel to forward the goal; without it, it publishes nothing usable. The default **"2D Goal
   Pose"** publishes `/goal_pose`, which our **`goal_relay.py`** node forwards to the `navigate_to_pose`
   action. So: run `goal_relay.py` + use "2D Goal Pose".
4. **Teleop conflict**: a running `teleop_twist_keyboard` (with `repeat_rate`) floods `/cmd_vel` with its
   last (often 0) command at 10 Hz → it **overrides Nav2** → robot won't move. **Kill teleop before Nav2.**
5. **`obstacle_min_range` too high blinds close obstacles**: it was `0.35` → obstacles within 0.35 m of the
   lidar were dropped, so they **vanished from the costmap as the robot approached → it drove into them**.
   Set **`obstacle_min_range: 0.10`** (the `scan_body_filter.py` already removes the robot's own body, so a
   small min range is safe).
6. **SmacPlanner2D slow with a non-circular footprint + small inflation** (it warns explicitly). If
   planning is sluggish, switch to **NavFn** (`nav2_navfn_planner::NavfnPlanner`) — much faster — or raise
   inflation. ⚠️ NavFn treats the robot as a point, so it needs inflation ≈ the robot's inscribed radius
   (~0.29) to plan feasible paths for this big robot.
7. **"Failed to make progress"** = the controller isn't translating (it aborts after 30 s). We saw it with
   RPP stuck rotating, and when paths were infeasible (too-low inflation for the big robot). Check the robot
   actually moves (`/cmd_vel` non-zero linear), and that inflation/footprint give feasible paths.

### Verify it's healthy
```bash
ros2 lifecycle get /amcl                 # active
ros2 lifecycle get /controller_server    # active
ros2 run tf2_ros tf2_echo map odom       # AMCL publishes map->odom (after a 2D Pose Estimate)
ros2 topic info /scan_filtered           # publisher count == 1 (else kill the dup filter)
ros2 topic hz /local_costmap/costmap     # local costmap updating
```

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
