# ROS 2 architecture (Pi side)

*Last updated: 2026-06-17.*

ROS 2 **Jazzy** on the Pi. Nodes communicate via topics; sensor positions via the TF tree.

## Nodes (current)
| Node | Package | Role |
|---|---|---|
| `micro_ros_agent` | `micro_ros_agent` | bridge to the Teensy (exposes its topics) |
| `odom_tf_relay` | (our script `~/odom_tf_relay.py`) | `/odom/unfiltered` → `/odom` + TF `odom→base_link` |
| `rplidar` | `rplidar_ros` | LiDAR driver → `/scan` |
| `base_to_lidar` | `tf2_ros static_transform_publisher` | static TF `base_link→lidar_link` |
| *(TODO)* SLAM / AMCL / Nav2 | `openamrobot_nav2` | mapping, localization, navigation |
| *(TODO)* camera driver | libcamera-based | `/rgb_image`, `/camera_info` |

All four current nodes are started together by the bring-up launch — see [bringup.md](bringup.md).

## Topics (current)
| Topic | Type | Source | Notes |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | Nav2 / teleop → Teensy | velocity command |
| `/odom/unfiltered` | `nav_msgs/Odometry` | Teensy | wheel odometry (raw) |
| `/odom` | `nav_msgs/Odometry` | `odom_tf_relay` | what Nav2 consumes |
| `/imu/data` | `sensor_msgs/Imu` | Teensy (MPU6500) | accel + gyro (no orientation) |
| `/scan` | `sensor_msgs/LaserScan` | rplidar | frame `lidar_link` |
| `/debug/left,right,pwm` | `geometry_msgs/Vector3` | Teensy | best-effort, debug |
| `/debug/openloop` | `geometry_msgs/Vector3` | → Teensy | open-loop motor test |

Full details (types, QoS, buses): [../01-communication.md](../01-communication.md).

## TF tree
```
map ──(SLAM/AMCL, TODO)──► odom ──(odom_tf_relay)──► base_link ──(static)──► lidar_link
                                                                └──────────► camera_link (TODO)
```
Check it live:
```bash
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link lidar_link
ros2 run tf2_tools view_frames     # generates frames.pdf
```

## Middleware (RMW / DDS)
- Currently **Fast DDS** (ROS 2 default).
- ⚠️ OpenAMR wants **CycloneDDS**: `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` (+ `ROS_DOMAIN_ID=30`
  in the guide). When we switch, **every** node (agent, drivers, Nav2) must use the same RMW or they
  won't see each other.

## Odometry note (and IMU upgrade)
Today `/odom` = **wheel odometry only** (the relay just republishes the Teensy's integrated pose).
The IMU is now working (see [../hardware/imu.md](../hardware/imu.md)) but **not yet fused**. Planned
upgrade: replace the relay with a `robot_localization` **EKF** fusing `/odom/unfiltered` + `/imu/data`
(use only the IMU `angular_velocity.z`; its orientation is invalid) → less heading drift.
