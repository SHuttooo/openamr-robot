# ROS 2 architecture (Pi side)

*Last updated: 2026-06-18.*

ROS 2 **Jazzy** on the Pi. Nodes communicate via topics; sensor positions via the TF tree.

## Nodes (current)
| Node | Package | Role |
|---|---|---|
| `micro_ros_agent` | `micro_ros_agent` | bridge to the Teensy (exposes its topics) |
| `rplidar` | `rplidar_ros` | LiDAR driver → `/scan` |
| `scan_body_filter` | (our `~/scan_body_filter.py`) | `/scan` → `/scan_filtered` (masks the robot body) |
| `ekf_filter_node` | `robot_localization` | fuse wheels + IMU gyro Z → `/odom` + TF `odom→base_link` |
| `camera` | `camera_ros` (RPi libcamera fork) | IMX708 → `/camera/image_raw` + `/camera/camera_info` |
| `base_to_lidar` / `base_to_imu` / `base_to_footprint` / `base_to_camera` / `camera_to_optical` | `tf2_ros static_transform_publisher` | static TFs |
| `slam_toolbox` | `slam_toolbox` (online_async) | mapping → `/map` + TF `map→odom` |
| *(TODO)* AMCL / Nav2 | `openamrobot_nav2` | localization, navigation |

The bring-up launch starts everything except SLAM (SLAM is launched separately). See [bringup.md](bringup.md).

## Topics (current)
| Topic | Type | Source | Notes |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | Nav2 / teleop → Teensy | velocity command |
| `/odom/unfiltered` | `nav_msgs/Odometry` | Teensy | wheel odometry (raw), child frame `base_footprint` |
| `/odom` | `nav_msgs/Odometry` | **`ekf_filter_node`** | fused (wheels + IMU yaw rate); what Nav2 consumes |
| `/imu/data` | `sensor_msgs/Imu` | Teensy (MPU6500) | accel + gyro; **only `angular_velocity.z` is usable** |
| `/scan` | `sensor_msgs/LaserScan` | rplidar | frame `lidar_link`, ~7 Hz, ~270 pts/rev |
| `/scan_filtered` | `sensor_msgs/LaserScan` | `scan_body_filter` | robot body masked; SLAM consumes this |
| `/map` | `nav_msgs/OccupancyGrid` | `slam_toolbox` | 0.05 m/cell |
| `/camera/image_raw` (+ `/compressed`) | `sensor_msgs/Image` (bgr8) | `camera` | frame `camera_optical_frame` — **use compressed over WiFi** |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | `camera` | uncalibrated for now |
| `/debug/left,right,pwm` | `geometry_msgs/Vector3` | Teensy | best-effort: x=target rpm, y=measured rpm, z=counts (left/right); pwm |
| `/debug/openloop` | `geometry_msgs/Vector3` | → Teensy | open-loop motor test |

Full details (types, QoS, buses): [../01-communication.md](../reference/01-communication.md).

## TF tree
```
map ──(slam_toolbox)──► odom ──(ekf_filter_node)──► base_link ──(static)──► lidar_link
                                                            ├──(static)──► imu_link
                                                            ├──(static)──► base_footprint
                                                            └──(static)──► camera_link ──► camera_optical_frame
```
Check it live:
```bash
ros2 run tf2_ros tf2_echo odom base_link          # from the EKF
ros2 run tf2_ros tf2_echo base_link camera_optical_frame
ros2 run tf2_tools view_frames                    # generates frames.pdf
```

## Odometry — EKF fusion (done 2026-06-18)
`/odom` and the TF `odom→base_link` now come from a `robot_localization` **EKF** (`~/ekf.yaml`), which
fuses:
- **wheel odometry** `/odom/unfiltered`: `vx` (linear) + `vyaw` (rotation),
- **IMU** `/imu/data`: **only `angular_velocity.z`** (yaw rate). The IMU orientation quaternion is invalid
  (all zeros) and its accel is tilted (~7°), so they are excluded. `two_d_mode: true`.

At rest the gyro Z reads ~0 (firmware deadband → no drift on straight lines); during a turn it tracks the
real rotation well (verified vs wheel odom). The fusion mainly cuts **heading drift in turns** (where the
wheels slip). This **replaced** the old `odom_tf_relay`. The EKF needs `base_footprint` and `imu_link` in
TF (hence the identity static TFs).

## Middleware (RMW / DDS) & remote visualization — ACTUAL setup
- **RMW = CycloneDDS** (`rmw_cyclonedds_cpp`) since 2026-06-18 (switched from Fast DDS for the docking / Nav2 actions; the Pi's `~/.bashrc` exports it). **`ROS_DOMAIN_ID = 0`**.
- To see the Pi's topics from the **Ubuntu dev PC** (RViz/rqt natively): same **domain 0**, same **CycloneDDS**, and **same LAN subnet** (DDS discovery is multicast → it must NOT cross a router). On Ubuntu:
  `export ROS_DOMAIN_ID=0` (the desktop defaults to 42 here — override it).
- OpenAMR recommends CycloneDDS — **now adopted**. **Every** node (agent, drivers, Nav2, the dev PC) must use the same RMW (Cyclone) + same domain.

See [visualization.md](visualization.md) for the full RViz-from-Ubuntu workflow.
