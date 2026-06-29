#!/usr/bin/env python3
"""Instant snapshot from the robot-side camera (headless Pi).
The /camera/image_raw/compressed topic is already JPEG -> write the bytes as-is.
Usage: source ROS + camera_ws, then: python3 ~/cam_snapshot.py [path.jpg]
"""
import sys, time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from rclpy.qos import qos_profile_sensor_data

OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/botshare/cam_snapshot.jpg"

class Snap(Node):
    def __init__(self):
        super().__init__("cam_snapshot")
        self.done = False
        self.create_subscription(CompressedImage, "/camera/image_raw/compressed",
                                 self.cb, qos_profile_sensor_data)
    def cb(self, m):
        if self.done:
            return
        with open(OUT, "wb") as f:
            f.write(bytes(m.data))
        print(f"snapshot written: {OUT} ({len(m.data)} bytes, format {m.format})")
        self.done = True

def main():
    rclpy.init()
    n = Snap()
    t0 = time.time()
    while rclpy.ok() and not n.done and time.time() - t0 < 8:
        rclpy.spin_once(n, timeout_sec=0.3)
    if not n.done:
        print("NO image received (camera_node launched? camera_ws sourced?)")

if __name__ == "__main__":
    main()
