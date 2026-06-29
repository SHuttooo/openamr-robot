#!/usr/bin/env python3
"""ASCII view of the scan + FRONT estimation from the open arc.

Bins the scan BY ANGLE (robust to a varying point count). For each 10 deg
sector, shows the min distance. The robot body blocks part of it (very close /
absent returns) -> the OPEN arc (toward the room) has its center = the front.

Run:  python3 ~/lidar_view.py
Tip: place your object straight ahead, it will show up as a clear distance dip
in a sector -> this confirms where the front is.
"""
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan

QOS = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                 history=HistoryPolicy.KEEP_LAST, depth=10)
SECT = 10            # degrees per sector
BLOCK = 0.35         # m: below = blocked (robot body)


class V(Node):
    def __init__(self):
        super().__init__('lidar_view')
        self.create_subscription(LaserScan, '/scan', self.cb, QOS)
        self.acc = {}     # sector (deg, multiple of SECT, -180..170) -> min dist

    def cb(self, msg):
        for i, r in enumerate(msg.ranges):
            if not (msg.range_min < r < msg.range_max):
                continue
            ang = math.degrees(msg.angle_min + i * msg.angle_increment)
            s = int(math.floor(ang / SECT) * SECT)
            if s not in self.acc or r < self.acc[s]:
                self.acc[s] = r


def main():
    rclpy.init()
    node = V()
    t0 = time.time()
    while time.time() - t0 < 2.0:
        rclpy.spin_once(node, timeout_sec=0.05)

    sectors = list(range(-180, 180, SECT))
    print("\nSCAN — min distance per sector (LIDAR frame, 0deg = sensor front)")
    print(" angle |  dist  | (wall/object)          state")
    print("-------+--------+--------------------------------")
    open_secs = []
    for s in sectors:
        d = node.acc.get(s)
        if d is None:
            print(f" {s:+4d}  |   --   |                          (none)")
        elif d < BLOCK:
            print(f" {s:+4d}  | {d:5.2f}  | {'#'*min(int(d*10),24):24s} BLOCKED")
        else:
            print(f" {s:+4d}  | {d:5.2f}  | {'#'*min(int(d*10),24):24s} open")
            open_secs.append(s)

    # center of the open arc (handles the +-180 wrap)
    if open_secs:
        xs = [math.cos(math.radians(s + SECT / 2)) for s in open_secs]
        ys = [math.sin(math.radians(s + SECT / 2)) for s in open_secs]
        center = math.degrees(math.atan2(sum(ys), sum(xs)))
        print("-------+--------+--------------------------------")
        print(f"Center of the OPEN arc ~ {center:+.0f} deg  (= likely robot front)")
        print(f" -> yaw TF base_link->lidar_link ~ {-center:+.0f} deg = {math.radians(-center):+.3f} rad")
        print("(to confirm: place the object straight ahead, it should fall near this center)")
    node.destroy_node()
    rclpy.shutdown()


main()
