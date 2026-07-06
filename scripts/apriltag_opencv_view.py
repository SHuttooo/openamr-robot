#!/usr/bin/env python3
"""OpenCV AprilTag 36h11 detector / viewer — diagnostic for the dock tags.

Subscribes to the RAW camera image (built into a numpy array directly, no
cv_bridge, no JPEG decode), runs cv2.aruco 36h11 detection INDEPENDENTLY of the
ROS apriltag node, overlays the result and republishes it as a raw Image on
/apriltag_debug (view via web_video_server), and logs once a second which tag
IDs are seen and at what rate.

Point: on the REAL image, is a tag actually detectable? If OpenCV sees the tags
fine here but the ROS apriltag node keeps dropping them, the node is mis-tuned;
if OpenCV also struggles, the IMAGE is the problem (focus / motion blur /
exposure). It also seeds an OpenCV-based central-tag tracker (id 1).

Run on the Pi (camera is local):
    python3 ~/apriltag_opencv_view.py
View the overlay:
    http://172.17.201.29:8080/stream?topic=/apriltag_debug
    (start web_video_server first if needed: ros2 run web_video_server web_video_server)
"""
import sys
import time
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

# Detection width: the gray image is downscaled to this width BEFORE detection
# (huge speed win → lower latency). Pass 0 to detect at full resolution.
#   python3 apriltag_opencv_view.py [detect_width]   (default 640)
DETECT_WIDTH = int(sys.argv[1]) if len(sys.argv) > 1 else 640

_D = cv2.aruco.DICT_APRILTAG_36h11
try:                                              # OpenCV >= 4.7 (new API)
    _dict = cv2.aruco.getPredefinedDictionary(_D)
    _det = cv2.aruco.ArucoDetector(_dict, cv2.aruco.DetectorParameters())
    def detect(gray):
        return _det.detectMarkers(gray)
except AttributeError:                            # OpenCV 4.6 (old API, the Pi)
    _dict = cv2.aruco.Dictionary_get(_D)
    _params = cv2.aruco.DetectorParameters_create()
    def detect(gray):
        return cv2.aruco.detectMarkers(gray, _dict, parameters=_params)

_CH = {'rgb8': 3, 'bgr8': 3, 'rgba8': 4, 'bgra8': 4, 'mono8': 1}


def to_bgr(msg):
    """sensor_msgs/Image -> BGR ndarray, or None if the encoding is unhandled."""
    ch = _CH.get(msg.encoding, 0)
    if ch == 0:
        return None
    buf = np.frombuffer(msg.data, np.uint8)
    if buf.size < msg.height * msg.step:
        return None
    frame = buf[:msg.height * msg.step].reshape(msg.height, msg.step)
    frame = frame[:, :msg.width * ch].reshape(msg.height, msg.width, ch)
    if msg.encoding == 'rgb8':
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    if msg.encoding == 'bgr8':
        return frame.copy()
    if msg.encoding == 'rgba8':
        return cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
    if msg.encoding == 'bgra8':
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    if msg.encoding == 'mono8':
        return cv2.cvtColor(frame.reshape(msg.height, msg.width), cv2.COLOR_GRAY2BGR)
    return None


class AprilOpenCV(Node):
    def __init__(self):
        super().__init__('apriltag_opencv_view')
        # depth=1 keep-last: always process the FRESHEST frame, never a backlog
        # (a queue would add latency that isn't the camera's fault).
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST)
        self.create_subscription(Image, '/camera/image_raw', self.cb, qos)
        self.pub = self.create_publisher(Image, '/apriltag_debug', 1)
        self.n = 0
        self.seen = {}
        self.age_sum = 0.0        # sum of image ages (ms) — pipeline latency
        self.det_sum = 0.0        # sum of detect times (ms)
        self.t0 = time.time()
        self._logged = False
        w = DETECT_WIDTH if DETECT_WIDTH else 'full'
        self.get_logger().info(
            f'OpenCV 36h11 detector up — detect_width={w} — /apriltag_debug')

    def cb(self, msg):
        img = to_bgr(msg)
        if img is None:
            if not self._logged:
                self.get_logger().warn(
                    f'unhandled/short image: enc={msg.encoding!r} '
                    f'{msg.width}x{msg.height} step={msg.step} bytes={len(msg.data)}')
                self._logged = True
            return
        if not self._logged:
            self.get_logger().info(f'image {msg.width}x{msg.height} {msg.encoding}')
            self._logged = True

        # Pipeline latency = age of the image when we receive it (capture->here).
        age_ms = (self.get_clock().now()
                  - rclpy.time.Time.from_msg(msg.header.stamp)).nanoseconds * 1e-6

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Downscale before detection — the whole point of the optimisation.
        scale = 1.0
        if DETECT_WIDTH and gray.shape[1] > DETECT_WIDTH:
            scale = DETECT_WIDTH / gray.shape[1]
            det_gray = cv2.resize(gray, (DETECT_WIDTH, int(gray.shape[0] * scale)))
        else:
            det_gray = gray
        t_det = time.time()
        corners, ids, _ = detect(det_gray)
        det_ms = (time.time() - t_det) * 1e3
        self.n += 1
        self.age_sum += age_ms
        self.det_sum += det_ms
        found = []
        if ids is not None:
            # Map corners back to full-resolution image coords for the overlay.
            corners = [c / scale for c in corners]
            cv2.aruco.drawDetectedMarkers(img, corners, ids)
            for c, i in zip(corners, ids.flatten()):
                i = int(i)
                found.append(i)
                self.seen[i] = self.seen.get(i, 0) + 1
                ctr = c[0].mean(axis=0).astype(int)
                cv2.circle(img, tuple(ctr), 6, (0, 0, 255), -1)
                cv2.putText(img, f'id{i}', (ctr[0] + 8, ctr[1]),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(img, f'ids: {sorted(found)}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        self._publish(img)

        dt = time.time() - self.t0
        if dt >= 1.0:
            rates = {k: round(v / dt, 1) for k, v in sorted(self.seen.items())}
            self.get_logger().info(
                f'fps={self.n / dt:.1f}  latency={self.age_sum / self.n:.0f}ms  '
                f'detect={self.det_sum / self.n:.0f}ms  id-Hz={rates}')
            self.n = 0
            self.seen = {}
            self.age_sum = 0.0
            self.det_sum = 0.0
            self.t0 = time.time()

    def _publish(self, img):
        # Downscale the overlay to keep the browser stream light (so the VIEW lag
        # isn't a red herring vs the measured pipeline latency).
        h, w = img.shape[:2]
        if w > 640:
            img = cv2.resize(img, (640, int(640 * h / w)))
        m = Image()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = 'camera_optical_frame'
        m.height, m.width = img.shape[:2]
        m.encoding = 'bgr8'
        m.is_bigendian = 0
        m.step = m.width * 3
        m.data = img.tobytes()
        self.pub.publish(m)


def main():
    rclpy.init()
    node = AprilOpenCV()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
