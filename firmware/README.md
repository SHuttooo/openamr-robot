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
| `config/lino_base_config.h` | this robot's pins, geometry (`LR_WHEELS_DISTANCE 0.46`), **tuned gains K_P 2.0 / K_I 0.10 / K_D 0.10**, `MOTOR2_GAIN 1.00`, IMU/driver selection |
| `lib/encoder/encoder.h` | `getRPM()` + `read()` (cumulative counts) used by the velocity estimator |
| `lib/pid/pid.h`, `lib/pid/pid.cpp` | explicit member init, `reset()`, **back-calculation anti-windup** (bleeds the integral on saturation, ≠ freeze) |
| `src/firmware.ino` | the whole velocity control chain (below) + `/debug/*` telemetry + `/debug/tune` live tuning + **watchdog** (deterministic full stop + PID reset) + **bounded** `/debug/openloop` + odometry first-dt guard |

## Velocity control chain (`firmware.ino`, tuned 2026-06-29)
Per wheel, at 50 Hz: `cmd_vel → kinematics → [feedforward + PID] → dither → PWM`, with the feedback
cleaned before it reaches the PID. Each stage fixes one measured problem (full story:
`docs/history/encoder-calibration.md`):
1. **Velocity estimator** (`VelEstimator`, 12-count window): velocity = Δcounts/Δt over a small fixed
   displacement → clean rpm even at low speed (instant getRPM = ±70% quantization noise below 5 rpm).
2. **Runtime ripple table** (`calib_rpm`, `LEFT_CAL/RIGHT_CAL[36]`): divides out the decentered-magnet
   ±40% 2/rev error. Loaded via `/debug/enc_cal` at runtime (the incremental encoder zero shifts each
   boot → a compiled table is phase-wrong). Re-align ~8 s/boot with `scripts/align_enc_cal.py`.
3. **Feedforward** (`KFF_DEFAULT 7.87` PWM/rpm + `FF_OFFSET_DEFAULT 21`): supplies the holding PWM →
   **same response at every speed** (the PID only trims the residual).
4. **PID** (Kp/Ki/Kd) + **back-calculation anti-windup** (`pid.cpp`).
5. **Anti-stiction dither** (`DITHER_DEFAULT 92` PWM, 25 Hz, **only <13 rpm**): breaks low-speed
   stick-slip → smooth down to ~0.06 m/s (docking). Off at cruise.

Live-tune via `/debug/tune` (Twist): `linear`=Kp,Ki,Kd · `angular.x`=R-gain · `angular.y`=Kff ·
`angular.z`=dither. Defaults above are compiled; live values are RAM-only.

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
