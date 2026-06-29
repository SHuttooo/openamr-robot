# Encoder velocity-ripple investigation + the motor velocity control chain

*2026-06-29. Full record so the session isn't lost. Data: `docs/data/encoder_calib_*.json`.*
*Sections 1–7 = the investigation (how we got here). The TL;DR below = the final, flashed result.*

## TL;DR — the final velocity control chain (firmware, 50 Hz, per wheel)

```
                          ┌─────────────────── FEEDBACK (cleaned) ───────────────────┐
                          │                                                          │
  /cmd_vel ──► kinematics ──► (3) FEEDFORWARD ──┐                                    │
   (m/s)       target_rpm      Kff·rpm+offset   │                                    │
                                                ▼                                    │
                                          ┌──────────┐   (4)PID   ┌──────┐  (5)      │
                          measured_rpm ──►│  error   ├──► Kp/Ki/Kd├─► + ◄─┤ DITHER   │
                                ▲         └──────────┘  +back-calc└──┬───┘ ±92@25Hz  │
                                │                        anti-windup │    (<13rpm)   │
                                │                                    ▼               │
                                │                              constrain ──► PWM ──► MOTOR
                                │                                                    │
                                │   (2) ripple    (1) small-window         encoder ◄─┘
                                └── table ◄─────── velocity estimator ◄──── counts
                                    /CAL[angle]    Δcounts/Δt (12 counts)
```

Each block fixes ONE measured problem. Signal-flow order = the numbers:

| # | Block | What it does | Why (the problem it kills) | Value |
|---|---|---|---|---|
| 1 | **Velocity estimator** | rpm = Δcounts/Δt over a fixed 12-count window | instant getRPM = ~1 count/sample below 5 rpm → ±70% noise | `VEL_WIN_COUNTS 12`, cap 200 ms |
| 2 | **Ripple table** | `true = measured / CAL[counts mod 1024]` | decentered magnet → ±40% 2/rev fake ripple the PID chased | 36 bins, **runtime-loaded** |
| 3 | **Feedforward** | `PWM = Kff·target + offset` (+ PID) | a pure PID makes the integral guess the holding PWM → overshoot that **grows with speed** | `KFF 7.87`, `FF_OFFSET 21` |
| 4 | **PID** | Kp·e + Ki·∫e + Kd·de | trims the residual (Kp=disturbance/damping, Ki=drift, Kd=min) | `Kp 2.0 / Ki 0.10 / Kd 0.10` |
| 4b | **Back-calc anti-windup** | bleeds the integral excess on saturation | high-speed (saturated) overshoot | in `pid.cpp` |
| 5 | **Anti-stiction dither** | ±A flipped each tick (25 Hz), avg 0 | low-speed stick-slip limit cycle (0→9 rpm) | `DITHER 92`, only <13 rpm |
| — | **R-gain** | scales right-wheel PWM | wheel asymmetry | `MOTOR2_GAIN 1.00` |

**Operating envelope:** smooth from ~**0.06 m/s** (docking, thanks to the dither) to the nav max
**0.16 m/s** and beyond. Below ~0.06 m/s = hard mechanical floor (motor deadband ~120 PWM, static>kinetic
friction). **Live-tune:** `/debug/tune` Twist → `linear`=Kp,Ki,Kd · `angular.x`=R-gain · `angular.y`=Kff ·
`angular.z`=dither (sliders in `pid_tuner.py`). **Per-boot ritual:** `align_enc_cal.py --arm 250` (~8 s),
because the table lives in RAM.

---

## 1. Symptom
During live PID tuning (wheels in the air, `scripts/pid_tuner.py`), the **LEFT wheel kept a slow
(~1 s) sustained oscillation of ±6 rpm** that **no gain (Kp/Ki/Kd) could remove** — lowering Ki
reduced it but made the loop too slow; raising it brought the oscillation back. The RIGHT wheel
tuned cleanly at the same gains. → the "oscillation" did not behave like a control problem.

