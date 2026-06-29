# Technical Internship Report — OpenAMR Autonomous Mobile Robot (AMR)

*Technical summary document. Platform: autonomous differential-drive robot based on linorobot2, ROS 2 Jazzy.*

---

## 1. Project overview

### 1.1 Objective
Commission and improve the reliability of an **autonomous mobile robot (AMR — Autonomous Mobile Robot)** with
differential drive: a robot that localizes itself on a map, plans a path to a goal, and
reaches it **while avoiding obstacles**, without human intervention.

### 1.2 Nature of the robot
- **Type**: differential drive (2 independent drive wheels + caster wheels), driven by BLDC motors.
- **Dimensions**: **0.78 m × 0.58 m** (rounded-corner rectangle).
- **Software base**: `linorobot2` (firmware + ROS 2 workspace) + the **Nav2** navigation stack.
- **Target use case**: autonomous indoor navigation + **docking** (berthing at a station via
  AprilTag visual markers).

### 1.3 Functional chain (overview)
```
        PERCEPTION                 DÉCISION                    ACTION
  ┌────────────────┐      ┌───────────────────────┐    ┌──────────────────┐
  │ LiDAR 2D       │─────►│ SLAM / AMCL (localise) │    │ Nav2 controller  │
  │ Caméra (IMX708)│      │ Nav2 planner (chemin)  │───►│ → /cmd_vel       │
  │ IMU (MPU-6500) │─────►│ EKF (fusion odométrie) │    │ → Teensy (PID)   │
  │ Encodeurs      │      │ costmaps (obstacles)   │    │ → drivers BLDC   │
  └────────────────┘      └───────────────────────┘    └──────────────────┘
         ▲                                                       │
         └───────────────── roues / déplacement réel ◄──────────┘
```

---

## 2. Hardware architecture

### 2.1 System view
```
   230 V AC ─► AC/DC 24 V ─┐
                           ├─(parallèle)─► Bus 24 V ─► Drivers BLDC ×2 ─► Moteurs ×2
   Batterie 24 V ──────────┘                    │
                                                └─► DC-DC 24V→5V ─► Raspberry Pi 5
                                                                        │ USB
                                              Teensy 4.0 (µROS) ◄───────┘
                                              ├─ I²C ─► IMU MPU-6500
                                              ├─ A/B ─► Encodeurs AS5040 ×2
                                              └─ PWM/DIR ─► Drivers BLDC ×2
   Raspberry Pi 5 ─ USB ─► LiDAR (RPLIDAR) + Caméra (CSI, IMX708)
```

### 2.2 Bill of materials (BOM) — identified components
| # | Component | Exact reference | Role |
|---|---|---|---|
| 1 | Compute unit (SBC) | **Raspberry Pi 5** (Ubuntu 24.04 + ROS 2 Jazzy) | ROS 2 brain: SLAM, Nav2, perception |
| 2 | Microcontroller | **Teensy 4.0** (NXP i.MX RT1062, Cortex-M7 600 MHz) | Real time: motor PID, encoder/IMU reading, odometry |
| 3 | Motor drivers ×2 | **ZBLD.C20-120L2R** (ZD) — 24 V, 7.5 A, 120 W | BLDC power stage (commutation via Hall sensors) |
| 4 | Motors ×2 | **Z4BLD60-24GN-30S** (ZD) — BLDC 60 W / 24 V / 3.8 A / 3000 rpm / **P=5** | Drive, ~30:1 gearbox → ~100 rpm at output |
| 5 | Encoders ×2 | **AMS AS5040** (magnetic, quadrature) — 1024 cnt/rev | Wheel speed/position measurement (odometry + PID) |
| 6 | Inertial measurement unit | **TDK InvenSense MPU-6500** (I²C 0x68) | Accelerometer + gyro → heading (yaw) fused in the EKF |
| 7 | 2D LiDAR | **Slamtec RPLIDAR A1** (USB via CP2102) | 360° scan → SLAM, localization, obstacle detection |
| 8 | Camera | **Sony IMX708** = Raspberry Pi **Camera Module 3** | Vision (calibrated), future AprilTag detection for docking |
| 9 | DC-DC | Buck **24 V→5 V** (~300 W CC/CV) | 5 V supply for the Raspberry Pi |
| 10 | Battery ×4 | **DM12-7S** — 12 V 7 Ah lead-acid (AGM) | Energy; 2 in series = 24 V bus |
| 11 | AC/DC | **230 V→24 V** converter (fixed output) | Mains supply (in parallel with the battery) |

