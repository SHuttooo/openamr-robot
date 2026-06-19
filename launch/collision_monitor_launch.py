from launch import LaunchDescription
from launch_ros.actions import Node

# Collision Monitor : intercepte cmd_vel_raw (sortie controller) -> cmd_vel (Teensy).
# Zone FootprintApproach : projette l'empreinte reelle (78x58) le long de la commande
# et ralentit/arrete si collision predite. Config dans nav2_params.yaml (collision_monitor:).

def generate_launch_description():
    params = '/home/botshare/openamr-platform-sw/ros2/src/openamrobot_nav2/config/nav2_params.yaml'
    return LaunchDescription([
        Node(
            package='nav2_collision_monitor',
            executable='collision_monitor',
            name='collision_monitor',
            output='screen',
            parameters=[params],
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_collision',
            output='screen',
            parameters=[{'autostart': True, 'node_names': ['collision_monitor']}],
        ),
    ])
