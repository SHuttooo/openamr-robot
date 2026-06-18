# Remote visualization (RViz / rqt from the Ubuntu dev PC)

*Last updated: 2026-06-18.*

The Pi is **headless** (Ubuntu Server). We visualize from a separate **Ubuntu 24.04 desktop** running
ROS 2 Jazzy natively (RViz, rqt). This is the workflow used on 2026-06-18.

## Prerequisites (must all match the Pi)
| Setting | Value | Why |
|---|---|---|
| `ROS_DOMAIN_ID` | **0** | Pi runs domain 0 (nothing set in its env). The dev desktop defaults to **42** → override it. |
| `RMW_IMPLEMENTATION` | **rmw_fastrtps_cpp** (Fast DDS) | Pi uses the default Fast DDS. |
| LAN subnet | **same** as the Pi (e.g. both `172.17.x.x/16`) | Fast DDS discovery is **multicast** → it does **not** cross a router. Different WiFi/subnet ⇒ no topics. |

```bash
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/jazzy/setup.bash
ros2 topic list            # should show /scan, /odom, /imu/data, /map, /camera/... from the Pi
```
If the list is empty: wrong domain, wrong RMW, or different subnet. (`ros2 daemon stop && ros2 daemon start`
after changing the domain.)

## RViz for SLAM / scan / TF
A ready config lives in the repo: `scripts/openamr_slam.rviz` (Grid, TF, LaserScan RAW `/scan` in red,
LaserScan FILTERED `/scan_filtered` in green, Map `/map`; Fixed Frame `map`).
```bash
rviz2 -d scripts/openamr_slam.rviz
```
Tips:
- "Lookup would require extrapolation into the future" at startup = TF/clock jitter, clears once the TF
  buffer fills (SLAM runs on the Pi's single clock, so it's unaffected).
- The Pi and the desktop clocks may differ by ~1 s (SSH-measured); harmless here (RViz uses message stamps).

## Camera — ALWAYS use the compressed transport over WiFi
**Never** add a raw `/camera/image_raw` Image display in RViz over WiFi: the raw stream (~2.76 MB/frame)
saturates the link and lags **everything** (camera + scan + map; ~3 s lag observed). Instead:
```bash
ros2 run rqt_image_view rqt_image_view
# topic = /camera/image_raw, then set the transport dropdown to "compressed"
```
Needs `ros-jazzy-rqt-image-view` + `ros-jazzy-image-transport-plugins` on the desktop.
On the robot side (headless), grab a snapshot instead: `python3 ~/cam_snapshot.py` → `~/cam_snapshot.jpg`.

## SSH gotcha (running things on the Pi from scripts)
`pkill -f <pattern>` matches its **own** command line → it kills the SSH session (exit 255). Use the
bracket trick: `pkill -f "[s]can_body_filter.py"`, `pkill -f "[a]sync_slam_toolbox"`, etc.
Also: foreground `sleep` is blocked in some automated shells — sleep inside the remote SSH command instead.
