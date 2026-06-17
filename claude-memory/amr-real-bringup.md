---
name: amr-real-bringup
description: Bring-up matériel réel du robot AMR (un launch) — base prête pour SLAM/Nav2
metadata: 
  node_type: memory
  type: project
  originSessionId: 2cacdf32-9177-478e-aa34-23589a0b332a
---

Bringup réel en UN lancement : **`ros2 launch /home/botshare/openamr_real_bringup.launch.py`**
(sur le Pi, après `source /opt/ros/jazzy/setup.bash && source ~/linorobot2_ws/install/setup.bash`).

Il démarre :
- agent micro-ROS (Teensy) → `/cmd_vel`, `/odom/unfiltered`, `/imu/data` (IMU réelle, cf [[amr-firmware-debug-flashed]])
- driver RPLidar (`rplidar_composition`, Standard, 115200, frame `lidar_link`) → `/scan` ~7 Hz
- `~/odom_tf_relay.py` : republie `/odom/unfiltered` → `/odom` + TF `odom→base_link` (roues seules)
- `static_transform_publisher` `base_link→lidar_link` = **x=0.335, y=0, z=0.18, yaw=π (180°)** MESURÉ
  (lidar 33,5 cm devant l'axe, centré, monté TOURNÉ de 180° : son 0° pointe vers l'arrière, l'avant = 180°)

Résultat : `/cmd_vel /odom /imu/data /scan` + TF `odom→base_link→lidar_link`. C'est le contrat Nav2
(manque `map→odom` = SLAM/AMCL, et `/scan_filtered` = filtre de la nav).

**À affiner avant nav précise :**
- TF `base_link→lidar_link` : MESURER la position réelle du lidar (hauteur + offset) et le YAW
  (où pointe le 0° du lidar vs avant robot). FOV utile ~170° vers l'avant (corps masque l'arrière)
  → configurer le `scan_body_filter` de openamrobot_nav2.
- Géométrie roues réelle Ø0.2/entraxe0.45 (sim = Ø0.22/0.4075).
- Upgrade odométrie : remplacer le relais par un **EKF `robot_localization`** fusionnant `/odom/unfiltered`+
  `/imu/data` (l'IMU n'a PAS d'orientation valide → n'utiliser que `angular_velocity.z`) pour réduire la dérive de cap.

**GOTCHA RPLidar** : le tuer brutalement (SIGTERM) en plein scan le laisse coincé
(`Cannot start scan: 80008000`, puis `operation time out`). Seul remède : **débrancher/rebrancher l'USB**
du lidar. Ne pas le relancer en boucle (respawn) sur un device coincé.

**SLAM prêt (pas encore lancé — demande de pousser le robot)** : `slam_toolbox` installé (apt) +
`nav2-map-server` installé. Config sur le Pi : **`~/slam_params.yaml`** (copie du template online_async,
patché : base_frame=base_link, scan_topic=/scan, mode mapping, **min_laser_range=0.35** pour virer la
structure robot — tous ses retours sont <0.30 m, à ±20-50° et ±80-90°, max ~0.30 —, max_laser_range=10,
minimum_travel 0.2). Lancer : `ros2 launch slam_toolbox online_async_launch.py use_sim_time:=false
slam_params_file:=/home/botshare/slam_params.yaml`, puis teleop, puis sauver la carte.

⚠️ **Le lidar s'arrête de publier tout seul par moments** (nœud vivant mais /scan muet) → le relancer
(`pkill -f '[r]plidar_composition'`, le respawn du launch le ramène). À surveiller pendant le SLAM.

**Suite** : `openamr-platform-sw` cloné dans `~/openamr-platform-sw` (PAS encore buildé). Après SLAM :
AMCL + Nav2 (`openamrobot_nav2`, `nav2_params.yaml`, frames base_link/odom/map, scan `/scan_filtered`),
puis docking (caméra). Doc réf : `~/openamr_hardware_bringup_guide/README_OPENAMR_HARDWARE_BRINGUP.md`.
Visu/dev : voir [[amr-dev-workflow]].
