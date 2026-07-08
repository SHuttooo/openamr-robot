# Runbook — real robot (start-up, encoder calibration, docking)

Operational commands that keep getting re-derived. **This is the source of truth.**
Verified 2026-07-01. Robot = Pi5 **`botshare@botshare.local`**, Teensy on `/dev/ttyACM0`
(by-id: `/dev/serial/by-id/usb-Teensyduino_USB_Serial_16778200-if00`), LiDAR on `/dev/ttyUSB0`.

> ⚠️ **The Pi IP is DHCP → it changes.** 2026-07-06 the Pi hardware was swapped (same SSD),
> new MAC → new IP: old `172.17.201.29` is DEAD, current is `172.17.17.64`. **Always use the
> mDNS hostname `botshare.local`** (follows the SSD) instead of a hard-coded IP. Find the IP:
> `getent hosts botshare.local`. The operator UI's rosbridge IP (`openamrobot-ui/.env`,
> `web/src/shared/constants/index.js`) must be updated to the new IP/`botshare.local` too.

## 0. DDS environment (every terminal, PC and Pi)
The robot runs **CycloneDDS on domain 0**. The PC defaults to FastDDS/domain 42 → it must be overridden
or it sees nothing.
```bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
```
SSH is non-interactive → it does **not** source ROS. Always prefix the above.

## 1. micro-ROS agent (Teensy telemetry) — ON THE PI
The agent bridges the Teensy: `/cmd_vel`, `/odom/unfiltered`, `/imu/data`, and the `/debug/*` topics.
It lives in `~/linorobot2_ws`. Started automatically by the bring-up; run standalone only for a bare
encoder calibration.
```bash
# on the Pi
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 run micro_ros_agent micro_ros_agent serial -b 115200 -D /dev/ttyACM0
```
Leave it running. (Harmless noise: `Failed to parse type hash ... USER_DATA (null)`.)

## 2. Encoder calibration (per Teensy power-cycle, BEFORE driving)
Places the ripple-correction table at the correct phase. The table lives in Teensy RAM → **re-run after
every Teensy power-cycle** (not per ROS launch). **WHEELS IN THE AIR, 24 V, hand on the cut-off.**
Needs the agent (§1) up so `/debug/*` telemetry exists (else it refuses: `REFUSED: no /debug telemetry`).
```bash
# on the PC — the script talks to the firmware over Cyclone/domain 0
cd ~/Documents/openamr
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
python3 scripts/align_enc_cal.py --arm 250     # fast ~6-8 s; full = scripts/calibrate_and_apply.sh
```
Success prints `table placed -> /debug/enc_cal`. Reference shape: `scripts/encoder_ref_table.json`.
See `docs/history/encoder-calibration.md`.

## 3. Full bring-up (nav + docking) — ON THE PI
Starts agent + LiDAR + EKF + scan filter + camera + Nav2 (+ docking with `use_docking:=true`).
```bash
# on the Pi, sourcing jazzy + linorobot2_ws + camera_ws + openamr-platform-sw, Cyclone/domain 0
ros2 launch openamrobot_bringup bringup.launch.py \
  map:=/home/botshare/maps/piece_actuelle.yaml use_docking:=true
```
Then **2D Pose Estimate** in RViz (gives `map→odom`; else costmaps stay empty). Nav auto-activates
(bond_timeout 60 s fix). Put the robot down first; run §2 calibration before trusting driving.

## 4. Operator UI (Docker) — ON THE PC
```bash
cd ~/Documents/openAMRobot/openamrobot-ui
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID=0 docker compose up   # -> http://localhost:5050/control
```
The `RMW/DOMAIN` prefix is **mandatory** (the shell's FastDDS/42 defaults override `.env` otherwise).

## 5. Docking (AprilTag bundle, no physical dock)
**One-time config** (per printed bundle / per map):
- Tag size: `openamrobot_docking/config/tags_36h11.yaml` → `size:` = measured black-square edge in metres
  (current: `0.131`).
- Dock pose: `openamrobot_docking/config/dock_trigger.yaml` → `dock_pose_x/y/yaw` = the dock in the map
  frame (capture: drive the robot to the docked spot facing the centre tag, read `/amcl_pose`).
- Physical bundle: 3 tags 36h11 (id 0/1/2) coplanar, same height (≈ camera height), horizontal row,
  **id 1 in the middle**; the two outer tags define the surface normal (wider baseline = more stable).

**Trigger** (all 3 tags must be seen together):
```bash
ros2 topic pub --once /dock_trigger std_msgs/Bool "{data: true}"    # dock  (or the UI dock button)
ros2 topic pub --once /undock_robot  std_msgs/Bool "{data: true}"   # undock
```
Manual AprilTag toggle (on-demand gate; dock_trigger does it automatically at staging):
```bash
ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: true}"
```

## Notes
- Camera intrinsics are calibrated (`openamrobot_perception/config/camera_info.yaml`, 1280×720). No redo.
- SSH backgrounding pitfall + full details: memory `amr-pi-ros-commands`, `amr-pid-tuning`,
  `amr-apriltag-on-demand-gate`, `amr-next-session-plan`.
