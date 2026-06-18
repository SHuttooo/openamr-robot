---
name: amr-docking-nav2-real
description: Portage docking/Nav2 vers le robot RÉEL — openamr-platform-sw buildé sur le Pi + plan + gotchas
metadata: 
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Objectif : faire tourner le **docking `openamrobot_docking`** sur le VRAI robot (la **sim** marche déjà,
faite par Matthieu lui-même). Démarré 2026-06-18.

**FAIT (2026-06-18) :**
- Stack installé sur le Pi : `ros-jazzy-navigation2`, `nav2-bringup`, `apriltag-ros`, `image-proc`,
  `rmw-cyclonedds-cpp`, `laser-filters`, `joint-state-publisher` (avant : tout absent sauf robot_state_publisher).
- `openamr-platform-sw` **buildé sur le Pi** : `cd ~/openamr-platform-sw/ros2 && colcon build
  --symlink-install --packages-select openamrobot_description openamrobot_nav2 openamrobot_gazebo
  openamrobot_docking`. ⚠️ Il FAUT inclure `openamrobot_gazebo` (dépendance d'ordre de build du docking)
  même si ros_gz n'est pas sur le Pi headless (gazebo build = juste install de fichiers).

**Comment marche le docking (sim)** : `apriltag_ros` détecte un bundle 3 tags 36h11 (IDs 0/1/2) sur
`/rgb_image`+`camera_info` → TF par tag ; `detected_dock_pose_publisher` → `/detected_dock_pose` (tag
central) ; `dock_trigger.py` attend `/dock_trigger` → NavigateToPose vers staging puis approche.

**MANQUE pour le réel (chantiers) :**
1. **Calibration caméra** (damier) + `image_proc` (rectification) — AprilTag en a besoin.
2. **Dock AprilTag physique** : imprimer 3 tags 36h11 (IDs 0/1/2), mesurer taille, config.
3. **Nav2+AMCL sur une vraie carte SLAM** (le socle ; valider d'abord une NavigateToPose).
4. **CycloneDDS sur TOUTE la stack** — `dock_trigger.py` crashe en Fast DDS sur les actions Nav2.
   Bascule disruptive (agent micro-ROS, lidar, filtre, EKF, caméra + Ubuntu).
5. **robot_state_publisher + URDF** (openamrobot_description, Ø0.2/0.45) pour le footprint Nav2.
6. **Remaps** : notre caméra = `/camera/image_raw` (docking attend `/rgb_image`) ; notre `/scan_filtered`
   (scan_body_filter.py) remplace la chaîne laser_filters du package.

**GOTCHA ISOLATION (vécu)** : lancer la **sim** docking sur le **même `ROS_DOMAIN_ID=0`** que le vrai robot
→ ils se parasitent (TF base_link wall-time du robot vs sim-time → flood `TF_OLD_DATA` → NavigateToPose
abort). Lancer la sim sur un **domaine séparé** (ex. 5). Sur Ubuntu tout le stack sim était déjà installé.

Doc package excellente : `~/openamr-platform-sw/ros2/src/openamrobot_docking/docs/`. Voir aussi
docs/software/navigation.md (repo). Lié : [[amr-camera-imx708-libcamera]] (calib), [[amr-session-2026-06-18]].
