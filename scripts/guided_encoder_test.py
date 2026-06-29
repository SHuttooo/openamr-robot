#!/usr/bin/env python3
"""Guided encoder test (wheels in the air, by hand, WITHOUT 24V power).

The script tells you what to do and when, with a countdown, detects motion
live, and prints a conclusion. Run it in YOUR terminal:

    python3 ~/guided_encoder_test.py

Velocities reconstructed from /odom/unfiltered:
    v_right = lin.x + ang.z * (LR/2)
    v_left  = lin.x - ang.z * (LR/2)
"""
import time
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

LR = 0.46   # wheel separation (m), matches firmware LR_WHEELS_DISTANCE (was 0.45 — Raj review PR3)
HALF = LR / 2.0
SEUIL = 0.01  # m/s: above = motion detected


class Mon(Node):
    def __init__(self):
        super().__init__('guided_encoder_test')
        self.create_subscription(Odometry, '/odom/unfiltered', self.cb, 10)
        self.vl = 0.0
        self.vr = 0.0

    def cb(self, msg):
        lin = msg.twist.twist.linear.x
        ang = msg.twist.twist.angular.z
        self.vr = lin + ang * HALF
        self.vl = lin - ang * HALF


def phase(node, titre, secondes, mesurer=True):
    print("\n" + "=" * 50)
    print(titre)
    print("=" * 50, flush=True)
    max_l = 0.0
    max_r = 0.0
    t0 = time.time()
    last_print = -1
    while time.time() - t0 < secondes:
        rclpy.spin_once(node, timeout_sec=0.05)
        if mesurer:
            max_l = max(max_l, abs(node.vl))
            max_r = max(max_r, abs(node.vr))
        restant = int(secondes - (time.time() - t0)) + 1
        if restant != last_print:
            last_print = restant
            live = ""
            if mesurer:
                gl = "LEFT✓" if abs(node.vl) > SEUIL else "left·"
                dr = "RIGHT✓" if abs(node.vr) > SEUIL else "right·"
                live = f"   [{gl}  {dr}]  vl={node.vl:+.3f} vr={node.vr:+.3f}"
            print(f"   {restant:2d}s...{live}", flush=True)
    return max_l, max_r


def main():
    rclpy.init()
    node = Mon()
    # flush the startup transient spike
    phase(node, "INIT - don't touch anything (startup flush)", 3, mesurer=False)
    gl, gr = phase(node, ">>> TURN THE  L-E-F-T  WHEEL  (MOTOR1) <<<", 10)
    phase(node, "PAUSE - stop everything", 3, mesurer=False)
    dl, dr = phase(node, ">>> TURN THE  R-I-G-H-T  WHEEL  (MOTOR2) <<<", 10)

    print("\n" + "#" * 50)
    print("RESULT")
    print("#" * 50)
    print(f"LEFT phase turned : max v_left={gl:.3f}  max v_right={gr:.3f}")
    print(f"RIGHT phase turned: max v_left={dl:.3f}  max v_right={dr:.3f}")
    print("-" * 50)
    enc_g = gl > SEUIL or dl > SEUIL  # a signal while turning left
    enc_d = gr > SEUIL or dr > SEUIL  # a signal while turning right

    def verdict(nom, max_attendu, max_autre):
        if max_attendu > SEUIL and max_autre <= SEUIL:
            return f"{nom}: OK (encoder counts, correct channel)"
        if max_attendu <= SEUIL and max_autre > SEUIL:
            return f"{nom}: signal on the WRONG channel (wiring/assignment swapped?)"
        if max_attendu <= SEUIL and max_autre <= SEUIL:
            return f"{nom}: NO signal -> encoder silent (dead/unplugged?)"
        return f"{nom}: signal on BOTH channels (strange)"

    print(verdict("LEFT wheel", gl, gr))
    print(verdict("RIGHT wheel", dr, dl))
    print("#" * 50, flush=True)

    node.destroy_node()
    rclpy.shutdown()


main()
