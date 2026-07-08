# Architecture & audit — OpenAMR project

> **Single reference document.** Describes the entire project structure (both repositories +
> the firmware), how the pieces connect, and the audit of duplicates / inconsistencies /
> items to fix. Updated **2026-06-26**. This is THE block that explains the whole;
> the other docs (`docs/hardware/`, `docs/software/`, `docs/procedures/`) are its details.

---

## 0. Overview in 30 seconds

An autonomous mobile robot (AMR) with differential drive. **Two brains**:

- **Teensy 4.0** (real-time firmware, 50 Hz) — reads the encoders + the IMU, controls the motors (PID), talks **micro-ROS** over USB serial.
- **Raspberry Pi 5** (ROS 2 Jazzy) — perception (lidar, camera), localization + navigation (**Nav2**), docking (**docking** AprilTag).

**Central design principle:** the **same** Nav2 stack and the **same** `nav2_params.yaml` run in **simulation** (Gazebo) and on the **real robot**. Only the **data source** and the **clock** (`use_sim_time`) change. This is what makes sim→real transparent.

**Three code sets:**

| Set | Path | Role | Deployed where |
|---|---|---|---|
| **Platform** (`openamr-platform-sw`) | `~/Documents/openAMRobot/openamr-platform-sw` | The ROS 2 packages (Nav2, Gazebo, docking, drivers, perception, description) | PC (dev) + Pi (colcon build) |
| **Instance** (`openamr`, THIS repo) | `~/Documents/openamr` | Docs, field scripts, configs/maps specific to THIS robot | PC + Pi (scripts) |
| **Firmware** (`linorobot2_hardware`) | `~/linorobot2_hardware` (on the Pi) | Upstream Teensy firmware + our `lino_base_config.h` overlay | Teensy (flashed) |

---

## 1. Platform repository — `openamr-platform-sw`

The ROS 2 monorepo under `ros2/src/`. **8 packages** (7 active + 1 empty).

### 1.1 Package map

| Package | Build | Role |
|---|---|---|
| **openamrobot_bringup** | ament_python | Top-level composer. `bringup.launch.py` = THE single entry point (sim/real selector). |
| **openamrobot_nav2** | ament_python | Nav2 stack: localization (AMCL), navigation (planner/controller/BT), SLAM, configs. |
| **openamrobot_gazebo** | ament_python | Gazebo Harmonic simulation: world, ros↔gz bridge, robot_state_publisher. |
| **openamrobot_docking** | ament_cmake | AprilTag docking (bundle of 3 tags 36h11). Sim + real. C++ (`detected_dock_pose_publisher`) + Python (`dock_trigger.py`, `camera_info_sync.py`). |
| **openamrobot_drivers** | ament_python | Thin hardware layer: micro-ROS agent (Teensy) + RPLIDAR driver. |
| **openamrobot_perception** | ament_python | Lidar body filter (`scan_body_filter`) + real camera (`camera_ros`/IMX708). |
| **openamrobot_description** | ament_python | URDF/Xacro, STL meshes, Gazebo plugins, robot RViz view. |
| **openamrobot_control** | — | **EMPTY** (folder with no content). |

### 1.2 Dependencies between packages

```
openamrobot_bringup (top-level)
 ├─→ openamrobot_drivers      (real)
 ├─→ openamrobot_perception   (real)
 ├─→ openamrobot_nav2         (always)
 ├─→ robot_localization, tf2_ros, rviz2, topic_tools
 ├─→ openamrobot_gazebo       (optional, sim)
 └─→ openamrobot_docking      (optional, docking)

openamrobot_gazebo  ─→ openamrobot_description (URDF), ros_gz_sim, ros_gz_bridge
openamrobot_docking ─→ openamrobot_nav2 (nav2_msgs), apriltag_ros, ros_gz_bridge
openamrobot_nav2    ─→ nav2_* (bringup, amcl, planner, controller, bt, …), slam_toolbox, laser_filters
openamrobot_drivers ─→ micro_ros_agent, rplidar_ros
openamrobot_perception ─→ camera_ros, sensor_msgs
```

