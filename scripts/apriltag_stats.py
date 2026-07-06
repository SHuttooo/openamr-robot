#!/usr/bin/env python3
"""Measure the REAL AprilTag pipeline the docking consumes.

Reports once a second, for BOTH ends of the pipeline:
  - /apriltag/image_in  : the image FEEDING the detector  -> Hz + latency
  - /apriltag/detections: the detector OUTPUT             -> Hz + latency,
                          per-tag detection Hz, and decision margin (quality).

The gap (DET latency - IMG latency) is the detector's own processing time.

The apriltag node is GATED — enable it first (or run this during a dock):
    ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: true}"
    python3 ~/apriltag_stats.py
    # when done: ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: false}"

Read it: DET Hz should be ~= IMG Hz; if id-Hz{1} collapses (esp. while moving)
the detector is dropping tag 1; low margin = marginal detection.
"""
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from apriltag_msgs.msg import AprilTagDetectionArray


class Stats(Node):
    def __init__(self):
        super().__init__('apriltag_stats')
        best = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT,
                          history=HistoryPolicy.KEEP_LAST)
        rel = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                         history=HistoryPolicy.KEEP_LAST)
        self.create_subscription(Image, '/apriltag/image_in', self.on_img, best)
        self.create_subscription(AprilTagDetectionArray, '/apriltag/detections',
                                 self.on_det, rel)
        self._reset()
        self.t0 = time.time()
        self.create_timer(1.0, self.report)
        self.get_logger().info('measuring /apriltag/image_in + /apriltag/detections ...')

    def _reset(self):
        self.img_n = 0
        self.img_age = 0.0
        self.det_n = 0
        self.det_age = 0.0
        self.seen = {}
        self.margin = {}

    def _age_ms(self, stamp):
        return (self.get_clock().now()
                - rclpy.time.Time.from_msg(stamp)).nanoseconds * 1e-6

    def on_img(self, msg):
        self.img_n += 1
        self.img_age += self._age_ms(msg.header.stamp)

    def on_det(self, msg):
        self.det_n += 1
        self.det_age += self._age_ms(msg.header.stamp)
        for d in msg.detections:
            i = int(d.id)
            self.seen[i] = self.seen.get(i, 0) + 1
            self.margin[i] = float(d.decision_margin)

    def report(self):
        dt = time.time() - self.t0
        img_hz = self.img_n / dt
        det_hz = self.det_n / dt
        img_lat = (self.img_age / self.img_n) if self.img_n else 0.0
        det_lat = (self.det_age / self.det_n) if self.det_n else 0.0
        rates = {k: round(v / dt, 1) for k, v in sorted(self.seen.items())}
        marg = {k: round(self.margin[k]) for k in sorted(self.margin)}
        self.get_logger().info(
            f'IMG {img_hz:4.1f}Hz lat={img_lat:3.0f}ms | '
            f'DET {det_hz:4.1f}Hz lat={det_lat:3.0f}ms | '
            f'id-Hz={rates} margin={marg}')
        self._reset()
        self.t0 = time.time()


def main():
    rclpy.init()
    node = Stats()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
