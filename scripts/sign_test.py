#!/usr/bin/env python3
"""Encoder SIGN test (wheels off the ground, by hand, WITHOUT 24V power).

Goal: verify that rolling a wheel in the robot's FORWARD direction gives a
POSITIVE measured speed. If the right one comes out negative when going
forward -> MOTOR2_ENCODER_INV is wrong -> likely cause of the runaway.

Run in YOUR terminal:  python3 ~/sign_test.py
Continuously displays signed vl and vr. Ctrl-C to stop.

    v_right = lin.x + ang.z * (LR/2)
    v_left  = lin.x - ang.z * (LR/2)
"""
import time
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

LR = 0.46   # wheel separation (m), matches firmware LR_WHEELS_DISTANCE (was 0.45 — Raj review PR3)
HALF = LR / 2.0
SEUIL = 0.01


class Mon(Node):
    def __init__(self):
        super().__init__('sign_test')
        self.create_subscription(Odometry, '/odom/unfiltered', self.cb, 10)
        self.vl = 0.0
        self.vr = 0.0

    def cb(self, msg):
        lin = msg.twist.twist.linear.x
        ang = msg.twist.twist.angular.z
        self.vr = lin + ang * HALF
        self.vl = lin - ang * HALF


def fleche(v):
    if v > SEUIL:
        return "FORWARD (+)"
    if v < -SEUIL:
        return "BACKWARD(-)"
    return "  ~0       "


def main():
    rclpy.init()
    node = Mon()
    print("Roll each wheel in the robot's FORWARD direction.")
    print("Expected: BOTH should display FORWARD (+).")
    print("Ctrl-C to stop.\n", flush=True)
    t0 = time.time()
    last = -1.0
    try:
        while True:
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.time()
            if now - last >= 0.4:
                last = now
                print(f"LEFT vl={node.vl:+.3f} {fleche(node.vl)}   |   "
                      f"RIGHT vr={node.vr:+.3f} {fleche(node.vr)}", flush=True)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


main()
