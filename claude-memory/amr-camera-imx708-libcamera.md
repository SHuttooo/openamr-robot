---
name: amr-camera-imx708-libcamera
description: "Caméra AMR (IMX708 NoIR, Pi5) — HW/noyau OK, blocage libcamera upstream → besoin du fork Raspberry Pi"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Test caméra du robot AMR le 2026-06-18. La caméra est **cam0 sur le Pi 5** : Pi Camera Module 3
**NoIR** (capteur **`imx708_noir`**, + autofocus `dw9807`), en **CSI** (pas USB).

**État HW/noyau : PARFAIT.** Le graphe média est complet et relié :
`imx708_noir → csi2 → pisp-fe → rp1-cfe` (liens ENABLED/IMMUTABLE, vu via `media-ctl -d /dev/media0 -p`).
`camera_auto_detect=1` dans /boot/firmware/config.txt. `botshare` est dans le groupe `video`.

**BLOCAGE = libcamera (logiciel).** `camera_node` (paquet apt `ros-jazzy-camera-ros` 0.6.0, lié à
`ros-jazzy-libcamera` **0.7.1**) échoue : « no cameras available », et en debug le pipeline `rpi/pisp`
dit **« Unable to acquire a CFE instance »**. Noyau = `6.8.0-1057-raspi`.

**Cause (recherche web, sources concordantes)** : la **libcamera upstream** (= celle d'apt) ne supporte
PAS le Camera Module 3 / IMX708 sur Pi 5 ; **seul le fork Raspberry Pi de libcamera** le gère.
Problème connu Pi5 + Ubuntu 24.04 + ROS 2 Jazzy + Cam Module 3.

**CORRECTIF identifié (pas encore appliqué)** : compiler le **fork RPi `raspberrypi/libcamera` +
`christianrauch/camera_ros`** depuis les sources dans un workspace colcon dédié (overlay, sans virer les
paquets apt). Guide exact : github.com/erykpawelek/libcamera_ros2_setup. Deps : g++/cmake/meson/ninja/
pybind11-dev/python3-colcon-meson + libs. ~20-40 min de build sur le Pi. Topics attendus :
`/camera/image_raw` (+ /compressed) + `/camera/camera_info`. Visu : `rqt_image_view` sur Ubuntu.

Montage caméra (doc) : x≈0.415 (8 cm devant le lidar), y=0, ~0.175 m du sol. À calibrer (damier) avant
tout AprilTag/docking. Voir [[amr-real-bringup]], [[pi-ssh-access]].
