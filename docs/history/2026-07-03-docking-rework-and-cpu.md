# Day summary — 2026-07-03: vision-CPU optimization + camera-frame docking rework

One long real-robot session. Two big threads landed — (1) a **vision-pipeline
optimization** that freed the Pi and fixed AprilTag detection, and (2) a **docking
rework** that computes the dock normal in the ROBOT frame (not the wobbly map). Plus a
hardware finding that turned out to be the real day-to-day blocker.

Robot: Pi 5, IMX708 via `camera_ros`, `apriltag_ros`, RPLIDAR A1, Teensy (micro-ROS),
ROS 2 Jazzy, Nav2, CycloneDDS. Dock = printed 3-tag 36h11 bundle (id0/id1/id2, 52 cm
baseline). Companion audit: `docs/AUDIT-2026-07-03-cpu-pipeline-optimization.md`.

---

## 1. Vision / CPU — the big win

### Root cause (measured, not assumed)
`vmstat` + `mpstat` during load showed the Pi was **NOT** the wall:
- CPU **~48-55 % idle**, **iowait 0 %**, **50 °C no throttling**, 2.3 GB RAM free, no swap.
- BUT **35 000 context-switches/s** and 20 % system time.

The bottleneck was the **pipeline architecture**, not raw compute. The image went through
**3 processes + 2 DDS hops**: `camera_node → apriltag_gate.py (Python/GIL, full-res
republish) → apriltag_node`. Every 2.7 MB frame was serialized + copied twice; the middle
hop was a single-threaded Python passthrough in the hot path. That starved the detector
(5-8 Hz, 250-700 ms stale) → the visual servo chased stale data → oscillation.

### Fixes shipped
- **B1 — cap the camera to ~15 fps** (`camera.launch.py` `FrameDurationLimits: [66667,66667]`).
  The sensor was running at 30 fps and dropping 2/3. → idle 55 %→67 %, interrupts halved,
  camera CPU halved, **zero precision loss** (same resolution).
- **A1 — compose camera + apriltag into ONE `component_container_mt`** with
  `use_intra_process_comms=True` (`apriltag_composed.launch.py`). Image passed by pointer,
  no DDS, no Python gate. → **vision CPU ~124 % → ~55 %**, **detector 5-8 Hz → 15 Hz**.
  Confirmed on-Pi that `camera::CameraNode` and `AprilTagNode` are both composable.
- **New launch structure** (openamrobot_docking / openamrobot_bringup):
  - `apriltag_composed.launch.py` — camera + apriltag intra-process (replaces
    camera.launch.py + apriltag.launch.yml for the real robot).
  - `docking_composed.launch.py` — dock_trigger + detected_dock_pose, `use_apriltag_gate:=false`
    (the composed apriltag is always-on; no Python gate to flip).
  - `bringup_composed.launch.py` — one command: bring-up (`use_camera:=false`,
    `use_docking:=false`) + composed vision + docking.

### Result
Docking ran end-to-end and **succeeded** (docked at 0.246-0.248 m, no oscillation). CPU
during a real dock: **~45 % used / 55 % idle**, **RAM ~1.0 GB / 3.9 GB (24 %)**, 48 °C, no
swap, no throttling. The vision container is the main consumer (~0.6-0.8 core). Plenty of
headroom — the Pi is **not** the limiter.

### Known launch wart
`bringup_composed` uses `use_docking:=false`, which makes the bring-up start a
`topic_tools relay /goal_pose → /goal_pose_nav` (`goal_pose_relay`). dock_trigger ALSO
forwards goals → dock_trigger's DOUBLE-FORWARDER guard fires. Workaround: kill the relay
(`pkill -f "topic_tools/relay.*goal_pose"`). **TODO:** make `bringup_composed` suppress the
bring-up relay.

---

## 2. Docking rework — normal in the ROBOT frame, not the map

