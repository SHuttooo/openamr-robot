# Field & diagnostic scripts

Tools split by **risk** (Raj review PR3): read-only tools are low-risk and can ship in an early PR;
powered tools move the robot and require **`--arm`** + fresh telemetry before any motion.

## ✅ Read-only — no motion (low-risk PR)
| Script | What it does |
|---|---|
| `encread.py` | print encoder counts + angle while you turn a wheel by hand |
| `encpid.py` | live target/measured rpm + error per wheel |
| `raw_debug_monitor.py` | raw dump of the `/debug/*` topics |
| `lidar_view.py` | ASCII sector view of `/scan` (find the robot's front) |
| `cam_snapshot.py` | grab one compressed camera frame to disk |
| `clean_map.py` | offline: despeckle a SLAM `.pgm` map |
| `stop.sh` | cancel the current Nav2 goal (stops motion) |

## ⚠️ Powered — MOVE THE ROBOT (require `--arm`, wheels in the air, hand on the cutoff)
| Script | What it does | Safety |
|---|---|---|
| `openloop_test.py` | fixed PWM on both motors (PID bypassed) | `--arm`, bounded, fresh-telemetry-required |
| `high_rate_capture.py` | 50 Hz capture around a jerk | `--arm`, **immediate stop at trigger** |
| `powered_debug_test.py` | stepped `/cmd_vel`, observe `/debug` | ⏳ same gate to add |
| `guided_encoder_test.py` | hand-turn wizard (no 24 V) | ⏳ |
| `sign_test.py` | forward/reverse encoder sign | ⏳ |
| `yawtest.py` | in-place rotation check | ⏳ |
| `wtest.sh` / `gtest.sh` | wheels-in-air / on-ground bash tests | ⏳ |
| `pid_tuner.py` | interactive PID/gain GUI (PC) | firmware bounds `/debug/openloop` |

> ⏳ = the `--arm` + fresh-telemetry gate (already on `openloop_test`/`high_rate_capture`) is to be
> applied to these too. The firmware **independently** bounds `/debug/openloop` (defense in depth).

## 🚀 Launch / orchestration / deploy
| Script | What it does |
|---|---|
| `deploy_to_pi.sh` | push edited platform-sw code PC → Pi + rebuild |
| `agentup.sh` | start the micro-ROS agent only (Teensy, no motion) |
| `bringall.sh` | ⚠️ LEGACY real Nav2 orchestrator (use `bringup.launch.py sim:=false`) |
| `goal_relay.py` | ⚠️ LEGACY standalone goal forwarder |

## ⚙️ Config / reference
`ekf.yaml`, `camera_info.yaml`, `openamr_nav.rviz`, `openamr_slam.rviz`, `pid_tuner.py` defaults,
`COMMANDS.md` (full command cheat-sheet).
