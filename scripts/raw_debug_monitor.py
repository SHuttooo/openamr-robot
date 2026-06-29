#!/usr/bin/env python3
"""Monitor for the firmware debug topics (raw counts per wheel).
Wheels off the ground, turned by hand, WITHOUT 24V power.

/debug/left  (Vector3): x=target rpm, y=measured rpm, z=raw counts  (MOTOR1 left)
/debug/right (Vector3): same for right (MOTOR2)

Live display, ~3 Hz. Ctrl-C to stop.
Goal: verify that the counts (z) move when you turn the wheel.
"""
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Vector3

# The firmware debug publishers are BEST_EFFORT -> we must match.
QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)


class Mon(Node):
    def __init__(self):
        super().__init__('raw_debug_monitor')
        self.create_subscription(Vector3, '/debug/left', self.cl, QOS)
        self.create_subscription(Vector3, '/debug/right', self.cr, QOS)
        self.l = (0.0, 0.0, 0.0)
        self.r = (0.0, 0.0, 0.0)

    def cl(self, m):
        self.l = (m.x, m.y, m.z)

    def cr(self, m):
        self.r = (m.x, m.y, m.z)


def main():
    rclpy.init()
    node = Mon()
    print("Turn each wheel by hand: the COUNTS (cnt) should move.")
    print("Ctrl-C to stop.\n", flush=True)
    last = -1.0
    try:
        while True:
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.time()
            if now - last >= 0.33:
                last = now
                lc, lm, lz = node.l
                rc, rm, rz = node.r
                print(f"L target={lc:+6.1f} meas={lm:+6.1f} cnt={int(lz):+9d}   |   "
                      f"R target={rc:+6.1f} meas={rm:+6.1f} cnt={int(rz):+9d}",
                      flush=True)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


main()