### Problem
`_estimate_dock` computed the dock centre + normal from the tags looked up in the **map
frame** (`_lookup_tag_map`) → it rode the AMCL `map→odom` transform, which **jumps**
(LiDAR relocalization) and drifts (odometry). Over the multi-second approach the fixed
map-frame target went stale → the robot arrived off-axis. User's exact ask: rely on the
**tag normal relative to the robot**, never the wobbly map.

### Fix
- **`_lookup_tag_base`** — tag position in `base_link` (static `base_link←camera` +
  AprilTag `camera←tag`), so NO map and NO odometry in the chain. Verified working:
  `base_link→tag` transforms return valid values when tags are visible.
- **`_estimate_dock_base_once`** — dock centre + normal in `base_link` (robot at the
  origin facing +x). **Robust to a single outer-tag dropout**: with both outer tags it
  uses the full 52 cm baseline; with the centre tag + ONE outer it falls back to the
  half-baseline (`_dock_pose_from_two`). This was essential — requiring both outers made
  the estimate `None` whenever id0 flickered, silently reverting to bearing-only.
- **Phase-5 FAR** now pure-pursuits the ROBOT-frame normal (`use_camera_frame_normal`,
  default true; live-tunable to compare against the legacy map path). Corrects BOTH lateral
  offset AND approach heading (perpendicular), unlike the centre-tag bearing which only
  centres. `freeze_axis_distance` back to 0.70 (normal dominates until the outer tags leave
  the FOV ~0.70 m; below that, bearing for the final blind stretch).

### How the normal is computed (for reference)
```
c0, c2 = outer tags in base_link ; baseline = c2 − c0 ; L = |baseline|
normal (nx,ny) = (−dy/L, dx/L)         # perpendicular to the tag row
→ flip toward the robot ; normal_yaw = atan2(−ny, −nx)   # heading to be perpendicular
dock centre = midpoint(c0, c2)
```

### Normal precision — measured
Stationary probe over 18 frames: **std 0.11°** (rock-solid), mean **+4.2°**, baseline 0.541 m.
→ NOT noisy at rest. The +4.2° is a CONSTANT offset — **either the robot was ~4° off (hand-
placed) or a camera-mount yaw bias**. **Unresolved — test pending** (see §6). Under MOTION
the estimate does jitter (blur, changing view angle), so a temporal average is still needed
(see below).

### Averaging (per user feedback — reuse, don't reinvent)
Added a temporal EMA on the base-frame normal (byaw) + lateral for the moving case, but
**reusing the EXISTING depth-weighted weight** `min(0.6, axis_filter_alpha·predock/depth)`
(weight grows as the robot advances → nearer, more accurate frames dominate) rather than a
new fixed alpha. Spike-reject gate (`axis_spike_reject`, ~20°) drops a bad frame. The
"stop pursuing when too close" is already the FAR→NEAR freeze handover. **This last edit is
deployed to the repo but NOT yet pushed to the Pi (Pi went offline at end of session).**

---

## 3. Control / actuation improvements

- **Velocity floors kept** (from 2026-07-02): taper 0.05, `min_turn_omega` 0.15.
- **Scan stiction fix**: `scan_rotation_speed` 0.17 → **0.30**. 0.17 (just above the 0.15
  continuous floor) was too close to STATIC friction to start a spin-in-place from rest →
  the robot juddered without searching ("tags not detected during scan"). 0.30 breaks
  stiction and sweeps.
- **Spin floor**: new `spin_min_omega` 0.25 in `_spin_to_yaw` — a P-controlled spin near
  its target commanded a sub-floor omega → didn't rotate. Snap up so Phase 3/4 spins execute.
- **Tuning (persisted)**: `drive_speed` 0.12, `line_yaw_kp` 1.0, `line_lookahead_distance`
  1.0. Turn radius = v/omega; slow v + the 0.15 floor forced a tight turn that swung the
  camera off the bundle. Gentler gains + speed = smooth line-following (verified "much better").