### 1.3 All launch files (18)

| File | Package | Role |
|---|---|---|
| **bringup.launch.py** | bringup | **Single entry point** sim/real (selector). |
| real_bringup.launch.py | bringup | Real data source (drivers + perception + EKF + static TFs). |
| goal_relay.launch.py | bringup | Simple goal forwarder `/goal_pose → /goal_pose_nav` (nav-only mode). |
| localization_launch.py | nav2 | map_server + AMCL + lifecycle. |
| navigation_launch.py | nav2 | controller + planner + smoother + behaviors + bt_navigator + lifecycle. |
| sim_bringup_launch.py | nav2 | Sim wrapper: localization + navigation + RViz (`use_sim_time` fixed to true). |
| online_async_launch.py | nav2 | slam_toolbox (live mapping). |
| gz_simulator.launch.py | gazebo | Gazebo + gz bridge + robot_state_publisher + robot spawn. |
| openamrobot_docking.launch.py | docking | **Sim** docking layer (camera_info bridge + sync + apriltag_sim + dock_pose + dock_trigger). |
| docking_real.launch.py | docking | **Real** docking layer (real apriltag + dock_pose + dock_trigger; no Gazebo). |
| bringup_sim.launch.py | docking | **Legacy**: 1-command sim (Gazebo + nav + docking via TimerActions). Kept for compat. |
| apriltag.launch.yml | docking | apriltag_node on `/camera/image_raw` (real camera). |
| apriltag_sim.launch.yml | docking | apriltag_node on `/rgb_image` (Gazebo camera). |
| detected_dock_pose_publisher.launch.py | docking | TF dock → `/detected_dock_pose`. |
| drivers.launch.py | drivers | micro-ROS agent + RPLIDAR. |
| camera.launch.py | perception | IMX708 camera (camera_ros). |
| scan_body_filter.launch.py | perception | `/scan` → `/scan_filtered` (real Python filter). |
| launch.py | description | Standalone robot visualizer (dev). |

### 1.4 Real inclusion graph (the single entry point)

```
bringup.launch.py  (args: sim, use_rviz, gui, use_camera, use_docking, map)
│
├─ [sim=true] ─ gz_simulator.launch.py
│              └─ FORWARDER (only one):
│                  ├─ use_docking=true  → openamrobot_docking.launch.py  (dock_trigger = forwarder)
│                  └─ use_docking=false → goal_relay.launch.py           (relay = forwarder)
│
├─ [sim=false] ─ real_bringup.launch.py
│               │   ├─ drivers.launch.py        (micro-ROS + RPLIDAR)
│               │   ├─ scan_body_filter.launch.py
│               │   ├─ camera.launch.py         (if use_camera)
│               │   ├─ ekf_node                 (robot_localization)
│               │   └─ static_transform_publisher ×4-5 (measured sensors)
│               └─ FORWARDER (only one):
│                   ├─ use_docking=true  → docking_real.launch.py        (dock_trigger = forwarder)
│                   └─ use_docking=false → goal_relay.launch.py          (relay = forwarder)
│
├─ localization_launch.py   (ALWAYS — map injected via temporary params)
├─ navigation_launch.py     (ALWAYS — remap bt_navigator goal_pose→goal_pose_nav)
└─ rviz2                    (if use_rviz)
```

**Map injection (fix for a real bug):** `bringup.launch.py` writes a temporary copy of
`nav2_params.yaml` with `map_server.yaml_filename` already filled in, then launches localization with
`map:=''`. The standard mechanism (RewrittenYaml + condition `map==''`) did not propagate reliably
through an include → map_server stayed empty → lifecycle blocked.

### 1.5 The goal forwarder rule — CRITICAL

`navigation_launch.py` **renames** the `bt_navigator` input from `/goal_pose` to
`/goal_pose_nav`, so that docking can intercept `/goal_pose` (undock before navigating).
Consequence: the RViz "2D Goal Pose" click (on `/goal_pose`) **only reaches Nav2 if someone copies**
`/goal_pose → /goal_pose_nav`. That "someone" = the **forwarder**.

**There must be exactly ONE. Never two** (otherwise the goal is published twice):

