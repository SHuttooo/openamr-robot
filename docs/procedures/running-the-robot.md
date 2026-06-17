# Running the robot (step by step)

*Last updated: 2026-06-17.*

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
ros2 launch /home/botshare/openamr_real_bringup.launch.py
```
This starts: micro-ROS agent (Teensy), RPLidar, odom relay, lidar TF. See [../software/bringup.md](../software/bringup.md).

Check it's alive (in another SSH tab):
```bash
ros2 topic list | grep -E 'scan|/odom|imu|cmd_vel'
ros2 topic hz /odom        # ~50 Hz
ros2 topic hz /scan        # ~7 Hz
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
so the 200 ms watchdog doesn't cut the motors between keypresses.

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
| `/scan` missing / LiDAR error `80008000` | LiDAR stuck → **unplug/replug** the LiDAR USB, relaunch once |
| `ros2` not found over `ssh "..."` | non-interactive shell → source ROS manually (see [../hardware/raspberry-pi.md](../hardware/raspberry-pi.md)) |
| `/debug/*` echo shows nothing | best-effort QoS → `ros2 topic echo /debug/right --qos-reliability best_effort` |
