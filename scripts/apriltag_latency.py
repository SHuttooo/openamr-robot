#!/usr/bin/env python3
"""Featherweight latency probe — subscribes ONLY to /apriltag/detections (tiny
messages, no image), so it adds ~0 CPU. Safe to run DURING a real dock to read
the true detection Hz + latency without perturbing it (unlike the image-based
tools, which themselves eat CPU and inflate the latency they measure).
"""
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from apriltag_msgs.msg import AprilTagDetectionArray


class Latency(Node):
    def __init__(self):
        super().__init__('apriltag_latency')
        rel = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                         history=HistoryPolicy.KEEP_LAST)
        self.create_subscription(AprilTagDetectionArray, '/apriltag/detections',
                                 self.cb, rel)
        self.n = 0
        self.age = 0.0
        self.ids = {}
        self.t0 = time.time()
        self.create_timer(1.0, self.report)
        self.get_logger().info('latency probe (detections only, ~0 CPU)')

    def cb(self, m):
        self.n += 1
        self.age += (self.get_clock().now()
                     - rclpy.time.Time.from_msg(m.header.stamp)).nanoseconds * 1e-6
        for d in m.detections:
            self.ids[int(d.id)] = self.ids.get(int(d.id), 0) + 1

    def report(self):
        dt = time.time() - self.t0
        hz = self.n / dt
        lat = (self.age / self.n) if self.n else 0.0
        r = {k: round(v / dt, 1) for k, v in sorted(self.ids.items())}
        self.get_logger().info(f'DET {hz:4.1f}Hz  lat={lat:3.0f}ms  id-Hz={r}')
        self.n = 0
        self.age = 0.0
        self.ids = {}
        self.t0 = time.time()


def main():
    rclpy.init()
    n = Latency()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    n.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