| Mode | Forwarder | How |
|---|---|---|
| Docking active (default) | **dock_trigger** | owns `/goal_pose`, undocks if needed, republishes on `/goal_pose_nav` |
| Nav only (`use_docking:=false`) | **relay** | dumb pipe `/goal_pose → /goal_pose_nav` |
| Nothing (Gazebo + Nav2 only) | **none** | RViz goals don't go through → you must launch the relay or the docking |

The single command chooses automatically via `use_docking`. With individual commands, **you
choose** (launch the relay OR the docking, never both).

### 1.6 `nav2_params.yaml` — the config monolith (shared sim+real)

| Section | Notable values |
|---|---|
| **amcl** | scan = `/scan_filtered`, likelihood_field, recovery alpha fast/slow |
| **controller_server** | RotationShimController (turns first if heading > threshold) + DWB; `max_vel_x` 0.20, `max_vel_theta` 0.5, `decel_lim_x` −2.5, `decel_lim_theta` −2.0, `acc_lim_theta` 0.5 |
| **critics DWB** | PathAlign 16.0 / GoalAlign 12.0 (fwd_point 0.30), ObstacleFootprint (full shape) |
| **local_costmap** | rolling 3×3 m, inflation **0.15**, `always_send_full_costmap: true` |
| **global_costmap** | inflation **0.35**, `always_send_full_costmap: true` |
| **planner_server** | SmacPlanner2D (A*) |
| **footprint** | chassis polygon (≈ 0.78×0.58 m, corners) — full footprint for obstacle avoidance |
| **collision_monitor** | "approach" action (slows down), source `/scan_filtered` |

### 1.7 Other platform configs

- `ekf.yaml` (bringup) — real EKF: fuses `/odom/unfiltered` (vx, vyaw) + `/imu/data` (**gyro-Z only**), `two_d_mode`, `transform_time_offset: 0.2`.
- `gz_bridge.yaml` (gazebo) — gz↔ros bridges: `/clock /odom /tf /imu /scan /rgb_image /camera/camera_info`, and `/cmd_vel` ros→gz.
- `scan_body_filter.yaml` (nav2, **sim**) vs `scan_body_filter_real.yaml` (perception, **real**) — two body filters (see §6 audit).
- `slam.yaml` (nav2) — slam_toolbox (Ceres, loop closure).
- `dock_trigger.yaml` (docking) — multi-phase sequencer + dock pose + obstacle guard.
- `tags_36h11.yaml` (real, **0.08 m**) vs `tags_36h11_sim.yaml` (sim, **0.16 m**) — size of the tag's black square.

---

## 2. Instance repository — `openamr` (THIS repo)

Specific to THIS robot: documentation, diagnostic/field scripts, local configs/maps.

### 2.1 Tree

```
openamr/
├── docs/           ← documentation (see §5)
├── scripts/        ← diagnostic scripts + helpers (see 2.2)
├── launch/         ← ⚠️ OLD real launch system (see §6 audit)
├── config/         ← ⚠️ nav2_params_real.yaml (OLD, see §6 audit)
├── firmware/       ← lino_base_config.h overlay (the rest is upstream on the Pi)
├── maps/           ← SLAM maps (coin1, coin2, …)
└── claude-memory/  ← session memos (context resumptions)
```

### 2.2 Scripts (catalog)

**Launch / field:**
- `bringall.sh` — ⚠️ **OLD** Nav2 orchestration on the Pi (kill → bringup → lidar check → EKF → init pose → wait map→odom → Nav2 → relay). See §6.
- `stop.sh` — cancels the current goal (`navigate_to_pose` cancel_goal) without killing the nav.
- `agentup.sh` — launches just the micro-ROS agent (Teensy test, no motion).

