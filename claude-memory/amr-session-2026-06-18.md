---
name: amr-session-2026-06-18
description: "Récap session 2026-06-18 — EKF IMU, filtre scan, SLAM+carte, caméra IMX708 réparée, roue gauche HS"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Grosse session le 2026-06-18 (depuis Ubuntu desktop, visu RViz/rqt à distance). Réalisé :

1. **Visu distante OK** : Ubuntu voit le Pi en **ROS_DOMAIN_ID=0 + Fast DDS + même sous-réseau /16**
   (multicast). RViz config `scripts/openamr_slam.rviz`. Cf [[amr-dev-workflow]] et docs/software/visualization.md.
2. **Filtre lidar** `/scan` → `/scan_filtered` (`~/scan_body_filter.py`) : masque la coque. Mesuré :
   ARRIÈRE (lidar −45..+49°) = coque, masqué à TOUTES distances ; CÔTÉS (±73..±96°) = poteaux, masqués
   seulement < 0,40 m (murs gardés au-delà). Repère lidar : 0°=arrière (monté tourné 180°).
3. **EKF `robot_localization`** (`~/ekf.yaml`) remplace `odom_tf_relay` : fusionne roues (vx,vyaw) +
   **gyro Z IMU uniquement** → `/odom` + TF odom→base_link. Gyro Z sain (0 au repos = deadband, suit en
   rotation). Cf [[amr-real-bringup]].
4. **SLAM** `slam_toolbox` online_async sur `/scan_filtered` → 1ère carte **`~/maps/coin1.{pgm,yaml}`** +
   sérialisée `coin1.{posegraph,data}`. Lidar basse réso (~270 pts) → carte rugueuse, **rouler LENTEMENT**
   (vite/pivots = dérive). Recharger : service `deserialize_map`.
5. **Caméra IMX708 NoIR RÉPARÉE** : libcamera apt ne gère pas la Cam Module 3 → compilé le **fork RPi
   libcamera + camera_ros** dans `~/camera_ws` (overlay). Topics `/camera/image_raw(+/compressed)`.
   ⚠️ **WiFi** : ne jamais tirer l'image brute à distance (lag 3 s) → **compressé** uniquement. Snapshot
   côté Pi : `python3 ~/cam_snapshot.py`. Tout dans `~/camera_ws` (source avant le bring-up). Cf
   [[amr-camera-imx708-libcamera]].
6. **Bring-up unifié** (`openamr_real_bringup.launch.py`) inclut désormais : agent, lidar, filtre, EKF,
   caméra (640×480 ~10fps), TF statiques (lidar/imu/footprint/camera).
7. **Roue GAUCHE en panne matérielle** (test step-response : PWM saturé, rpm 0) → cf
   [[amr-pid-tracking-observation]]. Le PID n'est pas en cause ; à réparer (faux contact probable).
8. **Doc** entièrement mise à jour (docs/ : camera, imu, bringup, ros-architecture, navigation,
   visualization (nouveau), 01-communication, 00-overview, README, running-the-robot, control-loop-pid).

Câblage : **marron=+ / bleu=−** sur ce robot ([[amr-wiring-dc-colors]]).
Gotcha SSH : `pkill -f "[m]otif"` (crochets) sinon auto-match → exit 255.
