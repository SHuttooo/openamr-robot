"""
⚠️  LEGACY / OBSOLETE (2026-06-26) — migrating to the platform.
    New, integrated equivalent: openamrobot_bringup/real_bringup.launch.py, launched via
        ros2 launch openamrobot_bringup bringup.launch.py sim:=false
    (data source + Nav2 + docking/forwarder in ONE command).
    Kept functional for field use until the new launch is validated on the
    robot. See docs/ARCHITECTURE.md §6.
================================================================================

Bring-up REEL OpenAMR (base materielle) — un seul lancement :
  - agent micro-ROS (Teensy : /cmd_vel, /odom/unfiltered, /imu/data)
  - driver RPLidar (/scan, frame lidar_link)
  - filtre lidar -> /scan_filtered (enleve la coque du robot ; cf scan_body_filter.py)
  - EKF robot_localization : fusionne /odom/unfiltered + gyro Z de /imu/data
      -> /odom (remappe) + TF odom->base_link   (remplace l'ancien odom_tf_relay)
  - camera_ros (IMX708 NoIR via fork RPi de libcamera) -> /camera/image_raw + /camera/camera_info
  - TF statiques base_link -> {lidar_link, imu_link, base_footprint, camera_link->camera_optical_frame}

Lancer (sourcer AUSSI le workspace camera pour camera_ros) :
  source /opt/ros/jazzy/setup.bash
  source ~/linorobot2_ws/install/setup.bash
  source ~/camera_ws/install/setup.bash     # fork RPi libcamera + camera_ros
  ros2 launch /home/botshare/openamr_real_bringup.launch.py
"""
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

TEENSY = '/dev/serial/by-id/usb-Teensyduino_USB_Serial_16778200-if00'
LIDAR = ('/dev/serial/by-id/'
         'usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0')
EKF_PARAMS = '/home/botshare/ekf.yaml'
SCAN_FILTER = '/home/botshare/scan_body_filter.py'


def generate_launch_description():
    return LaunchDescription([
        ExecuteProcess(
            cmd=['ros2', 'run', 'micro_ros_agent', 'micro_ros_agent',
                 'serial', '-b', '115200', '-D', TEENSY],
            output='screen'),
        Node(
            package='rplidar_ros', executable='rplidar_composition', name='rplidar',
            parameters=[{
                'serial_port': LIDAR,
                'serial_baudrate': 115200,
                'frame_id': 'lidar_link',
                'angle_compensation': True,
                'scan_mode': 'Standard',
            }],
            respawn=True, respawn_delay=3.0,
            output='screen'),
        # Filtre lidar : /scan -> /scan_filtered (masque la coque ; cf mesures 2026-06-18)
        ExecuteProcess(
            cmd=['python3', SCAN_FILTER],
            respawn=True, respawn_delay=3.0,
            output='screen'),
        # EKF : fusion roues + gyro Z IMU -> /odom + TF odom->base_link
        Node(
            package='robot_localization', executable='ekf_node', name='ekf_filter_node',
            parameters=[EKF_PARAMS],
            remappings=[('odometry/filtered', '/odom')],
            output='screen'),
        # base_link -> lidar_link : MESURE (lidar 33.5 cm devant l'axe, centre,
        #   monte TOURNE de 180deg : son 0deg pointe vers l'arriere).
        Node(
            package='tf2_ros', executable='static_transform_publisher', name='base_to_lidar',
            arguments=['--x', '0.335', '--y', '0.0', '--z', '0.18',
                       '--roll', '0.0', '--pitch', '0.0', '--yaw', '3.14159',
                       '--frame-id', 'base_link', '--child-frame-id', 'lidar_link'],
            output='screen'),
        # base_link -> imu_link : identite (IMU penchee ~14deg non modelisee ; on
        #   n'utilise que le gyro Z, robuste a un petit tilt).
        Node(
            package='tf2_ros', executable='static_transform_publisher', name='base_to_imu',
            arguments=['--x', '0.0', '--y', '0.0', '--z', '0.0',
                       '--frame-id', 'base_link', '--child-frame-id', 'imu_link'],
            output='screen'),
        # base_link -> base_footprint : le firmware publie /odom/unfiltered avec
        #   child_frame_id=base_footprint ; identite pour que l'EKF transforme les vitesses.
        Node(
            package='tf2_ros', executable='static_transform_publisher', name='base_to_footprint',
            arguments=['--x', '0.0', '--y', '0.0', '--z', '0.0',
                       '--frame-id', 'base_link', '--child-frame-id', 'base_footprint'],
            output='screen'),
        # --- Camera IMX708 NoIR (camera_ros + fork RPi libcamera depuis ~/camera_ws) ---
        Node(
            package='camera_ros', executable='camera_node', name='camera',
            parameters=[{
                'width': 1280,
                'height': 720,
                'format': 'RGB888',
                'frame_id': 'camera_optical_frame',
                'FrameDurationLimits': [100000, 100000],   # ~10 fps (leger pour le WiFi en compresse)
                # Calibration intrinseque 2026-06-19 (faite en 1280x720 -> resolution DOIT matcher).
                # Le YAML vient de scripts/camera_info.yaml (copie sur le Pi). Remote = topic compresse.
                'camera_info_url': 'file:///home/botshare/camera_info.yaml',
            }],
            respawn=True, respawn_delay=3.0,
            output='screen'),
        # base_link -> camera_link : MESURE (cam 8 cm devant le lidar, centree, ~0.175 m du sol).
        Node(
            package='tf2_ros', executable='static_transform_publisher', name='base_to_camera',
            arguments=['--x', '0.415', '--y', '0.0', '--z', '0.12',
                       '--frame-id', 'base_link', '--child-frame-id', 'camera_link'],
            output='screen'),
        # camera_link -> camera_optical_frame : convention optique ROS (z avant, x droite, y bas).
        Node(
            package='tf2_ros', executable='static_transform_publisher', name='camera_to_optical',
            arguments=['--x', '0.0', '--y', '0.0', '--z', '0.0',
                       '--roll', '-1.5708', '--pitch', '0.0', '--yaw', '-1.5708',
                       '--frame-id', 'camera_link', '--child-frame-id', 'camera_optical_frame'],
            output='screen'),
    ])
