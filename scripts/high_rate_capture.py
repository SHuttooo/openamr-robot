#!/usr/bin/env python3
"""50 Hz capture around a right-wheel jerk. WHEELS IN THE AIR. 24V. Hand on the cutoff.

Commands a small speed, records EVERY /debug/right message (full rate). On the FIRST jerk
(|right rpm| > JERK) it STOPS IMMEDIATELY (zero command) and then logs the coast-down passively
(no further motion). Reads the window of raw right counts around the jerk.

Safety (Raj review PR3/PR5):
  - requires --arm (no powered motion otherwise);
  - validates finite + bounded speed/duration;
  - requires fresh /debug telemetry before any motion;
  - zero command is sent at the trigger instant, then only passive logging.

Interpretation:
  - counts that JUMP then RETURN (delta +N then -N), net ~0  -> FALSE pulse (electrical glitch).
  - counts that drift clearly in one direction               -> REAL motion (driver/motor).

Usage: python3 ~/high_rate_capture.py --arm [speed] [max_duration]   (default 0.05 m/s, 10 s)
"""
import math
import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Twist, Vector3

JERK = 30.0          # |right rpm| beyond = jerk detected -> immediate stop
AFTER = 0.4          # s of PASSIVE coast-down logging after the stop (zero command)
PWM_ABORT = 850
SPEED_LIMIT = 0.30   # m/s — conservative ceiling for this diagnostic
DUR_LIMIT = 30.0     # s

BE = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                history=HistoryPolicy.KEEP_LAST, depth=10)


class Cap(Node):
    def __init__(self):
        super().__init__('high_rate_capture')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Vector3, '/debug/left', self.cl, BE)
        self.create_subscription(Vector3, '/debug/right', self.cr, BE)
        self.create_subscription(Vector3, '/debug/pwm', self.cp, BE)
        self.cntL = 0.0
        self.pwmR = 0.0
        self.pwmL = 0.0
        self.samples = []      # (t, cntL, cntR, rpmR, pwmR)
        self.jerk_t = None
        self.t0 = time.time()

    def cl(self, m):
        self.cntL = m.z

    def cp(self, m):
        self.pwmL = m.x
        self.pwmR = m.y

    def cr(self, m):
        t = time.time() - self.t0
        self.samples.append((t, self.cntL, m.z, m.y, self.pwmR))
        if self.jerk_t is None and abs(m.y) > JERK:
            self.jerk_t = t

    def send(self, vx):
        msg = Twist()
        msg.linear.x = vx
        self.pub.publish(msg)

    def stop(self, n=15):
        for _ in range(n):
            self.send(0.0)
            time.sleep(0.02)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    armed = '--arm' in sys.argv
    speed = float(args[0]) if len(args) > 0 else 0.05
    dur = float(args[1]) if len(args) > 1 else 10.0

    # --- safety gates (Raj review PR3): arm + bounds + finite ---
    if not armed:
        print("REFUSED: powered motion requires --arm. Re-run: high_rate_capture.py --arm [speed] [dur]")
        return
    if not (math.isfinite(speed) and abs(speed) <= SPEED_LIMIT):
        print(f"REFUSED: speed {speed} out of range (need finite, |v| <= {SPEED_LIMIT} m/s).")
        return
    if not (math.isfinite(dur) and 0.0 < dur <= DUR_LIMIT):
        print(f"REFUSED: duration {dur} out of range (need finite, 0 < dur <= {DUR_LIMIT} s).")
        return

    rclpy.init()
    node = Cap()

    # require FRESH telemetry before any motion (Raj PR3): a missing /debug topic must not look
    # like a stopped wheel -> refuse to drive if nothing arrives.
    t = time.time()
    while time.time() - t < 2.0 and not node.samples:
        rclpy.spin_once(node, timeout_sec=0.05)
    if not node.samples:
        print("REFUSED: no /debug/right telemetry (agent/firmware down?). No command sent.")
        node.destroy_node()
        rclpy.shutdown()
        return
    node.samples.clear()
    node.t0 = time.time()

    print(f"CMD {speed:+.3f} m/s, 50 Hz capture, STOP on |rpm_R|>{JERK}", flush=True)
    t0 = time.time()
    try:
        while time.time() - t0 < dur:
            if node.jerk_t is not None:
                print(">>> jerk detected -> IMMEDIATE STOP", flush=True)
                break
            if abs(node.pwmR) > PWM_ABORT or abs(node.pwmL) > PWM_ABORT:
                print(">>> pwm saturated -> abort", flush=True)
                break
            node.send(speed)
            rclpy.spin_once(node, timeout_sec=0.02)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()

    # passive post-stop logging: keep recording the coast-down, command ZERO only.
    t = time.time()
    while time.time() - t < AFTER:
        node.send(0.0)
        rclpy.spin_once(node, timeout_sec=0.02)

    s = node.samples
    print(f"\n{len(s)} samples. jerk_t = {node.jerk_t}")
    if node.jerk_t is None:
        print("No jerk detected (no runaway on this run).")
    else:
        ji = next((i for i, x in enumerate(s) if x[0] >= node.jerk_t), len(s) - 1)
        a = max(0, ji - 20)
        b = min(len(s), ji + 12)
        print("Window around the jerk (>>> = jerk sample):")
        print("   t(s)  | cntL    dL | cntR     dR  | rpm_R | pwm_R")
        print("---------+------------+--------------+-------+------")
        prevL = prevR = None
        for i in range(a, b):
            t, cl, cr, rpm, pwm = s[i]
            dL = "" if prevL is None else f"{int(cl - prevL):+4d}"
            dR = "" if prevR is None else f"{int(cr - prevR):+5d}"
            prevL, prevR = cl, cr
            mark = ">>>" if i == ji else "   "
            print(f"{mark}{t:6.2f} | {int(cl):6d} {dL:>4} | {int(cr):7d} {dR:>5} | "
                  f"{rpm:+5.1f} | {pwm:+5.0f}", flush=True)
    node.stop()
    node.destroy_node()
    rclpy.shutdown()


main()
