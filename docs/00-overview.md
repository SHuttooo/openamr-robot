# 00 — Overview & architecture

*Last updated: 2026-06-18.*

## What is this robot?

An **Autonomous Mobile Robot (AMR)** with **differential drive**: two independently driven wheels
(left + right); it turns by spinning the wheels at different speeds. It comes from a thesis (BHT Berlin),
**OpenAMR** platform, built on the **linorobot2** software stack.

End goal: autonomous navigation (mapping, localization, goal-driven motion, docking).

> **Scope of this documentation.** This describes **our specific robot** (a thesis/BHT build on the
> OpenAMR platform), i.e. what is *actually* wired and running on our unit. The official OpenAMR repos
> (`github.com/openAMRobot`) describe a broader, evolving platform and **conflate several hardware
> configurations** — treat them as a reference, not as the spec of this exact robot. One concrete
> difference to keep in mind:
> - **Firmware**: our robot runs **`linorobot2_hardware` + micro-ROS**, *not* the official
>   `openamr-platform-fw`. (We do use the official **`openamr-platform-sw`** for navigation.)

## The two "brains"

The robot has **two computers** that share the work:

| | **Raspberry Pi 5** | **Teensy 4.0** |
|---|---|---|
| Role | high-level "brain" | low-level real-time |
| Runs | ROS 2 Jazzy, navigation, USB/CSI sensors | motor/encoder/IMU loop @ 50 Hz |
| Handles | LiDAR, camera, high-level odometry, Nav2 | motor PWM, encoder reading, PID, IMU |
| OS / language | Ubuntu 24.04 / Python + C++ (ROS 2) | C++ firmware (Arduino/PlatformIO) |

**Golden rule:** the Teensy ONLY does motors + encoders + IMU. The LiDAR and camera are wired to the
**Pi** (the Teensy is not involved for them).

## Layer diagram

```
                      ┌─────────────────────────────────────────────┐
                      │                RASPBERRY PI 5                 │
                      │  ROS 2 Jazzy                                  │
                      │                                               │
   LiDAR  ─USB────────┤  rplidar_ros ──► /scan ──► scan_body_filter ──► /scan_filtered │
   Camera ─CSI────────┤  camera_ros (RPi libcamera fork) ──► /camera/image_raw │
                      │                                               │
                      │  micro-ROS agent ◄──USB──► Teensy             │
                      │      ▲ /cmd_vel        │ /odom/unfiltered,     │
                      │      │                 ▼ /imu/data, /debug/*   │
                      │  EKF (robot_localization) ──► /odom + TF odom→base_link │
                      │  slam_toolbox ──► /map + TF map→odom           │
                      │  Nav2 / AMCL (TODO) ──► /cmd_vel               │
                      └───────────────────────┬───────────────────────┘
                                              │ USB (micro-ROS, 115200)
                      ┌───────────────────────┴───────────────────────┐
                      │                  TEENSY 4.0                     │
                      │  50 Hz loop: cmd_vel → kinematics → PID →       │
                      │  motor PWM ; read encoders ; read IMU           │
                      └──┬──────────┬──────────┬───────────┬────────────┘
                         │PWM+dir   │quadrature│ I2C       │
                      ┌──┴───┐  ┌───┴────┐  ┌──┴────┐   (3.3V logic)
                      │Driver│  │Encoder │  │ IMU   │
                      │ ZBLD │  │ AS5040 │  │MPU6500│
                      └──┬───┘  └────────┘  └───────┘
                         │ 3 phases U/V/W
                      ┌──┴───┐
                      │Motor │ BLDC 24V  ×2 (left + right)
                      └──────┘
```

## Physical characteristics

| Quantity | Value |
|---|---|
| Type | differential, 2 driven wheels |
| Wheel diameter | **0.2 m** |
| Wheel separation (left–right) | **0.46 m** (measured 2026-06-19; `LR_WHEELS_DISTANCE`) |
| Robot footprint | **0.78 × 0.58 m** rectangle, rounded corners (base_link offset: front 0.415 / rear −0.365) |
| Motor voltage | **24 V** |
| Encoders | 1024 counts/rev, quadrature A/B |

> ⚠️ The OpenAMR simulation uses a different geometry (Ø 0.22 / separation 0.4075). The robot's real
> values are **Ø 0.2 / 0.45**. Don't mix them up during odometry calibration.

## Component list (detailed sheets)

| Component | Model | Sheet |
|---|---|---|
| Computer | Raspberry Pi 5 | [hardware/raspberry-pi.md](hardware/raspberry-pi.md) |
| Microcontroller | Teensy 4.0 | [hardware/teensy.md](hardware/teensy.md) |
| Motors | BLDC ZD 60_200W ×2 | [hardware/motors-drivers.md](hardware/motors-drivers.md) |
| Motor drivers | ZBLD C20-120L2R ×2 | [hardware/motors-drivers.md](hardware/motors-drivers.md) |
| Encoders | AS5040 magnetic, 1024 CPR | [hardware/encoders.md](hardware/encoders.md) |
| IMU | **MPU6500** (thought to be MPU6050) | [hardware/imu.md](hardware/imu.md) |
| LiDAR | RPLidar (on the Pi's USB) | [hardware/lidar.md](hardware/lidar.md) |
| Camera | Pi Camera Module 3 **NoIR** (IMX708) — **working** via RPi libcamera fork | [hardware/camera.md](hardware/camera.md) |
| Power | 24 V (AC/DC converter) | [hardware/power.md](hardware/power.md) |

## Software stack

- **Pi**: Ubuntu Server 24.04 + **ROS 2 Jazzy**. micro-ROS agent workspace in `~/linorobot2_ws`.
- **Teensy firmware**: `linorobot2_hardware` (PlatformIO, env `teensy40`) + our config + debug additions.
- **Navigation (target)**: `openamr-platform-sw` (Nav2, SLAM, docking) — see [software/navigation.md](software/navigation.md).

To understand how everything talks → **[01-communication.md](01-communication.md)**.
