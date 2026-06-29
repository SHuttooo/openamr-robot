# PID / velocity-loop tuning log — values from the bench step responses (2026-06-29)

Quantitative record of the tuning session (wheels in the air, `pid_tuner.py`), kept for documentation
and diagrams. Raw encoder data: `docs/data/encoder_calib_*.json`. Final config: see
`docs/history/encoder-calibration.md`.

## A. Encoder ripple — peak-to-peak through the fixes
`sensor_rpm / mean` per wheel angle (1.000 = perfect). Source plots = `encoder_calib.py` runs.

| Stage | LEFT p-p | RIGHT p-p | Note |
|---|---|---|---|
| Raw (no correction) | **~47 %** (0.84–1.22) | ~10–18 % | decentered magnet, 2 cycles/rev, identical across PWM 150/200/250/300 |
| Compiled table v1 (residual) | 2.3 % | 19 % | LEFT flat, RIGHT anti-phase (table mis-phased) |
| Compiled table v2 (residual) | ~12 % | ~9 % | both shifted again after reflash → table approach abandoned |
| Angle-domain filter (½-rev) | 5.4 % | 2.3 % | flat but ~0.6 s lag → rejected |
| Runtime table, 10° align | ~16 % | ~10 % | sub-bin phase error left residual |
| **Runtime table, sub-degree align** | **5.7–8.9 %** | **6–7 %** | FINAL: instant, survives reboot (re-align 8 s/boot) |

## B. PID step responses — overshoot vs gains & speed
Target = green line; overshoot = peak vs target. Wheels in air.

| Config | Speed | Overshoot / result | Lesson |
|---|---|---|---|
| Kp 1.79 / Ki 0.09 / Kd 0.15 | 0.24 m/s (22.8 rpm) | slow rise ~1.7 s, no overshoot | baseline too soft |
| Kp 8.9 then 18.7 (Ki 0.27) | 0.26 m/s | rise ~unchanged, more noise | **velocity loop: Ki paces the rise, not Kp** |
| Kp 5 / Ki 0.8 / Kd 0.1 | 0.15 m/s | **43 %** | Ki high → big overshoot |
| Kp 8.73 / Ki 0.8 | 0.15 m/s | **12 %** | Kp damps the overshoot |
| Kp 8.73 / Ki 0.8 | 0.21 m/s | **60 %** | integral **windup**, grows with speed |
| Kp 8.73 / Ki 0.5 | 0.11 m/s | OK (slight low-speed struggle) | |
| Kp 8.73 / Ki 0.5 | 0.21 m/s | **~5 %** (excellent) | |
| Kp 8.73 / Ki 0.5 | 0.33 m/s | **47 %** + dip, PWM saturating | saturation windup |
| + back-calculation anti-windup | 0.31 m/s | **36 %**, dip gone | helps saturation; rest is plain PI overshoot |
| **Feedforward** Kff 9.3 / Kp 5 / Ki 0.1 | 0.16 m/s | ~15 %, slight over-speed | FF added |
| Feedforward Kff 9.3 | 0.27 m/s | ~25 % — **same shape as 0.16** | **FF → speed-independent response** |
| Feedforward Kff 7.33 / Kp 2 / Ki 0.15 | 0.17 m/s | clean, ~0 overshoot | Kff tuned down |
| Feedforward Kff 7.33 | 0.21 m/s | clean, consistent | |
| **Kff 7.87 / Kp 2 / Ki 0.1 / Kd 0.1** | 0.16 & 0.27 m/s | **clean, consistent** | FINAL mid-range |

## C. Low-speed (stick-slip) & dither
nav max = 0.16 m/s; below ~0.09 m/s the drivetrain stick-slips (motor deadband ~120 PWM).

| Config | Speed | Result |
|---|---|---|
| Final gains, no dither | 0.09 m/s (9 rpm) | **floor**: LEFT smooth, RIGHT periodic dips |
| no dither | 0.06 m/s | large 0→9 rpm stick-slip limit cycle |
| Dither 40 PWM | 0.06 m/s | no effect (base PWM ~70 + 40 < ~120 deadband) |
| Dither 70 PWM | 0.06 m/s | LEFT smooth, RIGHT still oscillates |
| **Dither 92 PWM** | 0.06 m/s | **both smooth (~±1 rpm wobble)** → viable for docking |

## D. Final flashed values
`K_P 2.0 · K_I 0.10 · K_D 0.10 · KFF 7.87 · FF_OFFSET 21 · DITHER 92 (active <13 rpm) · MOTOR2_GAIN 1.00 ·
vel-estimator window 12 counts · back-calculation anti-windup`. Operating envelope: smooth ~0.06 → 0.16+ m/s.