**Motor / encoder tests:**
- `pid_tuner.py` — matplotlib GUI (PC): Kp/Ki/Kd/gain/speed/PWM sliders, 2 modes (open-loop + PID), live L/R curves. Publishes `/debug/tune`, `/cmd_vel`, `/debug/openloop`.
- `encpid.py`, `encread.py` — live encoder monitoring (target/measured rpm, counts).
- `openloop_test.py`, `powered_debug_test.py`, `guided_encoder_test.py`, `high_rate_capture.py`, `sign_test.py` — motor test variants (open loop, powered step, by hand wheels in the air, 50 Hz capture, encoder direction).
- `wtest.sh` (wheels in the air, raw asymmetry), `gtest.sh` (on the ground, validates geometry), `yawtest.py`.
- `raw_debug_monitor.py` — raw monitor of `/debug/*` topics.

**Perception / mapping:**
- `scan_body_filter.py` — body filter `/scan → /scan_filtered` (field version).
- `lidar_view.py` — ASCII view of the scan by sector (detects the front of the robot).
- `cam_snapshot.py` — camera snapshot (headless Pi).
- `clean_map.py` — cleans the SLAM `.pgm` files (scipy connected components, removes noise).

**Configs / misc:**
- `ekf.yaml`, `camera_info.yaml`, `openamr_nav.rviz`, `openamr_slam.rviz`, `COMMANDS.md` (full cheat sheet), `goal_relay.py`.
- `odom_tf_relay.py` — ⚠️ **obsolete** (replaced by the EKF). `tune.sh` — ⚠️ **obsolete** (replaced by `pid_tuner.py`).

### 2.3 Firmware (overlay)

`firmware/config/lino_base_config.h` = our `#define`s on top of upstream `linorobot2_hardware`:
- `LINO_BASE DIFFERENTIAL_DRIVE`, generic 2-pin driver, IMU `USE_MPU9250_IMU` (the chip is an MPU6500).
- PID: `K_P 0.6`, `K_I 0.35`, `K_D 0.15`. `LR_WHEELS_DISTANCE 0.46`. `MOTOR2_GAIN ≈ 1.10` (right wheel ~10% faster in open loop).
- `BAUDRATE 115200` (must match the agent). Encoder pins L 14/15, R 11/12; motors L PWM1/20/21, R PWM5/6/8.
- Build: PlatformIO (`pio run -e teensy40`). Flash: `teensy_loader_cli --mcu=TEENSY40 -s -w`.

---

## 3. Data flow at runtime

### 3.1 TF tree

```
map  ──(AMCL, on /scan_filtered)
 └ odom  ──(EKF [real] / DiffDrive plugin [sim])
    └ base_link
       ├ base_footprint   (identity)
       ├ lidar_link       real: x=0.335, z=0.18, yaw=π (mounted at 180°)
       ├ imu_link         (identity; only gyro-Z used)
       └ camera_link      real: x=0.415, z=0.12
          └ camera_optical_frame   (ROS optical convention)
             └ charging_dock_tag_{0,1,2}   (apriltag_ros, PnP)
```

In **real**, the static sensor TFs come from `static_transform_publisher` (measured values
of THIS robot). In **sim**, they come from the URDF joints.

### 3.2 Key topics — SIM vs REAL

| Data | SIM (source) | REAL (source) | Consumed by |
|---|---|---|---|
| Clock | `/clock` (Gazebo) | system clock | all if `use_sim_time` |
| `/odom` | Gazebo DiffDrive plugin | **EKF** (fuses `/odom/unfiltered` + gyro) | Nav2, costmaps |
| `/odom/unfiltered` | — | Teensy (micro-ROS) | EKF |
| `/imu/data` | Gazebo IMU plugin | Teensy MPU6500 | EKF (gyro-Z) |
| `/scan` | Gazebo lidar plugin | RPLIDAR | body filter |
| `/scan_filtered` | laser_filters (nav2) | scan_body_filter (perception) | AMCL, costmaps, collision_monitor, dock_trigger |
| camera | `/rgb_image` + `/camera_info` | `/camera/image_raw` + `/camera/camera_info` | apriltag |
| `/cmd_vel` | → DiffDrive plugin | → Teensy (PID) | base |
| goal | `/goal_pose` → `/goal_pose_nav` | same | bt_navigator |

**Key consequence: Nav2 and `nav2_params.yaml` are identical**; only the injection point of the
topics (and `use_sim_time`) changes.

