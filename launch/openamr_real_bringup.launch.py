"""Bring-up REEL OpenAMR (base matérielle) — démarre en un seul lancement :
  - agent micro-ROS (Teensy : /cmd_vel, /odom/unfiltered, /imu/data)
  - driver RPLidar (/scan, frame lidar_link)
  - relais odom -> /odom + TF odom->base_link
  - TF statique base_link -> lidar_link  (offset PLACEHOLDER, à mesurer)

Lancer :  ros2 launch /home/botshare/openamr_real_bringup.launch.py
"""
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

TEENSY = '/dev/serial/by-id/usb-Teensyduino_USB_Serial_16778200-if00'
LIDAR = ('/dev/serial/by-id/'
         'usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0')


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
        ExecuteProcess(
            cmd=['python3', '/home/botshare/odom_tf_relay.py'],
            output='screen'),
        # base_link -> lidar_link : MESURE sur le robot reel.
        #   x=0.335 (lidar 33.5 cm devant l'axe des roues), y=0 (centre), z~0.18,
        #   yaw=pi : le lidar est monte TOURNE de 180deg (son 0deg pointe vers l'arriere).
        Node(
            package='tf2_ros', executable='static_transform_publisher',
            name='base_to_lidar',
            arguments=['--x', '0.335', '--y', '0.0', '--z', '0.18',
                       '--roll', '0.0', '--pitch', '0.0', '--yaw', '3.14159',
                       '--frame-id', 'base_link', '--child-frame-id', 'lidar_link'],
            output='screen'),
    ])
