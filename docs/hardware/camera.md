# Camera (Pi Camera Module 3 / IMX708)

*Last updated: 2026-06-17.*

> **Status: NOT configured yet.** This sheet documents what we know and what remains to do.

## Overview
| | |
|---|---|
| Module | Raspberry Pi Camera Module 3 (Sony **IMX708** sensor) |
| Interface | **CSI** (MIPI ribbon to the Pi), **not USB** |

## Communication (Pi ↔ camera)
- **CSI / MIPI** ribbon directly into the Pi's camera connector. A CSI camera is handled by **libcamera**
  (e.g. `rpicam-hello`/`libcamera-hello`), not by `usb_cam`.
- Linux currently exposes many `/dev/video*` nodes (≈ video19–video37) but most are codec/ISP/metadata
  endpoints, **not** the actual capture device — the real capture node must be identified.

## Mounting (measured — for when we set it up)
Physical position relative to `base_link` (center of the wheel axle):
- **x ≈ 0.415 m** (8 cm in front of the LiDAR, which is at x=0.335)
- **y = 0** (centered)
- **height above ground = 0.175 m** → **z ≈ 0.12 m** relative to `base_link` (base_link is ~0.05 m above ground)
- Orientation: assumed facing forward (TBD). Note ROS uses a **`camera_optical_frame`** convention
  (optical frame: z forward, x right, y down) — define `base_link→camera_link→camera_optical_frame` accordingly.

## What it must provide (ROS contract)
| Topic | Type | Frame |
|---|---|---|
| `/rgb_image` | `sensor_msgs/msg/Image` | camera_optical_frame |
| `/camera_info` | `sensor_msgs/msg/CameraInfo` | camera_optical_frame |

## TODO
1. Identify the real camera capture device (`rpicam-hello --list-cameras`, `v4l2-ctl --list-devices`,
   inspect `/dev/video*` formats).
2. Set up a libcamera-compatible ROS 2 driver (or an image pipeline) that publishes `/rgb_image`.
3. **Calibrate** the camera (checkerboard → non-zero `camera_info` matrices) — required before any
   AprilTag / vision-based docking.

(Reference: section "Camera commissioning" in `~/openamr_hardware_bringup_guide/README_OPENAMR_HARDWARE_BRINGUP.md`.)
