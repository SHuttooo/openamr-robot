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

## What is a "quadrature" encoder? (quick primer)
An encoder measures wheel rotation. This one outputs **two square-wave signals, A and B, shifted 90°
apart** — that 90° shift is the "quadrature". As the wheel turns:
```
forward:               reverse:
A ┌─┐ ┌─┐ ┌─┐          A ┌─┐ ┌─┐ ┌─┐
  ┘ └─┘ └─┘ └            ┘ └─┘ └─┘ └
B   ┌─┐ ┌─┐ ┌─┐       B ┌─┐ ┌─┐ ┌─┐
  ──┘ └─┘ └─┘            ┘ └─┘ └─┘ └
   (A leads B)            (B leads A)
```
- **Count the edges** of A and B → **position** (more rotation = more counts).
- **Which signal leads** (A-before-B vs B-before-A) → **direction**.
- It is **incremental** (relative counts, not an absolute angle).
- 1024 counts/rev, and counting all edges of both channels gives **×4** resolution.
- "Magnetic" (AS5040): a magnet on the shaft + a sensor chip that generates the A/B pulses.

### "Hall" vs "quadrature" — not a contradiction
- **Quadrature** = the *output signal type* (A/B, 90° apart).
- **Hall-effect** = the *sensing technology* (reading a magnetic field).
The AS5040 **senses magnetically (Hall-array)** and **outputs quadrature** — both terms apply.

⚠️ **Two different "Hall" on this robot, don't confuse them:**
1. **Wheel encoder (AS5040)**: Hall-based magnetic sensing → **quadrature A/B output** → read by the
   **Teensy** for odometry/PID. **1024 counts/rev.**
2. **BLDC motor commutation Hall sensors** (3 per motor) → read by the **ZBLD driver** to commutate the
   motor phases (this is what "driver closed loop" refers to). The Teensy never sees these.

What tells them apart: **1024 counts/rev**. Commutation Hall sensors are very coarse (a few transitions
per rev) — they could never give 1024. That resolution means a real incremental encoder (AS5040). And it
is functionally confirmed: the firmware decodes clean A/B quadrature and the counts increment correctly.

> Note: the exact chip (AS5040) comes from the project brief; not physically re-verified on the board.
> The *behaviour* (A/B quadrature, 1024 CPR) is verified.

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
