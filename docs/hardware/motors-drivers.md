# Motors & drivers (BLDC + ZBLD)

*Last updated: 2026-06-17.*

## Overview
Two **BLDC** (brushless) motors, one per wheel, each driven by its own **ZBLD** driver. The Teensy
sends low-current logic signals to the drivers; the drivers deliver the 24 V power to the motor phases.

- **Motors**: ZD 60_200W ×2, 24 V, 3 phases U/V/W + Hall sensors. (LEFT = MOTOR1, RIGHT = MOTOR2)
- **Drivers**: ZBLD C20-120L2R ×2.

## Communication (Teensy → driver)
Per motor, 3 logic lines from the Teensy:

| Teensy signal | Driver input | Meaning | Left pin | Right pin |
|---|---|---|---|---|
| PWM | `VAR / AI2` | speed setpoint (PWM 3–10 kHz or 0–5 V) | **1** | **5** |
| IN_A | `FWD / DI1` | forward direction | **20** | **6** |
| IN_B | `REV / DI2` | reverse direction | **21** | **8** |
| GND | `COM` | **common ground (mandatory)** | GND | GND |

- Power side: `DC+ / DC− = 24 V` (with a fuse). Motor side: phases U/V/W + Hall.
- ⚠️ The driver `COM` **must** be tied to the Teensy GND, otherwise signals/encoders are noisy.

## Driver configuration — DIP switches (SW1–SW6)
Both drivers must be set **identically** (LEFT is the working reference).

| Switch | Function | Current setting |
|---|---|---|
| SW1 | open-loop / closed-loop | ON |
| SW2 | AI2 (speed source) | ON |
| SW3 | internal control | OFF |
| SW4 / SW5 | motor pole pairs | OFF |
| SW6 | RS485 termination | OFF |

> SW1 (open/closed loop) is worth understanding: in **closed loop** the driver regulates speed itself
> from the Hall sensors, which can **conflict** with the Teensy PID (double loop). Keep both drivers the same.

## Driver configuration — TWO trim pots (CRITICAL)
Each driver has **two** potentiometers. **They must match between LEFT and RIGHT** (calibrate the right
to the left, the known-good reference). These were the root cause of the right-wheel problem:

| Pot | Location | Function | Correct setting | Symptom if wrong |
|---|---|---|---|---|
| **VAR** | top | speed / gain (PWM → speed) | ~3.5/10, **same** both sides | too high → wheel runs ~8× too fast → **runaway** |
| **ACC/DEC** | near the DIP switches | acceleration/deceleration ramp | **4/10**, same both sides | =0 → no smoothing → **jerks/oscillation** in closed loop |

See the full story in [history/diagnostics.md](../history/diagnostics.md).

## Good to know / gotchas
- The original fault ("right wheel runs away, robot doesn't go straight") was **100 % driver tuning**:
  the right VAR pot was at max (10) and its ACC/DEC pot at 0. After matching both pots to the left, the
  right wheel tracks correctly.
- A small residual: the right channel needs slightly more PWM for the same speed (minor); the PID
  compensates. Fine-tune the right VAR pot if you want perfectly equal PWM.
- Test the motors safely with the **open-loop mode** (`/debug/openloop`) which bypasses the PID — useful
  to compare the two channels at identical PWM. See [firmware/debug-telemetry.md](../firmware/debug-telemetry.md).
- **Always**: wheels off the ground, 24 V on, a hand on the 24 V cut-off for the first tests.
