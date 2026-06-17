# OpenAMR Robot — working repo

Differential-drive AMR (OpenAMR platform, linorobot2-based firmware) on a Raspberry Pi 5 + Teensy 4.0.
This repo holds **our** work: documentation, diagnostic/bring-up scripts, the real-hardware launch, and
our firmware overlay.

## Start here → [`docs/README.md`](docs/README.md)
Full onboarding docs (overview, communication map, per-component sheets, procedures, diagnostics history).

## Layout
```
docs/        Onboarding documentation (read docs/README.md first)
scripts/     Diagnostic + helper nodes (encoders, motors, lidar, odom relay) — run on the Pi
launch/      openamr_real_bringup.launch.py — the real-hardware bring-up (agent + lidar + odom + TF)
firmware/    OVERLAY: only the files WE modified in linorobot2_hardware (config + firmware + pid)
claude-memory/  Condensed project notes (for resuming with an AI assistant on another machine)
```

## Not in this repo
- **`linorobot2_hardware/`** (the upstream firmware) is **git-ignored** — clone it separately on the Pi and
  apply our `firmware/` overlay. See [`docs/firmware/firmware.md`](docs/firmware/firmware.md).
- **Credentials**: the Pi SSH password is **not** stored here (ask the team).

## Quick robot bring-up (on the Pi)
```bash
ros2 launch /home/botshare/openamr_real_bringup.launch.py
```
See [`docs/procedures/running-the-robot.md`](docs/procedures/running-the-robot.md).

## Resuming on another machine (e.g. Ubuntu)
Clone this repo; the context lives in `docs/` + `claude-memory/`. The robot (Pi) is reached over the
network (SSH / ROS 2), independent of your OS. For native RViz/Gazebo, use Ubuntu with ROS 2 Jazzy on the
same network and matching `ROS_DOMAIN_ID` / RMW; to work with an AI assistant + live view from Windows, use
Foxglove. See [`claude-memory/amr-dev-workflow.md`](claude-memory/amr-dev-workflow.md).
