#!/usr/bin/env python3
"""POWERED test with debug telemetry (raw counts + pwm).
WHEELS OFF THE GROUND. 24V on the drivers. Hand on the 24V cutoff.

Commands a small forward speed and logs, per wheel:
  measured rpm, raw counts, delta counts (per interval), and the PWM.

Goal: see whether the RIGHT counts drop out (delta ~0) while the PWM
climbs/saturates -> windup confirmed.

Usage: python3 ~/powered_debug_test.py [speed] [dur]
  default: 0.1 m/s, 5 s

Safety:
  - auto-abort if |pwm| > PWM_ABORT (saturation) OR |measured rpm| > RPM_ABORT
  - zeros sent at end / on abort / Ctrl-C
  - the firmware also cuts the motors if no cmd_vel for 200 ms
"""
import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Twist, Vector3

SPEED = float(sys.argv[1]) if len(sys.argv) > 1 else 0.1
DURATION = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
PWM_MAX = 1023          # PWM_BITS=10 -> max 1023
PWM_ABORT = 850         # |pwm| beyond this = saturation -> abort
RPM_ABORT = 45          # |measured rpm| beyond this = runaway -> abort

BE = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                history=HistoryPolicy.KEEP_LAST, depth=10)


class T(Node):
    def __init__(self):
        super().__init__('powered_debug_test')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Vector3, '/debug/left', self.cl, BE)
        self.create_subscription(Vector3, '/debug/right', self.cr, BE)
        self.create_subscription(Vector3, '/debug/pwm', self.cp, BE)
        self.l = (0.0, 0.0, 0.0)   # target, measured, counts
        self.r = (0.0, 0.0, 0.0)
        self.pwm = (0.0, 0.0, 0.0)  # left pwm, right pwm

    def cl(self, m):
        self.l = (m.x, m.y, m.z)

    def cr(self, m):
        self.r = (m.x, m.y, m.z)

    def cp(self, m):
        self.pwm = (m.x, m.y, m.z)

    def send(self, vx):
        t = Twist()
        t.linear.x = vx
        self.pub.publish(t)

    def stop(self, n=15):
        for _ in range(n):
            self.send(0.0)
            time.sleep(0.02)


def main():
    rclpy.init()
    node = T()
    t0 = time.time()
    while time.time() - t0 < 0.6:
        rclpy.spin_once(node, timeout_sec=0.05)

    print(f"CMD lin.x={SPEED:+.3f} m/s for {DURATION:.0f}s  "
          f"(abort if |pwm|>{PWM_ABORT} or |rpm|>{RPM_ABORT})")
    print(" t   | cmd  | LEFT rpm   cnt    d | RIGHT rpm   cnt    d | pwmL  pwmR")
    print("-----+------+----------------------+----------------------+-----------",
          flush=True)

    aborted = None
    prev_lz = node.l[2]
    prev_rz = node.r[2]
    t0 = time.time()
    last = -1.0
    try:
        while time.time() - t0 < DURATION:
            node.send(SPEED)
            rclpy.spin_once(node, timeout_sec=0.05)
            pl, pr = node.pwm[0], node.pwm[1]
            if abs(pl) > PWM_ABORT or abs(pr) > PWM_ABORT:
                aborted = f"PWM saturated (L={pl:.0f} R={pr:.0f})"
                break
            if abs(node.l[1]) > RPM_ABORT or abs(node.r[1]) > RPM_ABORT:
                aborted = f"RPM runaway (L={node.l[1]:.0f} R={node.r[1]:.0f})"
                break
            now = time.time()
            if now - last >= 0.2:
                last = now
                lz, rz = node.l[2], node.r[2]
                dl, dr = int(lz - prev_lz), int(rz - prev_rz)
                prev_lz, prev_rz = lz, rz
                print(f"{now - t0:4.1f} | {SPEED:+.2f} | "
                      f"{node.l[1]:+6.1f} {int(lz):+7d} {dl:+5d} | "
                      f"{node.r[1]:+6.1f} {int(rz):+7d} {dr:+5d} | "
                      f"{pl:+5.0f} {pr:+5.0f}", flush=True)
    except KeyboardInterrupt:
        aborted = "Ctrl-C"
    finally:
        node.stop()

    print("\n----- END -----")
    print(f"abort = {aborted if aborted else 'no (duration elapsed)'}")
    print(f"last pwm  L={node.pwm[0]:+.0f}  R={node.pwm[1]:+.0f}")
    print(f"last rpm  L={node.l[1]:+.1f}  R={node.r[1]:+.1f}")
    node.stop()
    node.destroy_node()
    rclpy.shutdown()


main()
