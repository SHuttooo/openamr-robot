# Control loop & PID

*Last updated: 2026-06-17.*

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
- Gains: `K_P=0.3, K_I=0.15, K_D=0.25`.
- ⚠️ The **upstream PID had no anti-windup** (the integral was unbounded). We **added integral clamping**
  so `Ki·integral` cannot exceed the output range — this prevents the integral "catapult" that amplified
  the right-wheel instability. We also lowered `K_I` (0.4 → 0.15) to damp the loop.

## Safety
- **Command watchdog**: if no `/cmd_vel` for **200 ms**, the firmware sets the twist to zero → motors stop.
  This is your software safety net; it works even if the publisher dies.

## History context
The right wheel's bad behaviour was **not** the PID itself — it was driver tuning (pots). But the missing
anti-windup made it worse. See [../history/diagnostics.md](../history/diagnostics.md) for the full reasoning.