## 2. Hypothesis (correct): geometric encoder error
A magnetic encoder (AS5040) with a **decentered/tilted magnet** reports a **non-uniform angle**: it
reads faster/slower at different wheel angles. At constant true speed this looks like a periodic
velocity ripple, **locked to wheel position** (not time). The PID then chases this *measurement*
ripple. (Our `getRPM()` period method made it MORE visible — the old fixed-window average smoothed
it; see [[amr-architecture-doc]].)

## 3. Method — `scripts/encoder_calib.py`
At a **constant open-loop PWM** the wheel turns at a **constant true speed**. Over a full revolution
the encoder counts are exact (1024/rev), so the **mean measured rpm = the true speed**. Binning the
instantaneous rpm by **wheel angle (`counts mod 1024`, 36 bins of 10°)** gives the error profile
`ratio[angle] = sensor_rpm / mean`. Repeated at several PWMs to check speed-independence.

## 4. Findings (the data)
- **LEFT encoder: a 2-cycle/revolution error of ~40% peak-to-peak (0.84 .. 1.22)**, **IDENTICAL across
  PWM 100/150/200/250/300** → position-locked, speed-independent = **magnet misalignment**.
- **RIGHT encoder: same kind of 2/rev error but much smaller (~±5-6%)** → better aligned.
- Wheel speed difference at the same PWM: the **right was ~4.8% faster** (with MOTOR2_GAIN 1.10).
- Files: `docs/data/encoder_calib_data.json` (old profiles + residuals + tables + per-speed),
  `docs/data/encoder_calib_2026-06-29_after-correction.json` (raw run). **Use these for diagrams.**

## 5. Correction attempt — per-wheel lookup table (and why it FAILED)
Injected per-wheel tables `LEFT_CAL/RIGHT_CAL[36]` in `firmware.ino` (`calib_rpm()`:
`true = measured / cal[counts mod 1024]`, before the PID + odometry) + set `MOTOR2_GAIN` 1.10→1.05.

- **v1**: LEFT residual went to **2.3% (flat ✅)** but RIGHT was **19% and anti-phase** (the table made
  it worse). Refined the tables (`new = residual × old`, pointwise) and reflashed.
- **v2**: LEFT came back to **~±5%** and RIGHT **~±8%** — i.e. it did **NOT converge**, and even the
  already-good LEFT got worse.

### ROOT CAUSE of the failure (important)
The encoder is read **incrementally** — the count resets to **0 at every power-up**, at whatever
physical angle the wheel happens to be. So `counts mod 1024` is an angle **relative to boot**, not an
absolute wheel angle. **Every reflash reboots the Teensy → the encoder zero shifts by a random angle →
the fixed correction table is applied at the wrong angle.** The two wheels stop at different positions,
so the shift differs left vs right (explains why v1 LEFT happened to align but RIGHT didn't, and why
v2 shifted both again).

**Conclusion: a fixed position-indexed correction table CANNOT work reliably with this incremental
encoder** — the phase reference is lost on every power-cycle.

## 6. First attempt at a filter — time-domain low-pass (EMA) — FAILED
Replaced the table with a first-order EMA on the rpm. **It did almost nothing** (re-run calib: LEFT back
to ±18%). Why: an EMA attenuates *high frequency*, but the ripple's frequency *scales with speed* and
sits in the control band — at PWM 150 (~13 rpm) the ripple is ~0.42 Hz, which an alpha-0.85 EMA passes
at ~95%. **And it's worse the slower you go** (lower speed → lower ripple frequency → passes more). A
time-domain filter is the wrong tool for an angle-locked error.

## 7c. FINAL approach — runtime table + fast per-boot phase align (2026-06-29)
The angle-domain estimator (§7 below) worked but added ~0.6 s LAG (rejected by the user for the PID).
Final solution = the TABLE (instant, no lag), made reboot-proof by loading it at runtime:
- Firmware loads a 36+36 table AT RUNTIME via `/debug/enc_cal` (Float32MultiArray), applied instantly
  (`calib_rpm`, no averaging). A compiled-in table can't work — the flash reboots and shifts the zero.
