#!/usr/bin/env python3
"""OPEN-LOOP test: same fixed PWM on both motors (PID ignored).
WHEELS OFF THE GROUND. 24V. Hand on the cutoff. IDENTICAL pots (3.5 / 3.5).

Publishes /debug/openloop (x=PWM) at 20 Hz for DUR, logs /debug/left and
/debug/right (raw counts + measured rpm). Comparison: at identical PWM and
identical pots, both wheels MUST react similarly.
  - similar and smooth         -> both channels are healthy
  - right erratic/stalls/jumps -> right-channel fault (motor/Hall or encoder)

Usage: python3 ~/openloop_test.py [pwm] [dur]
  default: pwm=120, dur=10
Safety: abort if |rpm| > 60; sends 0 at end / abort / Ctrl-C;
the firmware also cuts off if no openloop command for 300 ms.
"""
import math
import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Vector3

_args = [a for a in sys.argv[1:] if not a.startswith('--')]
ARMED = '--arm' in sys.argv
PWM = float(_args[0]) if len(_args) > 0 else 120.0
DUR = float(_args[1]) if len(_args) > 1 else 10.0
RPM_ABORT = 60.0
PWM_LIMIT = 500.0    # conservative diagnostic ceiling (Raj review PR3)
DUR_LIMIT = 30.0

BE = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                history=HistoryPolicy.KEEP_LAST, depth=10)


class OL(Node):
    def __init__(self):
        super().__init__('openloop_test')
        self.pub = self.create_publisher(Vector3, '/debug/openloop', 10)
        self.create_subscription(Vector3, '/debug/left', self.cl, BE)
        self.create_subscription(Vector3, '/debug/right', self.cr, BE)
        self.l = (0.0, 0.0, 0.0)   # target, measured, counts
        self.r = (0.0, 0.0, 0.0)
        self.seen = False          # any fresh telemetry arrived?

    def cl(self, m):
        self.l = (m.x, m.y, m.z)
        self.seen = True

    def cr(self, m):
        self.r = (m.x, m.y, m.z)
        self.seen = True

    def send(self, pwm):
        v = Vector3()
        v.x = float(pwm)
        self.pub.publish(v)

    def stop(self, n=15):
        for _ in range(n):
            self.send(0.0)
            time.sleep(0.02)


def main():
    # --- safety gates (Raj review PR3): arm + bounds + finite + fresh telemetry ---
    if not ARMED:
        print("REFUSED: powered motion requires --arm. Re-run: openloop_test.py --arm [pwm] [dur]")
        return
    if not (math.isfinite(PWM) and abs(PWM) <= PWM_LIMIT):
        print(f"REFUSED: PWM {PWM} out of range (finite, |pwm| <= {PWM_LIMIT}).")
        return
    if not (math.isfinite(DUR) and 0.0 < DUR <= DUR_LIMIT):
        print(f"REFUSED: duration {DUR} out of range (0 < dur <= {DUR_LIMIT} s).")
        return

    rclpy.init()
    node = OL()
    # require FRESH telemetry before any motion: a missing /debug topic must not look like a
    # stopped wheel.
    t0 = time.time()
    while time.time() - t0 < 2.0 and not node.seen:
        rclpy.spin_once(node, timeout_sec=0.05)
    if not node.seen:
        print("REFUSED: no /debug telemetry (agent/firmware down?). No command sent.")
        node.destroy_node()
        rclpy.shutdown()
        return

    print(f"OPEN-LOOP: PWM={PWM:+.0f} on both motors, {DUR:.0f}s "
          f"(abort if |rpm|>{RPM_ABORT})")
    print(" t   | LEFT rpm   cnt     d | RIGHT rpm   cnt     d")
    print("-----+----------------------+----------------------", flush=True)

    rl, rr = [], []          # rpm samples for stats
    aborted = None
    prevL = None
    prevR = None
    sumL = 0
    sumR = 0
    t0 = time.time()
    last = -1.0
    try:
        while time.time() - t0 < DUR:
            node.send(PWM)
            rclpy.spin_once(node, timeout_sec=0.03)
            if abs(node.l[1]) > RPM_ABORT or abs(node.r[1]) > RPM_ABORT:
                aborted = f"rpm>{RPM_ABORT} (G={node.l[1]:.0f} D={node.r[1]:.0f})"
                break
            now = time.time()
            if now - last >= 0.3:
                last = now
                lz, rz = node.l[2], node.r[2]
                if prevL is not None:
                    dL, dR = int(lz - prevL), int(rz - prevR)
                    if abs(dL) < 2000 and abs(dR) < 2000:   # ignore capture artifact
                        sumL += dL
                        sumR += dR
                        rl.append(node.l[1])
                        rr.append(node.r[1])
                        print(f"{now - t0:4.1f} | {node.l[1]:+6.1f} {int(lz):+8d} {dL:+5d} | "
                              f"{node.r[1]:+6.1f} {int(rz):+8d} {dR:+5d}", flush=True)
                prevL, prevR = lz, rz
    except KeyboardInterrupt:
        aborted = "Ctrl-C"
    finally:
        node.stop()

    def stats(name, xs):
        if not xs:
            return f"{name}: (no data)"
        n = len(xs)
        mean = sum(xs) / n
        var = sum((x - mean) ** 2 for x in xs) / n
        return (f"{name}: mean={mean:+5.1f} rpm  min={min(xs):+5.1f}  "
                f"max={max(xs):+5.1f}  std-dev={var**0.5:4.1f}")

    tL = sumL
    tR = sumR
    ratio = (tR / tL) if tL else 0.0
    print("\n----- RESULT -----")
    print(f"abort = {aborted if aborted else 'no (duration elapsed)'}")
    print(stats("LEFT", rl))
    print(stats("RIGHT", rr))
    print(f"TOTAL COUNTS: LEFT={int(tL)}  RIGHT={int(tR)}  ratio R/L = {ratio:.3f}")
    print("Target ratio R/L = 1.000 (equal speeds at identical PWM).")
    print("  ratio < 1  -> right too SLOW  -> RAISE the right pot slightly")
    print("  ratio > 1  -> right too FAST  -> LOWER the right pot slightly")
    node.stop()
    node.destroy_node()
    rclpy.shutdown()


main()
