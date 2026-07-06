---
name: amr-min-velocity-floors
description: "Measured velocity floors (closed-loop sweep on the ground, scripts/min_velocity_sweep.py, 2026-07-02): LINEAR reliable floor 0.04 m/s (clean from 0.05), below = judder/stall; ANGULAR reliable floor 0.15 rad/s, below = stall/judder. Motor is WELL-SIZED (ratio ~1.0 above the floors); the floors are stick-slip + coarse Hall at low RPM, NOT a torque shortfall."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Empirical characterisation of the real robot's **velocity floors** (the "it doesn't like
low speed" feeling). Method: `scripts/min_velocity_sweep.py [linear|angular]` (run from the
PC), **robot ON THE GROUND (under load)**, commands `/cmd_vel` closed-loop (PID + dither, like
docking), measures the real velocity on `/odom/unfiltered`. See [[amr-pid-tuning]] and
[[amr-docking-bundle-setup]] (docking values).

## Measured floors (2026-07-02)
- **LINEAR**: 0.02 stalls · **0.03 = judder** (min 0, std 0.018) · **0.04 = reliable** (min 0.020) ·
  **0.05 = clean** (std 0.004) · 0.06–0.10 perfect (ratio ~1.0). → **reliable floor ≈ 0.04 m/s,
  CLEAN floor ≈ 0.05 m/s.**
- **ANGULAR**: 0.08 stalls · 0.10–0.12 judder (min 0, high std) · **0.15 = reliable** (min 0.093) ·
  0.20–0.30 perfect. → **reliable floor ≈ 0.15 rad/s.**

## Verdict: motor is WELL-SIZED (over-sized on torque)
- Motor **Z4BLD60-24GN-30S**: BLDC 60 W / 24 V / 3.8 A, 3000 rpm + **30:1** gearbox → ~100 rpm
  wheel (≈ **0.49 m/s max**), torque **~4.18 N·m/wheel** (huge). Wheel radius **0.046533 m**,
  track 0.4075 m. Specs in `docs/hardware/components-bom.md`.
- Above the floors, **real/commanded ratio ~1.0** → the motor tracks perfectly, no torque shortfall.
  The floors are **stick-slip (static friction) + coarse Hall commutation at low RPM** (docking runs
  at ~10–30 % of max speed). It's an **operating-point** problem, NOT a sizing one. (Also confirms
  the left wheel is healthy, cf openloop test — see [[amr-left-wheel-faux-contact]].)

## Docking consequences (keep commands ABOVE the floors) — applied in dock_trigger.py 2026-07-02
- **drive_speed 0.08** m/s → OK (well above 0.04).
- **Phase-5 taper + drive-to-point taper** floored at **0.05** m/s (was 0.07 / 0.03) — the lowest
  clean speed, soft touch. Hard-coded `v = max(0.05, ...)`.
- **scan_rotation_speed** lowered to **0.17 rad/s** (just above the 0.15 floor → slowest rotation
  still reliable = best tag visibility). Live-tunable.
- **Rotation stiction floor** added: new params `min_turn_omega 0.15` + `turn_deadband 0.04`. Yaw
  corrections below ~0.15 rad/s don't execute (stick-slip), so small non-zero corrections are snapped
  up to the floor and zeroed inside the deadband — fixes fine-alignment in Phase 5 (a "not straight"
  factor, on top of the noisy normal).
- **Judder at start** = static-friction breakaway on each start-from-standstill; the taper (never a
  full stop mid-dock) mitigates it; otherwise use the driver ACC/DEC ramp.