- The ripple SHAPE is fixed (magnet); only its PHASE shifts per boot. Store the shape once
  (`scripts/encoder_ref_table.json`); each boot run `scripts/align_enc_cal.py` (~8 s): short spin →
  measure raw ripple → sub-bin cross-correlate (~1°, via upsampling) vs the reference → roll to the
  current frame → publish. ~8 s vs ~54 s for a full calibration.
- Commands: `scripts/calibrate_and_apply.sh` (full) or `align_enc_cal.py --arm 250` (fast).
- **GOTCHA (cost a bad run):** align MUST reset the firmware table to flat (1.0) BEFORE its measurement
  spin, else it measures the residual of the already-loaded table → wrong offset → can load an ANTI-PHASE
  table (ripple DOUBLED, ~71% > raw). Fixed: align publishes a flat table first. Bug symptom: verify shows
  ripple BIGGER than raw.
- Result: LEFT ±40% → ~±4%, RIGHT ~±3.5%, flat across speeds, INSTANT, survives reboots (re-align).
  Re-run after each Teensy power-cycle (not per ROS launch — the table lives in Teensy RAM).

## 7. (superseded by 7c) The angle-domain velocity estimator (flashed then replaced 2026-06-29)
**Key fact: the AS5040 emits exactly 1024 counts/rev (just unevenly spaced).** So the *time to
accumulate 512 counts = the time for half a TRUE revolution = exactly one period of the 2/rev ripple.*
Computing velocity over that **fixed 512-count displacement** averages out exactly one ripple period →
the ripple cancels **at any speed, with no phase dependence** (survives reboots). Implementation in
`firmware.ino` (`struct VelEstimator`, ring buffer of `(count, micros)`, applied to `current_rpm1/2`):
velocity = `Δcounts / CPR / Δt_min` over the newest stored sample displaced by ≥ `vel_win_counts`.
- **Window** `VEL_WIN_COUNTS = 512` (half rev). **Live-tunable** via `/debug/tune` `angular.y` (counts,
  clamped 64..1024; 0 = keep default).
- **Time cap** `VEL_MAX_AGE_US = 800 ms` — caps the look-back so accelerating from rest never averages
  over the buffer's old standstill samples. **Startup bug fixed**: without it, before the wheel has
  travelled a full window the estimator fell back to the oldest buffered sample (seconds old, from when
  the wheel was stopped) → tiny Δcounts / huge Δt → reported ~0 rpm while the wheel was actually turning,
  so the PID slowly ramped PWM until a delayed "jump". Live-tunable via `angular.z` (ms; lower = snappier
  startup, more ripple). Calibration was fine (constant speed) but a step from rest exposed it.
- **Trade-off: lag ≈ half the window = a quarter rev** (~1.1 s at 13 rpm). Shrink the window (angular.y)
  or the time cap (angular.z) for less lag at the cost of partial ripple rejection. The only lag-free
  fix is HARDWARE: re-center the LEFT magnet (then ±40% → ~±6% and no software averaging is needed).
- Why this works where the others didn't: count-windowing is in the **angle domain** (counts are
  conserved 1024/rev), so it tracks the angle-locked ripple at all speeds, unlike the EMA, and needs no
  absolute phase, unlike the table.

`MOTOR2_GAIN 1.05` (steady-state speed match) kept — scalar, phase-independent, still valid. Lookup
tables removed. Remaining clean option if more is needed: re-center the LEFT magnet (HW).

**To verify/tune:** re-run `scripts/encoder_calib.py --arm 150,200,250` — both profiles should now be
~flat (the reported velocity is the half-rev average = constant). If the PID feels laggy, shrink the
window: `ros2 topic pub --once /debug/tune geometry_msgs/msg/Twist
"{linear: {x: 0.8, y: 0.2, z: 0.5}, angular: {x: 1.05, y: 320.0}}"`. See [[amr-pid-tuning]] and
`docs/CHANGELOG-FIXES.md`.
