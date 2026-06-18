# Running the robot (step by step)

*Last updated: 2026-06-18.*

## 0. Safety first
Read [safety.md](safety.md). For any motor test: **wheels off the ground, 24 V on, a hand on the 24 V
cut-off**, low speeds.

## 1. Connect to the Pi (SSH)
From the dev PC:
```bash
ssh botshare@172.17.201.29       # password: <ask the team>  (key auth also set up: `ssh pi`)
```
An interactive shell sources ROS 2 automatically (`~/.bashrc`).

## 2. Start the robot base (one command)
```bash
source ~/camera_ws/install/setup.bash      # camera overlay (RPi libcamera + camera_ros)
ros2 launch /home/botshare/openamr_real_bringup.launch.py
```
This starts: micro-ROS agent (Teensy), RPLidar, **scan body filter** (`/scan_filtered`), **EKF**
(`/odom` + TF, wheels+IMU), **camera** (`/camera/*`), and the static TFs.
See [../software/bringup.md](../software/bringup.md).

Check it's alive (in another SSH tab):
```bash
ros2 topic list | grep -E 'scan|/odom|imu|cmd_vel|camera|map'
ros2 topic echo /scan_filtered --once --qos-reliability best_effort
ros2 run tf2_ros tf2_echo odom base_link        # from the EKF
```

### (Alternative) start only the Teensy bridge
```bash
ros2 run micro_ros_agent micro_ros_agent serial -b 115200 \
  -D /dev/serial/by-id/usb-Teensyduino_USB_Serial_16778200-if00
```

## 3. Drive with the keyboard (teleop)
In a second SSH tab:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -p speed:=0.1 -p turn:=0.5 -p repeat_rate:=10.0
```
Keys: `i` forward, `,` backward, `j`/`l` rotate, `k` stop. `repeat_rate:=10.0` keeps the command flowing
so the 200 ms watchdog doesn't cut the motors between keypresses. Teleop also works **from the Ubuntu dev
PC** (same `ROS_DOMAIN_ID=0`). **Drive slowly** (0.1 m/s) — fast moves/spins break SLAM tracking.

## 3b. Map an area (SLAM) — on the Pi
```bash
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=false \
  slam_params_file:=/home/botshare/slam_params.yaml
```
Drive slowly with teleop, return to start to close the loop, then save:
```bash
mkdir -p ~/maps && cd ~/maps
ros2 run nav2_map_server map_saver_cli -f coin1 -p save_map_timeout:=15.0
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
  "{filename: '/home/botshare/maps/coin1'}"
```
Full details & caveats: [../software/navigation.md](../software/navigation.md).

## 3c. See the camera
- **On the robot (headless):** `python3 ~/cam_snapshot.py` → `~/cam_snapshot.jpg`.
- **From the Ubuntu PC:** `rqt_image_view` on `/camera/image_raw` with transport **compressed**
  (never raw over WiFi — it lags everything). See [../hardware/camera.md](../hardware/camera.md).

## 3d. Visualize from the Ubuntu dev PC (RViz)
```bash
export ROS_DOMAIN_ID=0 && source /opt/ros/jazzy/setup.bash
rviz2 -d scripts/openamr_slam.rviz
```
Requires the same domain (0), CycloneDDS, and the **same LAN subnet** as the Pi.
See [../software/visualization.md](../software/visualization.md).

## 4. Rebuild & flash the firmware (only if you changed it)
On the Pi:
```bash
# build
cd ~/linorobot2_hardware/firmware
ROS_DISTRO=jazzy ~/.platformio/penv/bin/pio run -e teensy40      # or: bash ~/build_fw.sh

# flash (stop the agent first to free the serial port)
pkill micro_ros_agent
HEX=~/linorobot2_hardware/firmware/.pio/build/teensy40/firmware.hex
sudo teensy_loader_cli --mcu=TEENSY40 -s -w -v $HEX
# if "error writing": it is in HalfKay bootloader → retry once without -s:
sudo teensy_loader_cli --mcu=TEENSY40 -w -v $HEX
```
Details & config: [../firmware/firmware.md](../firmware/firmware.md).

## 5. Stopping
- `k` in teleop, or `Ctrl-C` on the publisher → motors stop within 200 ms (watchdog).
- Hardware: the 24 V cut-off.

## Common issues
| Symptom | Likely cause / fix |
|---|---|
| No topics from Teensy | agent not running, wrong baud (must be 115200), or LED blinking 3× (init fail) |
| `/scan` missing / LiDAR error `80008000` | LiDAR stuck → **unplug/replug** the LiDAR USB (or battery power-cycle), relaunch once |
| `ros2` not found over `ssh "..."` | non-interactive shell → source ROS manually (see [../hardware/raspberry-pi.md](../hardware/raspberry-pi.md)) |
| `/debug/*` echo shows nothing | best-effort QoS → `ros2 topic echo /debug/right --qos-reliability best_effort` |
| Camera "no cameras available" | apt libcamera doesn't support IMX708 → source `~/camera_ws` (RPi fork). See [../hardware/camera.md](../hardware/camera.md) |
| Huge lag (camera + scan) over WiFi | a raw image was subscribed remotely → use the **compressed** camera topic only |
| Dev PC sees no topics | wrong `ROS_DOMAIN_ID` (use 0), wrong RMW, or different WiFi subnet than the Pi |
| `pkill ...` kills the SSH session (exit 255) | pattern matches its own cmdline → use the bracket trick `pkill -f "[s]can_body_filter.py"` |
| SLAM map drifts / scan doesn't align | drove too fast / in-place spins → drive slowly; consider a fresh map |
