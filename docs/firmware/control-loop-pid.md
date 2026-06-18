# Control loop & PID

*Last updated: 2026-06-18.*

> ✅ **PID re-tuned 2026-06-18 (step-response method).** The wheels used to not reach the commanded speed
> (~-26% steady-state error, ~2.9 s rise). Root cause: **K_I far too low (0.15)**. New gains
> **K_P 0.6 / K_I 0.35 / K_D 0.15** → steady-state error ~±2 %, rise ~1 s (≈2.4× faster). Method: command a
> `/cmd_vel` step (0.25 m/s ≈ 24 rpm) and record `/debug/left|right` (target rpm x, measured rpm y) at
> 50 Hz; judge rise time / overshoot / steady-state error. Test at ≥0.25 m/s (at 0.15 m/s the rpm
> measurement is quantized by ~2.9 rpm ≈ 20 %, too coarse to tune).
>
> ⚠️ **Two gotchas found while tuning:**
> 1. **`pio run -e teensy40` uses `config/lino_base_config.h`, NOT `custom/dev_config.h`** — the
>    `USE_DEV_CONFIG` flag is only on the `[env:dev]` env. Edit `lino_base_config.h` (the real config).
> 2. **The PID isn't the only loop** — the ZBLD drivers regulate internally (VAR gain + ACC/DEC ramp).
>    Open-loop (fixed PWM via `/debug/openloop`) the wheel breaks free after ~0.4 s of stiction then holds
>    speed quickly. The residual **right-wheel overshoot/ringing** is its different driver/motor dynamics.
> - Remaining: stiction dead-time (~0.4 s) → would need **feedforward** in firmware for a straight start;
>   right-wheel ringing → balance the right driver pots (VAR/ACC-DEC) or filter the rpm measurement.

## The 50 Hz loop (`firmware.ino`)
A ROS timer fires every **20 ms** → `controlCallback` → `moveBase()` then `publishData()`.

### `moveBase()` data flow
```
/cmd_vel (Twist)
   │
   ▼
kinematics.getRPM(vx, vy, wz) ─► target rpm per wheel  (motor1 = LEFT, motor2 = RIGHT)
   │                                   ▲
   │  encoders.getRPM() ───────────────┘ measured rpm
   ▼
pid.compute(target, measured) ─► PWM ─► motor.spin() ─► driver ─► wheel
   │
   ▼
kinematics.getVelocities(rpm1, rpm2) ─► measured vx, wz
   │
   ▼
odometry.update() ─► /odom/unfiltered     (pose integrated here)
```

### Differential kinematics (key facts)
- For pure forward motion, **both wheels get the same target** (`motor1 = motor2 = x_rpm`).
- Per-wheel reconstruction from `/odom/unfiltered` (here **0.45 = `LR_WHEELS_DISTANCE`, the wheel
  separation / track — NOT the wheel diameter, which is 0.2 m**):
  ```
  v_right = twist.linear.x + twist.angular.z * (LR_WHEELS_DISTANCE / 2)   # 0.45 / 2
  v_left  = twist.linear.x - twist.angular.z * (LR_WHEELS_DISTANCE / 2)
  ```
- `max_rpm = (V_power / V_operating) × MOTOR_MAX_RPM × MAX_RPM_RATIO`. With real 24 V power,
  `MOTOR_POWER_MAX_VOLTAGE` must be **24** (otherwise the RPM ceiling is halved).

## PID (`lib/pid/pid.cpp`)
- One PID per wheel: `pid = Kp·e + Ki·∫e + Kd·Δe`, output clamped to `[PWM_MIN, PWM_MAX]`.
- Gains (tuned 2026-06-18): `K_P=0.6, K_I=0.35, K_D=0.15` (was 0.3 / 0.15 / 0.25 — K_I was too low).
- ⚠️ The **upstream PID had no anti-windup** (the integral was unbounded). We **added integral clamping**
  so `Ki·integral` cannot exceed the output range — this prevents the integral "catapult" that amplified
  the right-wheel instability. We also lowered `K_I` (0.4 → 0.15) to damp the loop.

## Safety
- **Command watchdog**: if no `/cmd_vel` for **200 ms**, the firmware sets the twist to zero → motors stop.
  This is your software safety net; it works even if the publisher dies.

## History context
The right wheel's bad behaviour was **not** the PID itself — it was driver tuning (pots). But the missing
anti-windup made it worse. See [../history/diagnostics.md](../history/diagnostics.md) for the full reasoning.
