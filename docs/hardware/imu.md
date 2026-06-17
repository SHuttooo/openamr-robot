# IMU (MPU6500)

*Last updated: 2026-06-17.*

## Overview
An inertial measurement unit (accelerometer + gyroscope) on the Teensy's I²C bus. Used to improve
heading (yaw) estimation for navigation.

> ⚠️ **Important**: the board was labeled / assumed to be an **MPU6050**, but it is actually an
> **MPU6500**. This caused a lot of confusion (see below).

| | |
|---|---|
| Chip | **MPU6500** (3-axis accel + 3-axis gyro) |
| Bus | I²C, address **0x68** (AD0 = GND) |
| `WHO_AM_I` (reg 0x75) | **0x70** (an MPU6050 would return 0x68) |
| Magnetometer | none (MPU6500 has no mag; the MPU9250 would) |

## Communication (I²C → Teensy)
- `SDA = pin 18`, `SCL = pin 19` (Teensy 4.0 default `Wire`).
- The Teensy is the I²C master; the IMU answers at 0x68.
- The firmware reads acceleration and rotation rate; it publishes `sensor_msgs/Imu` on **`/imu/data`**.

## Firmware driver — the fix
The linorobot2 **MPU6050** driver checks `WHO_AM_I == 0x68` and **rejects** our chip (which returns 0x70)
→ `setup()` used to hang (LED 3 blinks, no topics). The fix:

- Use **`USE_MPU9250_IMU`** in `lino_base_config.h` (instead of `USE_MPU6050_IMU`).
- The MPU9250 driver accepts it: it reads `WHO_AM_I` bits [6:1]; `0x70` → `0x38`, which its
  `testConnection()` accepts (`MPU9250.cpp`). The MPU6500 is register-compatible with the MPU9250 core
  (accel+gyro), so it works.

## Status (verified)
- ✅ `/imu/data` publishes **real data**: at rest, `linear_acceleration.z ≈ 9.74 m/s²` (gravity).
- The `linear_acceleration.x ≈ -2` at rest means the IMU is **mounted at a slight tilt** (to account for
  in the URDF later).

## Good to know / gotchas
- **No orientation**: the driver provides raw accel + gyro only; the orientation quaternion in
  `/imu/data` is all zeros (invalid). For sensor fusion (EKF / `robot_localization`), use the
  **angular velocity** (`angular_velocity.z`, yaw rate), not the orientation.
- There is a tiny standalone I²C scanner project on the Pi (`~/i2cscan`) to re-check the bus / address
  (`WHO_AM_I`) if needed.
- The firmware default scales: accel ±2 g (`1/16384`), gyro ±250 °/s (`1/131`).
