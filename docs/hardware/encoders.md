# Encoders (AS5040)

*Last updated: 2026-06-17.*

## Overview
Magnetic incremental encoders, one per wheel, that let the Teensy measure each wheel's rotation
(for speed feedback in the PID and for odometry).

| | |
|---|---|
| Type | AS5040 magnetic, quadrature A/B |
| Resolution | **1024 counts/rev** (`COUNTS_PER_REV` in firmware) |
| Logic level | 3.3 V |

## Communication (quadrature → Teensy)
Two digital signals **A** and **B** in quadrature, read by the Teensy on **interrupt** pins. The phase
relationship between A and B gives direction; counting edges gives position.

| Encoder | A pin | B pin |
|---|---|---|
| LEFT (MOTOR1) | **14** | **15** |
| RIGHT (MOTOR2) | **11** | **12** |

In the firmware:
- `encoder.read()` → raw absolute count (int32).
- `encoder.getRPM()` → speed in RPM (from count delta / time).
- The sign is configured by `MOTOR1_ENCODER_INV` / `MOTOR2_ENCODER_INV` so that **forward = positive**.

## Status (verified)
- ✅ Both encoders count correctly (proven by hand-spin tests).
- ✅ Direction sign correct on both sides (forward → counts increase, measured speed positive).
- ✅ Under power they read real motion cleanly (no electrical glitch/dropout).

So the encoders are **healthy** — they were wrongly suspected early on; the real issues were elsewhere
(driver tuning). See [history/diagnostics.md](../history/diagnostics.md).

## Good to know / gotchas
- ⚠️ **CPR vs wheel**: `COUNTS_PER_REV = 1024` is the encoder's counts/rev. If there is a **gearbox**
  between motor and wheel, the counts per **wheel** revolution = encoder CPR × quadrature × gear ratio.
  This must be verified for accurate odometry (to be checked on the real robot).
- Raw counts are visible live on `/debug/left` and `/debug/right` (field `z`). See
  [firmware/debug-telemetry.md](../firmware/debug-telemetry.md).
