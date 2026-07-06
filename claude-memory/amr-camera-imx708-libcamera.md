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

**CORRECTIF ✅ APPLIQUÉ** : fork RPi `raspberrypi/libcamera` + `christianrauch/camera_ros` compilés dans
`~/camera_ws` (overlay). Caméra fonctionnelle, vérifiée par snapshot. Topics : `/camera/image_raw`
(+ /compressed) + `/camera/camera_info`. Lancer : sourcer `~/camera_ws/install/setup.bash` puis camera_node.

**CALIBRATION ✅ FAITE 2026-06-19** : damier 9×12 carrés (8×11 coins), 30 mm, 87 vues. Résultat 1280×720 :
fx≈1415,7 fy≈1415,1 cx≈629,3 cy≈366,4 ; distorsion plumb_bob [0,0038, 0,217, ~0, ~0, 0]. Sauvée dans
**repo scripts/camera_info.yaml + Pi ~/camera_info.yaml** ; bring-up la charge via `camera_info_url`.
⚠️ **La résolution DOIT matcher la calib** → caméra passée en **1280×720** dans le bring-up (le mode 16:9
recadre le capteur 4:3 → pas un simple ×2 du 480p). Recette de recalibration (republish compressé→raw
local + cameracalibrator) : cf docs/hardware/camera.md.
⚠️ Image **tournée ~90°** (caméra montée de côté) + peut-être pas parallèle au sol → à corriger dans le
**TF extrinsèque `camera_link`** (roll/pitch/yaw) avant le docking. Montage : x≈0.415, y=0, ~0.175 m du sol.
Voir [[amr-pi-ros-commands]].

**VOIR LA CAMÉRA SUR LE PC / WiFi (2026-06-25) — ne PAS passer par RViz/DDS.** Les images **ne traversent
pas le WiFi en DDS** : brut = 65 Mo/s (impossible) ; compressé (~50 Ko) ne passe pas non plus (publisher
`image_transport` **lazy** + QoS RELIABLE → l'appariement de l'abonné distant échoue ; en local sur le Pi
tout marche : ~24 Hz brut / ~31 Hz compressé). De plus **RViz2 n'a pas de "Transport Hint"** → son display
Image ne lit que le brut → inutilisable sur WiFi (le republish compressé→raw côté PC échoue car le compressé
ne traverse pas). **SOLUTION qui marche = `web_video_server`** (`sudo apt install ros-jazzy-web-video-server`)
lancé **sur le Pi** : lit la caméra en local (pas de DDS), sert du **MJPEG HTTP à la demande** (navigateur
fermé = 0 trafic). PC → navigateur `http://172.17.201.29:8080/stream?topic=/camera/image_raw&type=mjpeg`
(+`&quality=40` pour alléger). **Intégré dans `~/iboot.sh`** (lance web_video_server après la nav, et le tue
au kill pour éviter les doublons). Runbook : docs/procedures/real-robot-runbook.md §8bis.
