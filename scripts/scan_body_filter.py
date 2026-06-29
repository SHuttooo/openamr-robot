#!/usr/bin/env python3
"""OpenAMR lidar filter: /scan -> /scan_filtered.

The lidar is mounted ROTATED by 180deg: in the lidar frame,
  0deg   = REAR of the robot
  +-180  = FRONT of the robot
  -90    = left, +90 = right

Two kinds of sectors (measured 2026-06-18 via per-angle profiling):

1) FULL_MASK_SECTORS: the rear shell blocks EVERYTHING -> nothing real behind.
   We mask at ALL distances (otherwise we keep the shell, e.g. the central
   return at 0.72 m which IS the shell, not a wall).
     rear: -45 .. +45  (center 0.72 m, corners 0.24-0.30 m)

2) CLOSE_MASK_SECTORS: thin lateral posts (0.17-0.18 m) BUT real walls
   are visible farther away in the same direction -> we only remove the close
   ones (< CLOSE_MAX), keeping the walls.
     left side:  -96 .. -73
     right side: +73 .. +96

Edit these lists while watching RViz to fine-tune.
"""
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, HistoryPolicy

FULL_MASK_SECTORS_DEG = [(-45.0, 49.0)]            # rear shell: remove everything (right goes to +49)
CLOSE_MASK_SECTORS_DEG = [(-96.0, -73.0), (73.0, 96.0)]  # posts: only the close part
CLOSE_MAX = 0.40   # in the "close" sectors, only remove < 0.40 m (= post)


class ScanBodyFilter(Node):
    def __init__(self):
        super().__init__("scan_body_filter")
        self.full = [(math.radians(a), math.radians(b)) for a, b in FULL_MASK_SECTORS_DEG]
        self.close = [(math.radians(a), math.radians(b)) for a, b in CLOSE_MASK_SECTORS_DEG]
        # Publish RELIABLE: serves the costmap (reliable) AND AMCL/RViz (best_effort).
        # In best_effort, the costmap (which subscribes reliable) received NOTHING -> empty costmaps.
        pub_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
        self.pub = self.create_publisher(LaserScan, "/scan_filtered", pub_qos)
        self.sub = self.create_subscription(LaserScan, "/scan", self.cb, qos_profile_sensor_data)
        self.get_logger().info(
            f"scan_body_filter active | rear(full)={FULL_MASK_SECTORS_DEG} | "
            f"sides(<{CLOSE_MAX}m)={CLOSE_MASK_SECTORS_DEG} -> /scan_filtered")

    def in_any(self, sectors, ang):
        for lo, hi in sectors:
            if lo <= ang <= hi:
                return True
        return False

    def cb(self, m):
        out = LaserScan()
        out.header = m.header
        out.angle_min = m.angle_min
        out.angle_max = m.angle_max
        out.angle_increment = m.angle_increment
        out.time_increment = m.time_increment
        out.scan_time = m.scan_time
        out.range_min = m.range_min
        out.range_max = m.range_max
        inf = float("inf")
        r = list(m.ranges)
        for i in range(len(r)):
            v = r[i]
            if not math.isfinite(v):
                continue
            ang = m.angle_min + i * m.angle_increment
            if self.in_any(self.full, ang):
                r[i] = inf                       # rear shell: remove everything
            elif v < CLOSE_MAX and self.in_any(self.close, ang):
                r[i] = inf                       # close lateral post
        out.ranges = r
        out.intensities = m.intensities
        self.pub.publish(out)


def main():
    rclpy.init()
    rclpy.spin(ScanBodyFilter())


if __name__ == "__main__":
    main()
