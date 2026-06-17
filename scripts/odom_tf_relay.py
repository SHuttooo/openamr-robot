#!/usr/bin/env python3
"""Relais odom -> /odom + TF odom->base_link.
Le firmware publie /odom/unfiltered (Odometry avec pose integree, roues seules).
Nav2 attend /odom + la TF odom->base_link. Ce noeud fait le pont.
(Amelioration future : remplacer par un EKF robot_localization fusionnant IMU.)
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
