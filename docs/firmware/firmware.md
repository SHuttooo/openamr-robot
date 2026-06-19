# Firmware (Teensy) — structure, build, flash

*Last updated: 2026-06-17.*

## What it is
The Teensy runs **`linorobot2_hardware`** (upstream) + our configuration + debug additions. It is a
micro-ROS application: it connects to the agent on the Pi and exposes the robot's topics.

Source on the Pi: **`~/linorobot2_hardware`** (cloned from `github.com/linorobot/linorobot2_hardware`).

> ⚠️ **Not the official OpenAMR firmware.** The OpenAMR org has its own firmware repo
> (`openamr-platform-fw`) with its own interfaces/comm. Our robot runs **linorobot2_hardware + micro-ROS**
> instead. That's a deliberate, working choice for now — just don't confuse the two when reading the
> OpenAMR repos. (We *do* use the official `openamr-platform-sw` for navigation.)

## Repo structure (what matters)
```
linorobot2_hardware/
  config/
    lino_base_config.h   <- ALL our #defines (pins, PID, geometry, IMU, baud)
    config.h             <- includes lino_base_config.h
  firmware/
    platformio.ini       <- build config (env teensy40)
    src/firmware.ino     <- main program (setup + loop + ROS entities)
    lib/
      encoder/  motor/  pid/  kinematics/  odometry/  imu/  ...
```

## Our configuration (`config/lino_base_config.h`)
Key values for THIS robot (differ from upstream defaults):

| #define | Value | Why |
|---|---|---|
| `LINO_BASE` | `DIFFERENTIAL_DRIVE` | 2 driven wheels |
| `USE_GENERIC_2_IN_MOTOR_DRIVER` | — | PWM + 2 direction pins |
| `USE_MPU9250_IMU` | — | the IMU is an **MPU6500** (see [imu](../hardware/imu.md)) |
| `K_P / K_I / K_D` | `0.3 / 0.15 / 0.25` | PID; K_I lowered + anti-windup added |
| `MOTOR_MAX_RPM` | `80` | |
| `MOTOR_OPERATING_VOLTAGE` / `MOTOR_POWER_MAX_VOLTAGE` | `24` / `24` | |
| `COUNTS_PER_REV1/2` | `1024` | encoder CPR |
| `WHEEL_DIAMETER` | `0.2` | |
| `LR_WHEELS_DISTANCE` | `0.46` | measured 2026-06-19 (was 0.45) |
| `PWM_FREQUENCY` | `3000` | |
| `MOTOR1_ENCODER_INV` / `MOTOR2_INV` | `true` / `true` | sign conventions |
| `MOTOR1_PWM / IN_A / IN_B` | `1 / 20 / 21` | LEFT |
| `MOTOR2_PWM / IN_A / IN_B` | `5 / 6 / 8` | RIGHT |
| `BAUDRATE` | `115200` | **must match the agent** |

> ⚠️ The PID/`_INV` values were originally *reconstructed* (not read from the real binary). They have
> been validated empirically, but cross-check against the real thesis source if/when available.

## Build (on the Pi)
PlatformIO runs from its own venv (`penv`) to avoid the Ubuntu 24.04 PEP 668 restriction:
```bash
cd ~/linorobot2_hardware/firmware
ROS_DISTRO=jazzy ~/.platformio/penv/bin/pio run -e teensy40
# helper: bash ~/build_fw.sh
```
First build ≈ 5 min (compiles micro-ROS); incremental ≈ 8 s.

## Flash (on the Pi)
The Teensy CLI loader is installed (`teensy_loader_cli`) and the PJRC udev rules are in
`/etc/udev/rules.d/00-teensy.rules`. Robust sequence (stop the agent first to free the port):
```bash
pkill micro_ros_agent
HEX=~/linorobot2_hardware/firmware/.pio/build/teensy40/firmware.hex
sudo teensy_loader_cli --mcu=TEENSY40 -s -w -v $HEX     # -s = soft reboot into bootloader
# if it says "error writing" then it is in HalfKay; retry once WITHOUT -s:
sudo teensy_loader_cli --mcu=TEENSY40 -w -v $HEX
```
Then restart the agent (or the bring-up launch).

> Full setup history (why penv, why teensy_loader_cli, udev) is in [../history/diagnostics.md](../history/diagnostics.md).

## Related
- Control loop & PID: [control-loop-pid.md](control-loop-pid.md).
- Debug topics & open-loop mode: [debug-telemetry.md](debug-telemetry.md).
