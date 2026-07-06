#!/usr/bin/env python3
"""Overlay the ROS AprilTag node's OWN detections onto the image it processes.

Subscribes /apriltag/image_in (the frame fed to the detector) + /apriltag/detections
(the detector output: corners, id, margin), draws them, republishes to
/apriltag/detection_overlay. Shows EXACTLY what the docking's detector sees/finds
(NOT a separate OpenCV detection).

View: http://172.17.201.29:8080/stream?topic=/apriltag/detection_overlay
(apriltag must be enabled so /apriltag/image_in + detections flow).
"""
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from apriltag_msgs.msg import AprilTagDetectionArray

_CH = {'rgb8': 3, 'bgr8': 3, 'rgba8': 4, 'bgra8': 4, 'mono8': 1}


def to_bgr(m):
    ch = _CH.get(m.encoding, 0)
    if not ch:
        return None
    b = np.frombuffer(m.data, np.uint8)
    if b.size < m.height * m.step:
        return None
    f = b[:m.height * m.step].reshape(m.height, m.step)[:, :m.width * ch].reshape(m.height, m.width, ch)
    if m.encoding == 'rgb8':
        return cv2.cvtColor(f, cv2.COLOR_RGB2BGR)
    if m.encoding == 'bgr8':
        return f.copy()
    if m.encoding == 'rgba8':
        return cv2.cvtColor(f, cv2.COLOR_RGBA2BGR)
    if m.encoding == 'bgra8':
        return cv2.cvtColor(f, cv2.COLOR_BGRA2BGR)
    if m.encoding == 'mono8':
        return cv2.cvtColor(f.reshape(m.height, m.width), cv2.COLOR_GRAY2BGR)
    return None


class Overlay(Node):
    def __init__(self):
        super().__init__('apriltag_det_overlay')
        best = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                          history=HistoryPolicy.KEEP_LAST)
        rel = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                         history=HistoryPolicy.KEEP_LAST)
        self.create_subscription(Image, '/apriltag/image_in', self.on_img, best)
        self.create_subscription(AprilTagDetectionArray, '/apriltag/detections',
                                 self.on_det, rel)
        self.pub = self.create_publisher(Image, '/apriltag/detection_overlay', 1)
        self.dets = []
        self.get_logger().info('overlay up — /apriltag/detection_overlay')

    def on_det(self, msg):
        self.dets = msg.detections

    def on_img(self, msg):
        img = to_bgr(msg)
        if img is None:
            return
        for d in self.dets:
            pts = np.array([[int(c.x), int(c.y)] for c in d.corners], np.int32)
            cv2.polylines(img, [pts], True, (0, 255, 0), 2)
            cx, cy = int(d.centre.x), int(d.centre.y)
            cv2.circle(img, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(img, f'id{d.id} m{int(d.decision_margin)}', (cx + 8, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(img, f'dets: {[int(d.id) for d in self.dets]}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        self._publish(img)

    def _publish(self, img):
        h, w = img.shape[:2]
        if w > 640:
            img = cv2.resize(img, (640, int(640 * h / w)))
        m = Image()
        m.header.stamp = self.get_clock().now().to_msg()
        m.height, m.width = img.shape[:2]
        m.encoding = 'bgr8'
        m.is_bigendian = 0
        m.step = m.width * 3
        m.data = img.tobytes()
        self.pub.publish(m)


def main():
    rclpy.init()
    n = Overlay()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    n.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
