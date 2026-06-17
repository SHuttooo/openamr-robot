# Wiring & Teensy 4.0 pinout

*Last updated: 2026-06-17.*

Convention: **MOTOR1 = LEFT wheel, MOTOR2 = RIGHT wheel.** Logic level **3.3 V**.

## Teensy 4.0 pin assignment

| Function | Pin | Notes |
|---|---|---|
| **IMU** SDA | 18 | I²C data (MPU6500 @ 0x68) |
| **IMU** SCL | 19 | I²C clock |
| **Encoder LEFT (M1)** A | 14 | quadrature |
| **Encoder LEFT (M1)** B | 15 | quadrature |
| **Encoder RIGHT (M2)** A | 11 | quadrature |
| **Encoder RIGHT (M2)** B | 12 | quadrature |
| **Motor LEFT (M1)** PWM | 1 | → driver `VAR/AI2` (speed) |
| **Motor LEFT (M1)** IN_A / FWD | 20 | → driver `FWD/DI1` |
| **Motor LEFT (M1)** IN_B / REV | 21 | → driver `REV/DI2` |
| **Motor RIGHT (M2)** PWM | 5 | → driver `VAR/AI2` (speed) |
| **Motor RIGHT (M2)** IN_A / FWD | 6 | → driver `FWD/DI1` |
| **Motor RIGHT (M2)** IN_B / REV | 8 | → driver `REV/DI2` |
| Debug LED | 13 | init/status (3 blinks = init failure) |
| micro-ROS | USB | native serial, 115200 baud |

> These values are also the `#define`s in `lino_base_config.h` (see [firmware/firmware.md](../firmware/firmware.md)).
> Note: `MOTOR1_PWM` is pin **1** (pin 21 is **not** a PWM pin on the Teensy 4.x — a common upstream pitfall).

## Driver wiring (per motor)
| Teensy | → Driver (ZBLD) |
|---|---|
| PWM pin | `VAR / AI2` (speed setpoint) |
| IN_A pin | `FWD / DI1` (forward) |
| IN_B pin | `REV / DI2` (reverse) |
| GND | `COM` (**common ground — mandatory**) |

Driver power: `DC+ / DC− = 24 V` (fused). Motor side: phases **U/V/W** + Hall sensors.

## Grounding
All grounds must be common: **Teensy GND ↔ driver COM**. A floating COM was a real source of noise
concern (see [history/diagnostics.md](../history/diagnostics.md)).

## ASCII map
```
                 Teensy 4.0 (3.3V)
   IMU  ── SDA18/SCL19 ───────────────► MPU6500 (I2C 0x68)
   ENC L ── A14/B15 ──────────────────► encoder LEFT
   ENC R ── A11/B12 ──────────────────► encoder RIGHT
   M1   ── PWM1 / IN20 / IN21 ────────► driver LEFT  ── U/V/W ─► motor LEFT
   M2   ── PWM5 / IN6 / IN8 ──────────► driver RIGHT ── U/V/W ─► motor RIGHT
   USB ───────────────────────────────► Raspberry Pi (micro-ROS 115200)
   GND ───────────────────────────────► COM of both drivers (common)
```
