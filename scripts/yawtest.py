#!/usr/bin/env python3
# Measures the TOTAL rotation seen by the EKF odom (cumulative, unwrapped yaw).
# Turn the robot exactly 1 full turn (360 deg) by hand -> compare with the display.
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from nav_msgs.msg import Odometry

class YawTest(Node):
    def __init__(self):
        super().__init__('yaw_test')
        self.create_subscription(Odometry, '/odom', self.cb, 10)
        self.last = None
        self.total = 0.0
        print("Turn the robot SLOWLY exactly 1 turn (360 deg) by hand.")
        print("The 'total' should read ~360 (or -360). (Ctrl-C to finish)\n")

    def cb(self, m):
        q = m.pose.pose.orientation
        yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))
        if self.last is not None:
            d = yaw - self.last
            if d > math.pi: d -= 2*math.pi      # unwrap
            if d < -math.pi: d += 2*math.pi
            self.total += d
        self.last = yaw
        print(f'  instant yaw = {math.degrees(yaw):7.1f} deg   |   TOTAL ROTATION = {math.degrees(self.total):8.1f} deg', end='\r')

def main():
    rclpy.init()
    n = YawTest()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        print(f'\n\n>>> MEASURED TOTAL ROTATION = {math.degrees(n.total):.1f} deg  (target: 360 if you did 1 turn)')
    finally:
        n.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
