#!/usr/bin/env python3
"""Filtre lidar OpenAMR : /scan -> /scan_filtered.

Le lidar est monte TOURNE de 180deg : en repere lidar,
  0deg   = ARRIERE du robot
  +-180  = AVANT du robot
  -90    = gauche, +90 = droite

Deux types de secteurs (mesures le 2026-06-18 via profil par angle) :

1) FULL_MASK_SECTORS : la coque arriere bouche TOUT -> rien de reel derriere.
   On masque a TOUTES les distances (sinon on garde la coque, ex. le retour
   central a 0.72 m qui EST la coque, pas un mur).
     arriere : -45 .. +45  (centre 0.72 m, coins 0.24-0.30 m)

2) CLOSE_MASK_SECTORS : poteaux fins lateraux (0.17-0.18 m) MAIS de vrais murs
   sont visibles plus loin dans la meme direction -> on n'enleve que le proche
   (< CLOSE_MAX), on garde les murs.
     cote gauche : -96 .. -73
     cote droit  : +73 .. +96

Editer ces listes en regardant RViz pour affiner.
"""
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from rclpy.qos import qos_profile_sensor_data

FULL_MASK_SECTORS_DEG = [(-45.0, 49.0)]            # coque arriere : tout enleve (droite va a +49)
CLOSE_MASK_SECTORS_DEG = [(-96.0, -73.0), (73.0, 96.0)]  # poteaux : seulement le proche
CLOSE_MAX = 0.40   # dans les secteurs "close", on enleve seulement < 0.40 m (= poteau)


class ScanBodyFilter(Node):
    def __init__(self):
        super().__init__("scan_body_filter")
        self.full = [(math.radians(a), math.radians(b)) for a, b in FULL_MASK_SECTORS_DEG]
        self.close = [(math.radians(a), math.radians(b)) for a, b in CLOSE_MASK_SECTORS_DEG]
        self.pub = self.create_publisher(LaserScan, "/scan_filtered", qos_profile_sensor_data)
        self.sub = self.create_subscription(LaserScan, "/scan", self.cb, qos_profile_sensor_data)
        self.get_logger().info(
            f"scan_body_filter actif | arriere(full)={FULL_MASK_SECTORS_DEG} | "
            f"cotes(<{CLOSE_MAX}m)={CLOSE_MASK_SECTORS_DEG} -> /scan_filtered")

    def in_any(self, sectors, ang):
        for lo, hi in sectors:
            if lo <= ang <= hi:
                return True
        return False

    def cb(self, m):
        out = LaserScan()
        out.header = m.header
        out.angle_min = m.angle_min
        out.angle_max = m.angle_max
        out.angle_increment = m.angle_increment
        out.time_increment = m.time_increment
        out.scan_time = m.scan_time
        out.range_min = m.range_min
        out.range_max = m.range_max
        inf = float("inf")
        r = list(m.ranges)
        for i in range(len(r)):
            v = r[i]
            if not math.isfinite(v):
                continue
            ang = m.angle_min + i * m.angle_increment
            if self.in_any(self.full, ang):
                r[i] = inf                       # coque arriere : tout enleve
            elif v < CLOSE_MAX and self.in_any(self.close, ang):
                r[i] = inf                       # poteau lateral proche
        out.ranges = r
        out.intensities = m.intensities
        self.pub.publish(out)


def main():
    rclpy.init()
    rclpy.spin(ScanBodyFilter())


if __name__ == "__main__":
    main()
