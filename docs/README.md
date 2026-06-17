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
  procedures/            <- how-to (step by step)
    running-the-robot.md
    safety.md
  history/               <- decisions & diagnostics (the "why")
    diagnostics.md
```

## Key conventions (know these right away)

- **MOTOR1 = LEFT wheel, MOTOR2 = RIGHT wheel.** (used everywhere)
- The **Teensy** handles motors + encoders + IMU. The **LiDAR** and **camera** are on the **Pi**.
- You talk to the robot through **ROS 2** (topics). The Pi↔Teensy link uses **micro-ROS**.
- Always use the **stable** serial paths `/dev/serial/by-id/...` (not `ttyACM0`/`ttyUSB0`, which can change).

## Project status (summary)

- ✅ Differential 2-wheel base, hardware base working.
- ✅ Right wheel: runaway fixed (motor-driver tuning).
- ✅ IMU repaired (it was an MPU6500, not an MPU6050).
- ✅ Real bring-up in a single launch (`/cmd_vel /odom /imu/data /scan` + TF).
- ⏳ Navigation (SLAM + Nav2): to be set up.
- ⏳ Camera: not configured yet.

---
*Last updated: 2026-06-17.*
