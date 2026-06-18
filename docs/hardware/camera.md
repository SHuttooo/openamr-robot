# Camera (Pi Camera Module 3 NoIR / IMX708)

*Last updated: 2026-06-18.*

> **Status: WORKING.** The camera streams to ROS (`/camera/image_raw` + `/camera/camera_info`).
> Still TODO: intrinsic calibration (checkerboard) before any AprilTag / vision docking.

## Overview
| | |
|---|---|
| Module | Raspberry Pi Camera Module 3 **NoIR** (Sony **IMX708** sensor, no IR-cut filter) |
| Autofocus | `dw9807` VCM (lens motor) on the module |
| Interface | **CSI** (MIPI ribbon to the Pi), **not USB** → handled by **libcamera** |
| Device | "cam0" on the Pi 5 CSI connector |

## Communication (Pi ↔ camera)
- **CSI / MIPI** ribbon into the Pi's camera connector. Kernel side is fully OK:
  `camera_auto_detect=1` (in `/boot/firmware/config.txt`) loads the overlay; the media graph is
  `imx708_noir → csi2 → pisp-fe → rp1-cfe` (verify with `media-ctl -d /dev/media0 -p`).
- The capture is driven by **libcamera**, exposed to ROS by the **`camera_ros`** node.

## ⚠️ The libcamera gotcha (and the fix) — IMPORTANT
On **Pi 5 + Ubuntu 24.04 + ROS 2 Jazzy**, the **apt** packages
(`ros-jazzy-libcamera` / `ros-jazzy-camera-ros`) use **upstream libcamera**, which does **NOT** support
the Camera Module 3 (IMX708) on Pi 5. Symptom:
```
camera_node → "no cameras available"
# debug (LIBCAMERA_LOG_LEVELS=*:0): rpi/pisp pipeline → "Unable to acquire a CFE instance"
```
The hardware/kernel are fine — it's purely a libcamera version problem. **Only the Raspberry Pi fork of
libcamera supports the IMX708.**

**Fix (done 2026-06-18): build the RPi fork of libcamera + `camera_ros` from source in a colcon overlay.**
On the Pi, in `~/camera_ws`:
```bash
# build deps (apt)
sudo apt install -y g++ cmake meson ninja-build pkg-config libboost-dev libgnutls28-dev openssl \
  libjpeg-dev libpng-dev libtiff-dev python3-yaml python3-ply pybind11-dev python3-colcon-meson \
  libglib2.0-dev libgstreamer-plugins-base1.0-dev libdrm-dev libevent-dev

mkdir -p ~/camera_ws/src && cd ~/camera_ws/src
git clone https://github.com/raspberrypi/libcamera.git        # the RPi FORK (key!)
git clone https://github.com/christianrauch/camera_ros.git

cd ~/camera_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -y
colcon build --packages-select libcamera camera_ros           # ~6-7 min on the Pi 5
```
This overlay **shadows** the apt libcamera without removing it (reversible: just don't source it).
Reference guide: <https://github.com/erykpawelek/libcamera_ros2_setup>.

## Run it
```bash
source /opt/ros/jazzy/setup.bash
source ~/camera_ws/install/setup.bash          # MUST source the overlay (RPi libcamera + camera_ros)
ros2 run camera_ros camera_node --ros-args \
  -p width:=640 -p height:=480 -p format:=RGB888 -p frame_id:=camera_optical_frame \
  -p FrameDurationLimits:="[100000,100000]"     # ~10 fps (see Performance below)
```
It is also wired into the main bring-up (`openamr_real_bringup.launch.py`) — just source `~/camera_ws`
before launching. Verified working at both 1280×720 and 640×480 `bgr8` on `/camera/image_raw`.

## ROS interface (provided)
| Topic | Type | Frame |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/msg/Image` (bgr8, 1280×720) | `camera_optical_frame` |
| `/camera/image_raw/compressed` | `sensor_msgs/msg/CompressedImage` | `camera_optical_frame` |
| `/camera/camera_info` | `sensor_msgs/msg/CameraInfo` | `camera_optical_frame` |

> Note: `camera_info` is currently **uncalibrated** (default/empty matrices, a warning is logged).
> Calibrate before any metric vision (see TODO).

## Mounting (measured) & TF
Physical position relative to `base_link` (center of the wheel axle):
- **x ≈ 0.415 m** (8 cm in front of the LiDAR, which is at x=0.335)
- **y = 0** (centered)
- **z ≈ 0.12 m** relative to `base_link` (≈ 0.175 m above the ground)
- Orientation: facing forward (to refine).

The bring-up publishes two static TFs:
```
base_link → camera_link        (x=0.415, y=0, z=0.12)
camera_link → camera_optical_frame   (roll=-90°, yaw=-90°  → ROS optical convention: z fwd, x right, y down)
```
Images are published in `camera_optical_frame`.

## ⚠️ Performance & bandwidth (IMPORTANT — learned the hard way)
The **raw** image is huge: 1280×720×3 ≈ **2.76 MB/frame** (640×480 ≈ 0.92 MB). Subscribing to
`/camera/image_raw` **over WiFi saturates the link** → multi-second lag on EVERYTHING (the camera AND
`/scan`/`/map`, since they share the network). Symptom seen 2026-06-18: ~3 s lag in RViz the moment an
Image display on the raw topic was added.

Rules:
- **Never pull the RAW image across WiFi.** Keep raw **local on the Pi** (for on-board nav/vision).
- **Remote viewing = always the `compressed` (JPEG) topic** (~30× smaller, ~100 KB/frame).
- **Reduce at the source**: 640×480 + `FrameDurationLimits:=[100000,100000]` (~10 fps) is plenty for a
  preview and very light. Bump up only when actually needed (and only on-board).

## View it on the robot (headless Pi) — the easy way
The Pi has no GUI, so grab a snapshot to a file (the compressed topic is already JPEG → bytes written
as-is, no decoding):
```bash
source /opt/ros/jazzy/setup.bash && source ~/camera_ws/install/setup.bash
python3 ~/cam_snapshot.py            # writes ~/cam_snapshot.jpg  (script in repo scripts/cam_snapshot.py)
```

## View the stream (from the Ubuntu dev PC) — use COMPRESSED
```bash
export ROS_DOMAIN_ID=0 && source /opt/ros/jazzy/setup.bash
ros2 run rqt_image_view rqt_image_view
# in the GUI: topic = /camera/image_raw, then set the transport dropdown to "compressed"
```
Needs `ros-jazzy-rqt-image-view` + `ros-jazzy-image-transport-plugins` on Ubuntu (already installed).
Do **not** add a raw Image display in RViz over WiFi (it lags everything).

## TODO
1. **Calibrate** the camera (checkerboard → real `camera_info` matrices) — required before AprilTag/docking.
2. Fine-tune autofocus (the `dw9807` AF control logs minor warnings; functional but to configure).
3. Refine the camera mount orientation in the URDF.

(Reference: "Camera commissioning" in `~/openamr_hardware_bringup_guide/README_OPENAMR_HARDWARE_BRINGUP.md`.)