### 2.3 Teensy 4.0 wiring / pinout (3.3 V logic)
Convention: **MOTOR1 = LEFT wheel, MOTOR2 = RIGHT wheel**.

| Function | Teensy pin | Destination |
|---|---|---|
| IMU SDA / SCL | 18 / 19 | MPU-6500 (I²C 0x68) |
| LEFT encoder A / B | 14 / 15 | left AS5040 |
| RIGHT encoder A / B | 11 / 12 | right AS5040 |
| LEFT motor PWM / FWD / REV | 1 / 20 / 21 | left driver `VAR/AI2` `FWD/DI1` `REV/DI2` |
| RIGHT motor PWM / FWD / REV | 5 / 6 / 8 | right driver `VAR/AI2` `FWD/DI1` `REV/DI2` |
| micro-ROS | USB | Raspberry Pi (native serial, 115200 baud) |

> **Driver principle**: the Teensy sends **PWM (speed setpoint) + 2 direction lines**; the driver
> itself handles **BLDC commutation from the Hall sensors** (the Teensy never sees U/V/W).
> Common ground is mandatory: **Teensy GND ↔ driver COM**.

### 2.4 Driver configuration (DIP switches)
| SW1 | SW2 | SW3 | SW4 | SW5 | SW6 |
|---|---|---|---|---|---|
| OFF | ON | OFF | ON | ON | OFF |
- **SW1 OFF = open loop**: the driver is a plain power stage, **the Teensy PID is the only
  regulator** (avoids a double loop → cleaner motion).
