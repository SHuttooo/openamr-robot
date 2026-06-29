#!/usr/bin/env python3
"""⚠️ LEGACY / OBSOLETE (2026-06-26) — replaced by the robot_localization EKF (ekf.yaml).
The EKF already publishes /odom + the odom->base_link TF. Running this node IN ADDITION
creates a SECOND publisher of the odom->base_link TF -> flickering TF, unstable AMCL/costmaps.
Do NOT run alongside the EKF bring-up. Kept only for historical reference.

Relay odom -> /odom + TF odom->base_link.
The firmware publishes /odom/unfiltered (Odometry with integrated pose, wheels only).
Nav2 expects /odom + the odom->base_link TF. This node bridges the two.
(Superseded by a robot_localization EKF fusing the IMU.)
"""
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster


class OdomRelay(Node):
    def __init__(self):
        super().__init__('odom_tf_relay')
        self.pub = self.create_publisher(Odometry, '/odom', 10)
        self.br = TransformBroadcaster(self)
        self.create_subscription(Odometry, '/odom/unfiltered', self.cb, 20)

    def cb(self, msg):
        msg.header.frame_id = 'odom'
        msg.child_frame_id = 'base_link'
        self.pub.publish(msg)

        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = 0.0
        t.transform.rotation = msg.pose.pose.orientation
        self.br.sendTransform(t)


def main():
    rclpy.init()
    node = OdomRelay()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


main()
