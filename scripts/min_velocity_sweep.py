#!/usr/bin/env python3
"""Balayage de vitesse minimale — trouve la vitesse la plus basse à laquelle le
robot bouge de façon FIABLE sous charge (au sol).

Commande /cmd_vel en boucle fermée (PID + dither, exactement comme le docking) et
mesure la vitesse RÉELLE sur /odom/unfiltered (odométrie roues, firmware). Pour
chaque consigne : ramp, puis 3 s de mesure -> moyenne / min / écart-type / ratio.

Usage:  python3 min_velocity_sweep.py [linear|angular] [v1,v2,...]
  défaut linear  : 0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.10   (m/s)
  défaut angular : 0.08,0.10,0.12,0.15,0.20,0.25,0.30        (rad/s)

⚠️ ROBOT AU SOL, ESPACE DÉGAGÉ. angular = tourne sur place (peu de place) ;
   linear = AVANCE (prévoir ~1,5 m devant). Main sur la coupure.
   Tuer dock_trigger avant : pkill -f "[d]ock_trigger.py" (sinon il se bat sur /cmd_vel).
"""
import sys, time, statistics
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data

MODE = sys.argv[1] if len(sys.argv) > 1 else 'angular'
if len(sys.argv) > 2:
    SPEEDS = [float(x) for x in sys.argv[2].split(',')]
elif MODE == 'linear':
    SPEEDS = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10]
else:
    SPEEDS = [0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30]
SETTLE, DUR, PERIOD = 1.2, 3.0, 0.03

rclpy.init()
n = Node('min_velocity_sweep')
pub = n.create_publisher(Twist, '/cmd_vel', 10)
cur = {'v': 0.0}

def cb(m):
    tw = m.twist.twist
    cur['v'] = tw.linear.x if MODE == 'linear' else tw.angular.z

n.create_subscription(Odometry, '/odom/unfiltered', cb, qos_profile_sensor_data)

def send(v):
    t = Twist()
    if MODE == 'linear':
        t.linear.x = float(v)
    else:
        t.angular.z = float(v)
    pub.publish(t)

unit = 'm/s' if MODE == 'linear' else 'rad/s'
print(f"=== BALAYAGE {MODE.upper()} ({unit}) — robot AU SOL, sous charge ===")
print(f"{'consigne':>9} | {'reel_moy':>9} | {'reel_min':>9} | {'std':>6} | {'ratio':>5} | verdict")
print("-" * 72)
try:
    for v in SPEEDS:
        t0 = time.time()
        while time.time() - t0 < SETTLE:
            send(v); rclpy.spin_once(n, timeout_sec=PERIOD); time.sleep(PERIOD)
        s = []
        t0 = time.time()
        while time.time() - t0 < DUR:
            send(v); rclpy.spin_once(n, timeout_sec=PERIOD); s.append(cur['v']); time.sleep(PERIOD)
        moy = statistics.mean(s); mn = min(s); sd = statistics.pstdev(s)
        ratio = moy / v if v else 0.0
        if ratio > 0.75 and mn > 0.3 * v:
            verdict = "OK fiable"
        elif ratio > 0.35:
            verdict = "partiel / broute"
        else:
            verdict = "CALE (stick-slip)"
        print(f"{v:>9.3f} | {moy:>9.3f} | {mn:>9.3f} | {sd:>6.3f} | {ratio:>5.2f} | {verdict}")
finally:
    for _ in range(15):
        send(0.0); time.sleep(PERIOD)
    print("=== STOP === robot arrêté")
    n.destroy_node(); rclpy.shutdown()
