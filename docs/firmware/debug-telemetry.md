# Debug telemetry & open-loop mode

*Last updated: 2026-06-17.*

These are **our additions** to the firmware (not in upstream). They were essential to diagnose the
right-wheel problem and remain useful tools.

## Debug topics (published by the Teensy)
All are `geometry_msgs/msg/Vector3`, **best-effort** QoS, ~50 Hz:

| Topic | x | y | z |
|---|---|---|---|
| `/debug/left` | target rpm (LEFT) | measured rpm (LEFT) | raw encoder counts (LEFT) |
| `/debug/right` | target rpm (RIGHT) | measured rpm (RIGHT) | raw encoder counts (RIGHT) |
| `/debug/pwm` | PWM LEFT | PWM RIGHT | 0 |

> ⚠️ **best-effort QoS**: a Python/CLI subscriber must request best-effort too, e.g.
> `ros2 topic echo /debug/right --qos-reliability best_effort`, otherwise it receives nothing.

## Open-loop test mode (input)
| Topic | Type | Meaning |
|---|---|---|
| `/debug/openloop` | `geometry_msgs/msg/Vector3` | `x` = a fixed PWM applied to **both** motors, **bypassing the PID** |

- When `|x| ≥ 1` and a message arrived within the last **300 ms**, `moveBase()` skips the PID and drives
  both motors with that PWM directly. Otherwise it falls back to normal PID control.
- Use it to compare the two motor channels at identical drive (this is how we proved the right hardware
  was healthy and the problem was in the closed loop). Safety: same 300 ms timeout idea as `/cmd_vel`.

## Diagnostic scripts (on the Pi, `~/`)
| Script | Purpose |
|---|---|
| `guided_encoder_test.py` | guided hand-spin test of each encoder (uses `/odom/unfiltered`) |
| `sign_test.py` | check encoder sign (forward → positive) |
| `powered_debug_test.py` | small `/cmd_vel`, logs per-wheel rpm/counts/pwm, auto-abort on runaway |
| `openloop_test.py` | drive both motors at equal PWM via `/debug/openloop`, compare wheels (ratio D/G) |
| `high_rate_capture.py` | 50 Hz capture of `/debug/right` around a jerk (raw counts, glitch vs real) |
| `raw_debug_monitor.py` | live print of `/debug/left` + `/debug/right` |
| `i2cscan/` | standalone Teensy sketch: I²C bus scanner (used to ID the IMU as MPU6500) |

(These were the tools used during the diagnosis — see [../history/diagnostics.md](../history/diagnostics.md).)
