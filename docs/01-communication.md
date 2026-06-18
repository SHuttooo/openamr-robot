# 01 — Communication (buses, protocols, topics)

*Last updated: 2026-06-17.*

This file describes **precisely** how each element talks to the others: the **physical bus**, the
**protocol**, the **rate/baud**, and on the ROS side the **topics + message types + frames**.

---

## 1. Physical links overview

| Link | Physical bus | Protocol | Rate | Detail |
|---|---|---|---|---|
| Pi ↔ Teensy | **USB** (CDC ACM) | **micro-ROS** (XRCE-DDS over serial) | **115200 baud** | `/dev/ttyACM0` |
| Teensy ↔ IMU | **I²C** | I²C master (Teensy) | 100 or 400 kHz | address **0x68** |
| Teensy ↔ encoders | **GPIO** | **quadrature A/B** (incremental) | — | interrupts |
| Teensy ↔ drivers | **GPIO** | **PWM + 2 direction lines** | PWM 3 kHz | per motor |
| Pi ↔ LiDAR | **USB** (CP2102 UART bridge) | **RPLIDAR** serial protocol | **115200 baud** | `/dev/ttyUSB0` |
| Pi ↔ Camera | **CSI** (MIPI ribbon) | libcamera / CSI | — | not USB |
| ROS internal (on the Pi) | localhost | **DDS** (Fast DDS) | — | default RMW |

> ⚠️ **Common ground is mandatory**: the drivers' `COM` must be tied to the **Teensy GND**, otherwise
> the PWM/direction signals and the encoders pick up noise. (see [history/diagnostics.md](history/diagnostics.md))

---

## 2. Pi ↔ Teensy link (micro-ROS) — the core

This is **the** link that turns the Teensy into a "ROS node".

- **Physical**: USB cable from the Teensy to a Pi USB port → shows up as `/dev/ttyACM0`.
  - **Stable** path: `/dev/serial/by-id/usb-Teensyduino_USB_Serial_16778200-if00`.
- **Protocol**: **micro-ROS**, which uses **XRCE-DDS** (a lightweight DDS for microcontrollers)
  encapsulated over the serial link. The Teensy is the **client**, the Pi runs the **agent**.
- **Baud**: **115200** (set by `#define BAUDRATE 115200` in the firmware; the agent must be started with
  the **same** `-b 115200`, otherwise no connection at all).
- **Start the agent** (on the Pi):
  ```bash
  ros2 run micro_ros_agent micro_ros_agent serial -b 115200 \
    -D /dev/serial/by-id/usb-Teensyduino_USB_Serial_16778200-if00
  ```
- Without the agent running, the Teensy publishes into the void: **no topics** appear on the Pi.

### Topics exchanged over micro-ROS (Teensy ⇄ agent)