- **SW2 ON = speed setpoint via AI2** (0–5 V input where the Teensy's filtered PWM arrives).
- **SW4+SW5 ON = 5 pole pairs** (the motor is P=5).

### 2.5 Power and electrical safety
- **24 V** bus supplied by the **battery (2× 12 V lead-acid in series)** OR the **AC/DC mains supply**, in parallel.
- **DC-DC 24→5 V** for the Pi; **Teensy powered at 5 V from the Pi's USB**; IMU + encoders at **3.3 V**.
- **Battery thresholds** (24 V lead-acid, at rest): ~25.5–26 V full ✅ / ~24 V half ⚠️ / ≤ 23.5 V discharged ❌.
  Under load the voltage drops → aim for **≥ 25 V before any navigation test**.
- **Identified safety points (to be fixed)**: no **fuse** on the battery (a short = hundreds
  of amps → fire risk), no **battery cut-off / emergency stop**, battery and mains in
  parallel (back-feed risk if connected simultaneously), 230 V to be protected (30 mA RCD + enclosure).

---

## 3. Software architecture

### 3.1 ROS 2 stack
- **OS / middleware**: Ubuntu 24.04, **ROS 2 Jazzy**, **CycloneDDS** (`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`,
  `ROS_DOMAIN_ID=0`). *FastDDS → CycloneDDS migration performed* (FastDDS crashed the Nav2 actions
  used for docking).
- **micro-ROS** (XRCE-DDS): bridge between the Teensy and ROS 2 on the Pi over **USB serial 115200**
  (`micro_ros_agent`). Topics exposed by the firmware: `/cmd_vel`, `/odom/unfiltered`, `/imu/data`,
  `/debug/openloop`, `/debug/left`, `/debug/right`, `/debug/pwm`.

### 3.2 Teensy firmware (linorobot2)
- Receives `/cmd_vel` → differential kinematics → per-wheel speed setpoint.
- **Per-wheel PID control** (K_P 0.6 / K_I 0.35 / K_D 0.15), output **10-bit PWM (0–1023) at 3 kHz**.
- Reads the **AS5040 encoders** (1024 cnt/rev) → actual speed + **odometry**; reads the **IMU** (yaw).
- Key parameters: `MOTOR_MAX_RPM 80`, `WHEEL_DIAMETER 0.2`, `LR_WHEELS_DISTANCE 0.46`, `COUNTS_PER_REV 1024`.
- 200 ms watchdog: motors stopped if `/cmd_vel` is no longer received.

### 3.3 Localization & mapping
- **robot_localization (EKF)**: fuses the **wheel odometry** + the **IMU** → smoothed `odom → base_link` TF.
  (Tuning `transform_time_offset: 0.2` to align the scan and the TF under CycloneDDS.)
- **slam_toolbox** (online async): builds the **map** from the LiDAR → `coin_ok` map
  (`.pgm` + `.yaml`).
- **AMCL** (Nav2): particle-filter localization on the saved map → `map → odom` TF.

### 3.4 Navigation (Nav2)
| Component | Plugin / role |
|---|---|
| **map_server** | publishes the static map `/map` |
| **AMCL** | localization on the map (`map → odom`) |
| **planner_server** | **SmacPlanner2D / NavFn** → global path (`/plan`) on the **global costmap** |
| **controller_server** | **DWB** (Dynamic Window) → `/cmd_vel`, local tracking on the **local costmap** |
| **bt_navigator** | behavior tree (mission orchestration) |
| **behavior_server** | recovery behaviors (spin, backup, wait) |
| **costmaps** | cost grids: `static_layer` (map), `obstacle/voxel_layer` (real-time LiDAR), `inflation_layer` (margin) |
| **lifecycle_manager** | configure/activate sequence of the Nav2 nodes |

### 3.5 Perception
- **scan_body_filter.py** (in-house node): filters `/scan → /scan_filtered`, **masks the robot's shell**
  (rear sectors + lateral posts) so it is not mistaken for an obstacle.
- **Camera**: `camera_ros` (with the **RPi fork of libcamera**, the upstream version does not support the Cam Module 3),
  **calibration** completed (9×12 checkerboard target, 30 mm) → `camera_info.yaml`.

### 3.6 Robot footprint — critical navigation parameter
- Actual footprint (octagon ≈ rounded rectangle) **0.78 × 0.58 m**, `base_link` (wheel axle = center of
  rotation) **off-center**: front 0.415 m / rear 0.365 m / half-width 0.29 m.
- **Footprint enlarged by +0.12 m** used as a **hard margin**: the controller tests this shape at
  each cycle → keeps ~12 cm of clearance from any obstacle seen by the LiDAR.

---

## 4. DASHBOARD — work completed

Status legend: ✅ done/validated · 🟡 partial/in progress · 🔵 documented/prepared · ⏳ remaining to do.

### 4.1 Hardware & electronics
| Task | Technical detail | Status |
|---|---|---|
| **Full wiring audit** | Teensy ↔ drivers ↔ motors ↔ encoders ↔ IMU pinout, checked pin by pin against the firmware | ✅ |
| **Component identification** | Reading labels + datasheets (Teensy 4.0, ZBLD.C20, Z4BLD60, AS5040, MPU-6500, IMX708, DM12-7S) | ✅ |
| **Encoder overvoltage fix** | A/B outputs at ~5 V on the **5 V-intolerant** Teensy 4.0 → encoder supply lowered to **3.3 V** | ✅ |
| **Right encoder fix** | **Off-center** magnet → "drunk" right wheel → recentering of the AS5040 | ✅ |
| **Driver tuning (DIP)** | Open loop (SW1), AI2 source (SW2), 5 pole pairs (SW4/SW5) | ✅ |
| **Wheel balancing** | L/R asymmetry ~9 % in open loop → corrected by the Teensy PID (~0.2 %) | ✅ |
| **Power diagnosis** | Highlighted the **battery sag under load** + 24 V threshold table | ✅ |
| **Left wheel: intermittent contact** | Signal wiring healthy → fault localized on the **24 V power / motor connector** (to be re-soldered) | 🟡 |
| **Electrical safety** | Identified gaps: fuse, battery cut-off/emergency stop, 230 V protection | 🔵 |

### 4.2 Firmware & low-level control
| Task | Detail | Status |
|---|---|---|
| **Motor/encoder tests** | Open loop (constant PWM) + L/R rpm reading via `/debug/*` | ✅ |
| **PID re-tuning** | Step-response method → K_P/K_I/K_D | ✅ |
| **Wheelbase correction** | `LR_WHEELS_DISTANCE` 0.45 → **0.46** (Teensy re-flash) | ✅ |
| **Motor chain validation on mains** | Closed-loop forward motion, L/R wheels equalized, left wheel holds | ✅ |
| **Encoder ripple correction** | Decentered-magnet ±40% 2/rev error characterized + corrected by a **runtime lookup table** (re-aligned ~8 s/boot) | ✅ |
| **Velocity feedforward** | `PWM = Kff·target + PID` → **speed-independent response** (Kff=7.87 PWM/rpm, measured open-loop) | ✅ |
| **Back-calculation anti-windup** | Bleeds the integral on saturation → no high-speed overshoot | ✅ |
| **Low-speed velocity estimator** | Fixed-displacement (12 counts) → clean rpm where the fixed-time method gives ±70% noise | ✅ |
| **Anti-stiction dither** | ±92 PWM @ 25 Hz below 13 rpm → smooth motion down to ~0.06 m/s (docking) | ✅ |
| **Tuning GUI** | `pid_tuner.py`: live step-response plots + sliders Kp/Ki/Kd/R-gain/Kff/Dither via `/debug/tune` | ✅ |

### 4.3 Perception & mapping
| Task | Detail | Status |
|---|---|---|
| **Camera calibration** | 9×12 / 30 mm checkerboard target → intrinsic matrix + distortion (`camera_info.yaml`) | ✅ |
| **LiDAR shell filter** | `scan_body_filter.py`: masks rear + posts; publication in **RELIABLE** (QoS fix) | ✅ |
| **SLAM map** | slam_toolbox → `coin_ok` map saved (+ save/backup) | ✅ |

### 4.4 Autonomous navigation (Nav2)
| Task | Detail | Status |
|---|---|---|
| **CycloneDDS migration** | Entire stack on `rmw_cyclonedds_cpp` (required for docking) | ✅ |
| **Nav2 + AMCL bring-up** | map_server + AMCL + planner + DWB + bt_navigator working on the real map | ✅ |
| **Correct footprint** | Replacement of `robot_radius` (0.44 m circle too small) with the actual footprint 0.78×0.58 | ✅ |
| **Empty costmaps fix (QoS)** | `/scan_filtered` BEST_EFFORT vs costmap RELIABLE → 0 obstacles; switched to **RELIABLE** | ✅ |
| **Avoidance fix (critic)** | `BaseObstacle` (center only) → added **`ObstacleFootprint`** (tests the whole shape) | ✅ |
| **Dual costmap tuned** | **global inflation 0.40** (centered path, accounts for size) / **local 0.15** + ObstacleFootprint (hard avoidance) | ✅ |
| **Robust launcher** | `bringall.sh`: auto-pose → guaranteed `map→odom`, TF wait before nav, LiDAR health check | ✅ |
| **Centering / finishing touches** | Refine the global inflation + confirm the wheel axle position | 🟡 |
| **Real AprilTag docking** | Pipeline understood and validated in simulation; real-world port to be done | ⏳ |

### 4.5 Documentation & tooling
| Task | Detail | Status |
|---|---|---|
| **Technical docs** | `docs/hardware/*` (wiring, BOM, power, encoders, IMU, camera), `docs/software/navigation.md`, `docs/history/diagnostics.md` | ✅ |
| **Reusable scripts** | `bringall.sh`, `agentup.sh`, `wtest.sh`, `gtest.sh`, `goal_relay.py`, `scan_body_filter.py`, Nav2 RViz config | ✅ |
| **Command cheat sheet** | `scripts/COMMANDS.md` (all PC + Pi commands) | ✅ |

---

## 5. Problems encountered & solutions (technical analysis)

This section illustrates the **diagnostic approach** — often more instructive than the result.

| Observed symptom | Root cause found | Solution |
|---|---|---|
| "Drunk" wheel, weaving | **Off-center magnet** of the **right encoder** | Mechanical recentering of the AS5040 |
| **Left wheel oscillation no gain could fix** | **Decentered magnet, left encoder** → ±40 % 2/rev *measurement* ripple (not real motion) | **Runtime correction table** + full velocity-loop rebuild — see **§5.1** |
| ~4–5 V at encoder output | AS5040 powered at 5 V → 5 V outputs on the **5 V-intolerant Teensy 4.0** | Encoder supply at **3.3 V** |
| Robot "weak", crashes into things | **24 V voltage too low** (battery at 23.4 V, sag under load) | Recharge ≥ 25 V / test **on mains** |
| Robot does not hold its heading | Left wheel **dropping out** (intermittent cable contact) under load + low 24 V | Localized on the power side; to be re-soldered |
| **Empty** costmaps (0 obstacles) | (a) **QoS mismatch**: scan BEST_EFFORT vs costmap RELIABLE; (b) nav launched **before** `map→odom` (lifecycle order) | (a) scan in **RELIABLE**; (b) auto-pose + **wait for `map→odom`** before nav |
| "Sees the obstacle but drives into it" | The **`BaseObstacle`** critic only tests the **center**; the front extends 0.53 m | **`ObstacleFootprint`** critic (entire footprint) |
| Path hugs the walls | Same global/local inflation; planner = point robot | **Global inflation ↑ (0.40)**, local ↓ (0.15) |
| LiDAR not publishing (`/scan` empty) | **RPLIDAR startup timeout** (recurring bug) | **Unplug/replug** the USB; health check at launch |
| RViz "Nav2 Goal" has no effect | The tool needs the Navigation2 panel | Use **"2D Goal Pose"** + `goal_relay.py` relay node |
| SLAM drops scans | Scan ahead of the EKF TF under CycloneDDS | `transform_time_offset: 0.2` in the EKF |

> **Important physical limitation (not fixable in software)**: the LiDAR is **2D at ~18 cm height**.
> An obstacle **lower than ~18 cm** is **invisible** → neither inflation nor footprint avoids it.
> A hardware solution is required (low sensor / depth camera / bumper).

### 5.1 In-depth case study — diagnosing and rebuilding the motor velocity loop

This case study is representative of the whole internship: a symptom that *looked* like a control
problem turned out to be a **sensor defect**, and fixing it properly meant rebuilding the entire
low-level velocity loop. It is documented in full in `docs/history/encoder-calibration.md`.

**Symptom.** During PID tuning, the **left wheel kept a slow ±6 rpm oscillation that no gain could
remove** (lowering K_I calmed it but made the loop sluggish; raising it brought it back). The right
wheel tuned cleanly. A symptom that does not respond to *any* gain is a strong hint that it is **not** a
control problem.

**Diagnosis — measure, don't guess.** I wrote `encoder_calib.py`: at a constant open-loop PWM the wheel
turns at a constant *true* speed, so binning the *instantaneous* measured rpm by **wheel angle**
(`counts mod 1024`) reveals any angle-locked error. Result: the **left encoder reports a 2-cycle/rev
velocity error of ±40 % peak-to-peak, identical at every speed** → position-locked, speed-independent =
a **decentered magnet** on the AS5040. The PID had been faithfully chasing a 40 % *measurement*
artifact. The right wheel showed only ±6 %.

**A sequence of attempts — each one instructive.** The fix is the interesting part:
1. *Compiled correction table* (`true = measured / CAL[angle]`): it **could not hold**. The encoder is
   **incremental** — its count resets to 0 at a random wheel angle on every boot — so a table compiled
   into the firmware is mis-phased by the very re-flash that installs it (verified: it even *doubled*
   the ripple when applied anti-phase).
2. *Time-domain low-pass*: useless — the ripple frequency scales with speed and sits inside the control
   band (it passes *more* at low speed).
3. *Angle-domain estimator* (velocity over half a revolution): flattened the ripple at any speed, but
   added ~0.6 s of lag → unacceptable for the controller.
4. **Final solution — runtime table + fast per-boot phase alignment.** The ripple *shape* is a fixed
   physical property; only its *phase* shifts each boot. So the shape is characterized **once**
   (`encoder_ref_table.json`) and, after each power-on, a ~8 s routine (`align_enc_cal.py`) spins the
   wheel, cross-correlates the measured ripple against the reference to find the per-wheel phase offset
   (sub-degree), and uploads the correctly-phased table to the firmware over a ROS topic — **instant
   correction, no lag, and it survives reboots.** Residual ripple: ±40 % → **±4 %**.

**Rebuilding the loop on a clean signal.** With trustworthy velocity feedback, tuning exposed that a
**pure PID cannot give a consistent response across speeds**: the integral has to "discover" the
holding PWM, which differs with speed, producing an overshoot that *grows with speed* (12 % at 0.15 m/s,
47 % at 0.31). The structural fix is **velocity feedforward**: `PWM = K_ff · target_rpm + PID`, where
`K_ff` (≈ 7.9 PWM/rpm) is measured open-loop. The feedforward supplies the bulk of the command, the PID
only trims the residual → **the same response shape at every speed**, and the gains drop to a calm
`K_P = 2.0 / K_I = 0.10 / K_D = 0.10`. Three more refinements complete the chain:
- **Back-calculation anti-windup** (bleeds the integral out on saturation) removes the residual
  high-speed overshoot.
- A **fixed-displacement velocity estimator** (timing a small 12-count window) removes the ±70 %
  quantization noise the fixed-time method produces below ~5 rpm.
- An **anti-stiction dither** (±92 PWM flipped at 25 Hz, active only below 13 rpm) breaks the low-speed
  **stick-slip** limit cycle (the wheel sticking and releasing against static friction), giving smooth
  motion **down to ~0.06 m/s** — useful for docking. Below that is a hard mechanical floor (motor
  deadband ≈ 120 PWM, static > kinetic friction).

**Resulting control chain** (Teensy, 50 Hz, per wheel):

```
  cmd_vel ─► kinematics ─► [ FEEDFORWARD + PID(+anti-windup) ] ─► DITHER ─► PWM ─► MOTOR
   (m/s)     target_rpm                  ▲                      (<13rpm)            │
                                         │ measured rpm                            │
                ripple table ◄── velocity estimator ◄────── encoder counts ◄───────┘
                /CAL[angle]     Δcounts/Δt (12 counts)
```

| Stage | Problem it solves | Key value |
|---|---|---|
| Velocity estimator (12-count window) | low-speed quantization noise (±70 %) | clean rpm at any speed |
| Runtime ripple table | decentered magnet ±40 % 2/rev | ±40 % → ±4 % |
| Feedforward `K_ff·target` | speed-dependent overshoot | same response everywhere |
| PID + back-calc anti-windup | residual error + saturation overshoot | K_P 2.0 / K_I 0.10 / K_D 0.10 |
| Anti-stiction dither | low-speed stick-slip | smooth to ~0.06 m/s |

**Skills demonstrated:** instrumentation and data-driven diagnosis (separating a sensor artifact from a
control problem), digital control (PID, feedforward, anti-windup), DSP (angle- vs time-domain filtering,
cross-correlation phase alignment), embedded firmware (Teensy/micro-ROS, runtime parameterization), and
knowing the **physical limits** (stick-slip, motor deadband) beyond which software cannot help.

---

## 6. Results / current state

- ✅ Low-level control chain **reliable** (on mains): PID, odometry, encoders, IMU.
- ✅ **Velocity loop fully rebuilt and tuned** (feedforward + PID + anti-windup + runtime encoder-ripple
  correction + anti-stiction dither): consistent response across the whole speed range, smooth from
  ~0.06 m/s (docking) to the nav max — see **§5.1**.
- ✅ **SLAM** operational, map saved.
- ✅ **AMCL localization + Nav2 navigation** working; the robot **plans and moves**.
- ✅ **Obstacle avoidance** working: the costmap sees obstacles, the controller tests the full
  shape of the robot and **no longer drives into them**, global path better centered.
- 🟡 **To finalize**: balancing the centering (global inflation), confirming the wheel axle
  dimensions, repairing the left-wheel intermittent contact, recharging the battery (return to off-mains autonomy).
- ⏳ **Outlook**: real AprilTag docking, electrical safety (fuse + emergency stop).

---

## 7. Outlook / project continuation
1. **Repair the left-wheel intermittent contact** (re-solder the power/motor connector) — reliability priority #1.
2. **Electrical safety**: battery fuse, cut-off/emergency stop, 230 V protection (RCD).
3. **Energy autonomy**: suitable lead-acid charger; eventually, **voltage telemetry** (lead-acid sags).
4. **Real docking**: printing an AprilTag dock, `apriltag_ros → detected_dock_pose → approach` pipeline.
5. **Low obstacles**: add a low sensor / depth camera to complement the 2D LiDAR.
6. **Robustness**: automatic startup of the stack at boot (systemd service).

---

## 8. Technical skills applied
- **Mobile robotics**: differential kinematics, odometry, sensor fusion (EKF), SLAM, particle
  localization (AMCL), trajectory planning, obstacle avoidance (costmaps, DWB).
- **ROS 2**: nodes, topics, TF, QoS, lifecycle, parameters, RViz, micro-ROS, CycloneDDS.
- **Embedded systems**: Teensy/ARM Cortex-M7 microcontroller, real-time PID, PWM, I²C, quadrature
  encoders, Hall sensors, 3.3 V/5 V logic levels.
- **Electronics / electrical engineering**: BLDC motors, drivers, datasheet reading, measurements (multimeter),
  power diagnosis, electrical safety (lead-acid, 230 V).
- **Methodology**: bisection diagnosis (isolating hardware vs software), reproducible tests, systematic
  **technical documentation**, version control (Git).

---

## 9. Glossary
| Term | Definition |
|---|---|
| **AMR** | Autonomous Mobile Robot |
| **ROS 2** | Robot Operating System 2 — robotics middleware |
| **DDS / RMW** | ROS 2 real-time communication layer (CycloneDDS here) |
| **micro-ROS** | ROS 2 for microcontrollers (Teensy ↔ Pi bridge) |
| **SLAM** | Simultaneous Localization And Mapping |
| **AMCL** | Adaptive Monte Carlo Localization — particle-filter localization |
| **EKF** | Extended Kalman Filter — odometry + IMU fusion |
| **Costmap** | Cost grid representing the space (free / obstacle / margin) |
| **Inflation** | Cost halo around obstacles (planning margin) |
| **Footprint** | Ground footprint of the robot (collision shape) |
| **DWB** | Dynamic Window approach — Nav2 local controller |
| **TF** | Transform — frame tree (map → odom → base_link → sensors) |
| **BLDC** | Brushless DC — brushless direct-current motor |
| **Quadrature encoder** | 2-channel A/B sensor giving position + direction of rotation |
| **PID** | Proportional-Integral-Derivative controller |
| **AprilTag** | QR-code-like visual marker for localization/docking |

---

*For the detail of each point: `docs/hardware/`, `docs/software/navigation.md`,
`docs/history/diagnostics.md`, `scripts/COMMANDS.md`. Full history in the Git repository.*