### 3.3 Firmware → ROS chain (real)

```
Teensy 4.0 (50 Hz)  ──USB serial 115200──>  micro_ros_agent  ──>  ROS network
  publishes: /odom/unfiltered, /imu/data(_raw), /debug/left, /debug/right, /debug/pwm
  subscribes: /cmd_vel (→ PID), /debug/openloop (→ direct PWM, bypass PID), /debug/tune (→ live gains)
  /debug/{left,right} = Vector3 (x=target rpm, y=measured rpm, z=counts); QoS best-effort
  watchdog 200 ms: cuts the motors if no more /cmd_vel (but NOT open-loop)
```

### 3.4 Docking pipeline

```
camera → apriltag_node (PnP on tags 0/1/2) → TF camera_optical_frame→charging_dock_tag_{0,1,2}
        → detected_dock_pose_publisher → /detected_dock_pose (10 Hz)
        → dock_trigger (multi-phase sequencer):
            1) NavigateToPose to the staging
            2) centering scan (rotation, center the tag)
            3) estimate the dock normal (baseline of the external tags)
            4) pure-pursuit toward the normal
            5) final approach in 2 regimes (EMA axis far → visual servo near)
        dock_trigger also owns /goal_pose (undock-before-navigation gate)
        output: /cmd_vel (direct), /docking/debug_markers
```

---

## 4. How to launch (command recap)

**Sourcing (each terminal):**
```bash
source /opt/ros/jazzy/setup.bash
source ~/Documents/openAMRobot/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
```

**Single command:**
```bash
ros2 launch openamrobot_bringup bringup.launch.py sim:=true  use_rviz:=true        # full sim + docking
ros2 launch openamrobot_bringup bringup.launch.py sim:=false use_rviz:=true        # full robot + docking
# nav-only variant: add use_docking:=false
```

**Individual commands (sim) — terminal 3 = ONE forwarder:**
```bash
ros2 launch openamrobot_gazebo gz_simulator.launch.py gui:=true        # T1 Gazebo
ros2 launch openamrobot_nav2   sim_bringup_launch.py use_rviz:=true     # T2 Nav2
ros2 launch openamrobot_bringup goal_relay.launch.py                    # T3a nav only
ros2 launch openamrobot_docking openamrobot_docking.launch.py           # T3b docking (NOT in addition to T3a)
```

**Trigger docking:**
```bash
ros2 topic pub /dock_trigger std_msgs/msg/Bool "{data: true}" --once
```

⚠️ Only one general command at a time (otherwise two Gazebos / two `/clock`s). Never two
forwarders.

---

## 5. Documentation map (this repo)

| Folder | Content |
|---|---|
| `docs/00-overview.md`, `01-communication.md` | General architecture, buses, topics, TF, DDS. |
| `docs/hardware/` | 11 sheets: motors+drivers, driver error codes, encoders, IMU, lidar, camera, **power**, Pi, Teensy, wiring, BOM. |
| `docs/software/` | ros-architecture, bringup, navigation, visualization. |
| `docs/firmware/` | firmware (structure+config), control-loop-pid, debug-telemetry. |
| `docs/procedures/` | running-the-robot, **real-robot-runbook** (the full runbook), safety. |
| `docs/history/` | diagnostics (resolved root-causes), internship report. |
| `docs/launch-architecture-audit.html` | Visual launch audit (HTML, predating the §1.4 unification). |

---

## 6. AUDIT — duplicates, divergences, inconsistencies

### 🔴 Major — TWO real launch systems in parallel

| System | Files | State |
|---|---|---|
| **OLD** (field, on the Pi) | `openamr/launch/openamr_real_bringup.launch.py` + `openamr/config/nav2_params_real.yaml` + `scripts/bringall.sh` | Historical, deployed on the Pi |
| **NEW** (integration) | `openamr-platform-sw` → `bringup.launch.py sim:=false` + `nav2_params.yaml` | The target — replaces the old one |

→ **Two real `nav2_params`** (`openamr/config/nav2_params_real.yaml` vs platform-sw `nav2_params.yaml`) that **can diverge** (footprint, inflation, collision_monitor tuned separately). **Risk**: you tune one file, the other stays stale.

