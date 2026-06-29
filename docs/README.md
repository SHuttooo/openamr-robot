# Documentation — AMR Robot (OpenAMR / linorobot2)

> Onboarding documentation for a student joining the project.
> **Keep it up to date** as the project progresses (each file has a "Last updated" date).

## Where to start

1. **[00-overview.md](00-overview.md)** — what the robot is, the overall architecture, the layer diagram.
2. **[01-communication.md](01-communication.md)** — **precise map of ALL communication** (physical buses, protocols, baud rates, ROS topics + types + frames). Read this early.
3. Then the per-topic sheets below, depending on what you need to work on.

## File tree

```
docs/
  README.md              <- this file (index)
  00-overview.md         <- overview + architecture
  01-communication.md    <- all communications (buses, protocols, topics)
  hardware/              <- one sheet per physical component
    raspberry-pi.md
    teensy.md
    motors-drivers.md
    motor-driver-fault-codes.md  <- ZBLD.C20 LED blink codes (red LED = fault, e.g. code 10 = under-voltage)
    encoders.md
    imu.md
    lidar.md
    camera.md
    power.md
    wiring-pinout.md
  firmware/              <- code running on the Teensy
    firmware.md
    control-loop-pid.md
    debug-telemetry.md
  software/              <- Raspberry Pi side (ROS 2)
    ros-architecture.md
    bringup.md
    navigation.md
    visualization.md     <- RViz/rqt from the Ubuntu dev PC (domain, RMW, compressed camera)
  procedures/            <- how-to (step by step)
    running-the-robot.md       <- base robot quick-start (bring-up, teleop, SLAM, firmware flash)
    real-robot-runbook.md      <- full Nav2 navigation stack + troubleshooting (current reference)
    safety.md
  history/               <- decisions, diagnostics, reports (the "why")
    diagnostics.md
    rapport-stage-technique.md <- technical internship report (FR, historical)
```

> **Two procedure docs, by purpose:** [`running-the-robot.md`](procedures/running-the-robot.md) is the
> quick-start for the **base robot** (bring-up, teleop, SLAM, firmware). [`real-robot-runbook.md`](procedures/real-robot-runbook.md)
> is the **full autonomous-navigation (Nav2) runbook** with every pitfall and fix — use it for navigation.

## Key conventions (know these right away)

- **MOTOR1 = LEFT wheel, MOTOR2 = RIGHT wheel.** (used everywhere)
- The **Teensy** handles motors + encoders + IMU. The **LiDAR** and **camera** are on the **Pi**.
- You talk to the robot through **ROS 2** (topics). The Pi↔Teensy link uses **micro-ROS**.
- Always use the **stable** serial paths `/dev/serial/by-id/...` (not `ttyACM0`/`ttyUSB0`, which can change).

## Project status (summary)

- ✅ Differential 2-wheel base, hardware base working.
- ✅ Right wheel: runaway fixed (motor-driver tuning).
- ✅ IMU repaired (it was an MPU6500, not an MPU6050).
- ✅ Real bring-up in a single launch (`/cmd_vel /odom /imu/data /scan /scan_filtered /camera/*` + TF).
- ✅ **Odometry EKF** (`robot_localization`): wheels + IMU gyro Z fused → `/odom`.
- ✅ **LiDAR body filter** → `/scan_filtered` (robot chassis masked).
- ✅ **SLAM** (`slam_toolbox`) builds & saves maps (current working map `~/maps/piece_actuelle`).
- ✅ **Camera working** (IMX708 NoIR via the **Raspberry Pi libcamera fork** — the apt one doesn't support it).
  Viewed over WiFi via `web_video_server` (MJPEG in a browser), not RViz — see the runbook §8b.
- ✅ Remote visualization from an Ubuntu desktop (RViz/rqt, domain 0, CycloneDDS, same subnet).
- ✅ **Nav2 + AMCL integrated** (`openamr-platform-sw`, deployed on the Pi as `~/openamr-integration`):
  localization + planner + DWB + RotationShim, footprint/inflation/speed tuned. See
  [real-robot-runbook.md](procedures/real-robot-runbook.md). *Real-robot validation pending a power fix
  (see below).*
- ✅ **Motor velocity loop fully tuned (2026-06-29).** Feedforward (`PWM=Kff*target+PID`) → same response
  at every speed; back-calculation anti-windup; small-window velocity estimator; **anti-stiction dither**
  → smooth down to ~0.06 m/s. Final gains baked in firmware (Kp 2.0 / Ki 0.10 / Kd 0.10, Kff 7.87,
  dither 92). The "left wheel oscillation" was a **decentered encoder magnet** (±40% 2/rev ripple),
  corrected by a **runtime ripple table** re-aligned in ~8 s per boot (`align_enc_cal.py`). See
  [history/encoder-calibration.md](history/encoder-calibration.md) and the diagnostics journal §13.
- ⏳ Camera **calibration** (needed before AprilTag docking).
- ⚠️ **Power blocker:** the Pi browns out under load (24 V→5 V DC-DC undersized / battery low). The robot
  cannot run until the power path is fixed — see runbook §14.
- ⚠️ Per-boot ritual: the encoder ripple table lives in RAM → run `align_enc_cal.py` after each Teensy
  power-cycle (see running-the-robot §4b).

---
*Last updated: 2026-06-29.*
