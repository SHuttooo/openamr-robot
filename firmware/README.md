# OpenAMRobot firmware overlay (Teensy 4.0)

Reproducibility (Raj review PR5): this is an **overlay** on the upstream Linorobot2 firmware, pinned
to an exact commit. A clean checkout + this overlay reproduces the flashed artifact.

## Pinned upstream
| Item | Value |
|---|---|
| Repo | `https://github.com/linorobot/linorobot2_hardware.git` |
| Branch | `jazzy` |
| Commit | `aaf9d59` ("move wifi config to #include file thats gitignored") |
| Board / framework | PlatformIO `teensy` / `arduino`, env `teensy40` |
| micro-ROS distro | `jazzy` (`board_microros_distro = ${sysenv.ROS_DISTRO}`) |

## What this overlay changes (vs upstream)
The files in this directory replace the upstream ones:

| File | Why |
|---|---|
| `config/lino_base_config.h` | this robot's pins, geometry (`LR_WHEELS_DISTANCE 0.46`), PID gains, `MOTOR2_GAIN`, IMU/driver selection |
| `lib/encoder/encoder.h` | **period-method `getRPM()`** — fine low-speed resolution (was a 0/3/6 staircase) |
| `lib/pid/pid.h`, `lib/pid/pid.cpp` | explicit member init, `reset()`, **saturation-aware anti-windup** |
| `src/firmware.ino` | `/debug/*` telemetry + `/debug/tune` live tuning; **watchdog = deterministic full stop + PID reset**; **bounded** `/debug/openloop`; odometry first-dt guard |

## Apply + build + flash (on the Pi)
```bash
bash apply_overlay.sh              # clone upstream @aaf9d59 (if needed) + copy this overlay over it
cd ~/linorobot2_hardware/firmware
ROS_DISTRO=jazzy ~/.platformio/penv/bin/pio run -e teensy40        # build
pkill -9 -f micro_ros_agent                                        # free the serial port
sudo teensy_loader_cli --mcu=TEENSY40 -s -w \
    .pio/build/teensy40/firmware.hex                               # flash (-s then re-run if needed)
```

## CI (recommended next step)
A GitHub Action that, on push: checks out upstream `@aaf9d59`, applies this overlay, runs
`pio run -e teensy40`, and uploads `firmware.hex` as an artifact. Not yet wired — the build command
above is the manual equivalent.