**✅ DECISION (2026-06-26) — Migrate to platform-sw.** `bringup.launch.py sim:=false` becomes THE
real launch; `openamr-platform-sw/.../nav2_params.yaml` is **authoritative**. Execution plan:
1. **✅ DONE** — `openamr/launch/openamr_real_bringup.launch.py`, `openamr/config/nav2_params_real.yaml`, `scripts/goal_relay.py` and `scripts/bringall.sh` marked **legacy** (headers + pointer to `bringup.launch.py`).
2. **✅ DONE** — Params reconciliation: diff old↔new → **nothing to port**. The `nav2_params_real.yaml` snapshot is an OLDER version of the live params (which already has RotationShim, decel −2.5, PathAlign 16, costmap full True, inflation 0.35). ⚠️ Only observation: the footprint differs (old `[0.535, 0.31]` wider vs live `[0.415, 0.19]`) — **to verify on the robot** during the real test.
3. **⏳ TODO (after robot validation)** — Point `scripts/bringall.sh` to `ros2 launch openamrobot_bringup bringup.launch.py sim:=false` (or deprecate it). ⚠️ Reproduce the `map→odom` wait before the nav if the real costmaps come out empty.
4. **⏳ TODO (after robot validation)** — Remove the old system.

### 🟠 Medium

- **`bringup_sim.launch.py`** (docking) now duplicates `bringup.launch.py sim:=true` (since the unification). Kept for compat, but a single implementation should remain in the end.
- **Two lidar body filters**: `scan_body_filter.yaml` (sim, laser_filters, radians) vs `scan_body_filter_real.yaml`/`scripts/scan_body_filter.py` (real, degrees + distance mask). Legitimate (different mountings) **but the calibrations must stay consistent**.
- **Two map injections**: `bringup.launch.py` (temporary params, deterministic) vs `sim_bringup_launch.py` (map passed directly). Unify on the deterministic method.

### 🟢 Minor / false duplicates (OK, justified)

- **2 `parameter_bridge` bridges** (gz_simulator + camera_info in docking) — documented workaround (image_transport looks for `/camera_info` at the root).
- **2 apriltag configs** (sim `/rgb_image` vs real `/camera/image_raw`) — genuine sim/real split.
- **2 RViz configs** (description `rviz.rviz` robot dev vs nav2 `nav2_view.rviz`) — different uses.
- **Obsolete scripts** in `openamr/scripts/`: `odom_tf_relay.py` (replaced by EKF), `tune.sh` (replaced by `pid_tuner.py`) — to remove or mark.

### 📄 Docs to fix / stale

- `docs/software/visualization.md` — mentions "FastDDS default 42" whereas we switched to **CycloneDDS** (domain 0). To update.
- `docs/procedures/running-the-robot.md` — overlaps `real-robot-runbook.md`; clarify the scope (quick-start vs full runbook).
- `docs/software/navigation.md` — lists "docking: TODO": now **integrated** (sim + real) → update.
- `docs/software/bringup.md` — describes the old `openamr_real_bringup.launch.py`; add the single command `bringup.launch.py`.
- **Missing**: no formal doc "colcon build/deploy platform-sw workflow" nor "real docking: set tag size + dock pose". No changelog.

### 🔴 Hardware blockers (reminder, outside software)

- **Battery**: aim for ≥ 25 V at rest before any nav test (otherwise soft torque → collisions).
- **Pi 5 brownout**: cuts out at bringup launch (current spike > supply) — check the Pi's `ping`.
- **Left wheel cable**: intermittent faulty contact (to resolder).

---

## 7. Summary

**Strengths:** clean layered architecture, a single Nav2 stack shared sim/real, symmetric single
entry point (`bringup.launch.py`), clean goal routing (one exclusive forwarder),
well-mastered firmware, rich hardware doc, valuable diagnostics history.

**To address first:** the divergence of the **two real launch systems** (§6 major) —
it's the only real risk of confusion/regression. The rest is consolidation (remove the
legacy, align the filters, refresh 4-5 docs).