| Topic | Type | Direction (Teensy's view) | QoS | Purpose |
|---|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | **subscribes** (in) | reliable | velocity command (linear x, angular z) |
| `/odom/unfiltered` | `nav_msgs/msg/Odometry` | **publishes** (out) | reliable | wheel odometry (velocities + integrated pose) |
| `/imu/data` | `sensor_msgs/msg/Imu` | **publishes** (out) | reliable | accel + gyro (MPU6500) |
| `/debug/left` | `geometry_msgs/msg/Vector3` | publishes (out) | **best-effort** | left: x=target rpm, y=measured rpm, z=raw counts |
| `/debug/right` | `geometry_msgs/msg/Vector3` | publishes (out) | **best-effort** | right: same |
| `/debug/pwm` | `geometry_msgs/msg/Vector3` | publishes (out) | **best-effort** | x=left PWM, y=right PWM |
| `/debug/openloop` | `geometry_msgs/msg/Vector3` | **subscribes** (in) | reliable | x=PWM applied to BOTH motors open-loop (test) |

> ⚠️ **QoS**: the published `/debug/*` topics are **best-effort**. To read them in Python, the subscriber
> must ALSO be best-effort, otherwise "incompatible QoS, no messages received".

The control loop (kinematics + PID) runs at **50 Hz** (20 ms timer) → these topics publish at ~50 Hz.
Safety: if no `/cmd_vel` is received for **200 ms**, the firmware zeroes the motors (watchdog).

---

## 3. Internal Teensy links

### Teensy ↔ IMU (I²C)
- **I²C** bus: `SDA = pin 18`, `SCL = pin 19` (Teensy 4.0 default Wire).
- Address **0x68** (AD0 to ground). `WHO_AM_I` (register 0x75) = **0x70** → this is an **MPU6500**.
- The firmware reads accelerometer + gyroscope (no magnetometer). See [hardware/imu.md](hardware/imu.md).

### Teensy ↔ encoders (quadrature)
- Digital **A/B** quadrature signals, read via interrupts.
- Left (MOTOR1): `A = pin 14, B = pin 15`. Right (MOTOR2): `A = pin 11, B = pin 12`.
- 1024 counts/rev × quadrature decoding. See [hardware/encoders.md](hardware/encoders.md).

### Teensy ↔ motor drivers (PWM + direction)
Per motor, 3 logic wires:
- `PWM` (speed, PWM signal); `IN_A` (= FWD/forward); `IN_B` (= REV/reverse).
- Left: `PWM=pin 1, IN_A=pin 20, IN_B=pin 21`. Right: `PWM=pin 5, IN_A=pin 6, IN_B=pin 8`.
- On the driver side, the speed input is `VAR/AI2` (PWM 3–10 kHz or 0–5 V), the direction is `FWD/DI1`
  & `REV/DI2`, and `COM` = common ground (tie to Teensy GND). See [hardware/motors-drivers.md](hardware/motors-drivers.md).

---

## 4. Pi side (ROS 2)

### Topics produced on the Pi (in addition to the Teensy's)
| Topic | Type | Produced by | Frame |
|---|---|---|---|
| `/odom` | `nav_msgs/msg/Odometry` | **`ekf_filter_node`** (robot_localization; fuses wheels + IMU yaw) | odom → base_link |
| `/scan` | `sensor_msgs/msg/LaserScan` | `rplidar_ros` | lidar_link |
| `/scan_filtered` | `sensor_msgs/msg/LaserScan` | **`scan_body_filter.py`** (masks robot body) | lidar_link |
| `/map` | `nav_msgs/msg/OccupancyGrid` | `slam_toolbox` | map |
| `/camera/image_raw` (+ `/compressed`) | `sensor_msgs/Image`, `CompressedImage` | `camera_ros` (RPi libcamera fork) | camera_optical_frame |
| `/camera/camera_info` | `sensor_msgs/msg/CameraInfo` | `camera_ros` | camera_optical_frame |

> ⚠️ **Camera bandwidth**: `/camera/image_raw` is ~2.76 MB/frame (1280×720). Over WiFi, always use the
> **`compressed`** topic; never subscribe to raw remotely (it lags the whole network). See
> [hardware/camera.md](hardware/camera.md).

### Transform tree (TF)
```
map ──(slam_toolbox)──► odom ──(ekf_filter_node)──► base_link ──(static)──► lidar_link
                                                            ├──(static)──► imu_link
                                                            ├──(static)──► base_footprint
                                                            └──(static)──► camera_link ──► camera_optical_frame
```
- `odom → base_link`: published by the **EKF** (`robot_localization`), fusing wheel odom + IMU yaw rate.
- `base_link → lidar_link`: **static**, measured: x=0.335, y=0, z=0.18, **yaw=π** (LiDAR mounted rotated 180°).
- `base_link → camera_link → camera_optical_frame`: static, x=0.415/z=0.12, then optical convention.
- `map → odom`: from `slam_toolbox` (mapping). AMCL will provide it later for pure localization.

### DDS middleware & remote visualization
- ROS 2 uses an **RMW** (DDS layer). **Fast DDS** (default), **`ROS_DOMAIN_ID = 0`** (Pi has neither set).
- To view the Pi's topics from the **Ubuntu dev PC** (native RViz/rqt): same **domain 0**, same **Fast DDS**,
  and **same LAN subnet** (Fast DDS discovery is multicast → does not cross a router). On Ubuntu run
  `export ROS_DOMAIN_ID=0` (this desktop defaults to 42). See [software/visualization.md](software/visualization.md).
- ⚠️ OpenAMR's guide suggests CycloneDDS (domain 30); we are **not** using that. If we switch RMW later,
  **all** nodes (incl. the dev PC) must use the same one.

---

## 5. "Who talks to whom" recap

```
cmd_vel (Twist) ──► [agent] ──USB/micro-ROS──► [Teensy] ──PWM/dir──► [drivers] ──U/V/W──► [motors]
                                                  │
[encoders] ──quadrature──► [Teensy] ──► /odom/unfiltered ──► [odom_tf_relay] ──► /odom + TF
[IMU MPU6500] ──I2C 0x68──► [Teensy] ──► /imu/data
[LiDAR] ──USB/UART──► [rplidar_ros] ──► /scan ──► (filter) ──► /scan_filtered ──► [Nav2]
[Nav2] ──► /cmd_vel  (closed navigation loop)
```