- **Sigma-delta PWM of omega** (`omega_pwm`, default true, `_floor_omega`): below the motor
  floor, emit ±0.15 pulses whose time-average = the desired rate → gentle continuous turn
  instead of the ±0.15 left-right limit cycle. (Works best while already driving forward.)

---

## 4. HARDWARE — the real day-to-day blocker

**Right-wheel faux-contact confirmed.** A pure-rotation test (`/cmd_vel_nav` z=0.4) with
wheel telemetry:
- `/cmd_vel` final = 0.4 → command reaches the base ✓ (collision_monitor not blocking).
- LEFT wheel = **-8.8…-9.5 rpm** (turning) ; RIGHT wheel = **0.0 rpm (DEAD)**.

A later open-loop per-wheel test had BOTH wheels turn → the fault is **intermittent**: the
right motor connection drops in and out. This explains most of the day's flakiness (nav
"struggling", robot veering, spins failing "sometimes", docking working 1-in-2). **No
software fix — it needs the right-motor connection re-seated / re-soldered. This is the #1
blocker.** Diagnose by wiggling the connectors while watching `/debug/right` rpm jump
between 0 and ~9, and check the driver fault LEDs.

---

## 5. Nav2 planning speedup ("takes too long to think")

Diagnosis: SmacPlanner2D planning at full 0.05 m resolution + `max_planning_time 2 s`, plus
the controller waiting **30 s stuck** before recoveries. (Partly amplified by the
faux-contact: robot commanded but doesn't move → "Failed to make progress" → recovery.)
Changes in `nav2_params.yaml` (need a navigation relaunch to load; one is live):
- `downsample_costmap: true` + `downsampling_factor: 2` → A* on a 0.10 m grid, ~4× fewer
  nodes → much faster global plans.
- `max_planning_time` 2.0 → 1.0.
- `progress_checker.movement_time_allowance` 30 → 12 (recover sooner; **live-settable** via
  `ros2 param set /controller_server progress_checker.movement_time_allowance 12.0`).

---

## 6. Pending / next session
1. **Deploy the last EMA edit to the Pi** (Pi was offline at session end) + reload dock_trigger.
2. **Test the moving EMA + PWM + alignment** on the composed pipeline.
3. **Resolve the +4.2° normal offset**: place the robot truly perpendicular (equal L/R gap
   to the dock face), read the reported `norm=` in the `[P5]` debug. ~0 → no bias (control
   issue) ; ~+4° → camera-mount bias → add a `normal_yaw_offset` calibration param.
4. **If the robot still arrives off-perpendicular** after a good estimate: implement the
   "freeze the perpendicular heading at the 0.70 m handover and drive straight holding it
   (odom yaw)" for the NEAR leg — the bearing corrector un-aligns because it only centres id1.
5. **FIX THE RIGHT-WHEEL FAUX-CONTACT** (hardware) — until then nav/docking stay flaky.
6. Relaunch navigation to load the Nav2 planner speedups.
7. Still open from before: 6 PRs ready but not opened; deterministic camera focus (LensPosition).

## Tools added today
- `scripts/cpusnap.sh` (on Pi `/tmp/cpusnap.sh`) — labelled CPU snapshot, builds a comparison table.
- `normal_probe.py` — dock-normal noise/bias probe (base_link).
- `spintest.sh` / `wheeltest.sh` — wheel/faux-contact diagnostics.
- `dock_stack.sh`, `vision_composed.sh`, `bringup_nocam.sh` — dedicated-log launchers.
- `apriltag_composed.launch.py`, `docking_composed.launch.py`, `bringup_composed.launch.py`.

## One-line takeaway
The **software is in good shape** — vision is optimized (Pi at 45 % CPU with margin),
docking computes the normal robustly in the robot frame, the controller is smooth. **The
remaining blocker is hardware: the intermittent right-wheel connection.**
