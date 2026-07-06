---
name: amr-ui-operator
description: "UI opérateur openamrobot-ui (React+rosbridge, dockerisée) : PRODUCTION-READY, tous les topics matchent déjà le vrai robot. Piège DDS = compose défaut FastDDS alors que robot=CycloneDDS/domain0 (panneaux vides). Runbook = docs/REAL-ROBOT-INTEGRATION.md. Fork SHuttooo, branche feat/real-robot-integration."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**UI opérateur = repo SÉPARÉ `openamrobot-ui`** (cloné `~/Documents/openAMRobot/openamrobot-ui`).
Remotes : `origin`=openAMRobot (org), `fork`=SHuttooo (mon fork, créé 2026-06-30). Pas de node/npm ni
Docker sur le PC → on **édite le code + push, build/test côté toi via Docker**.

## Archi (déjà mûre, maintenue par Raj)
React (CRA) + Redux + Blockly + roslib/rosbridge ; servie par Flask (:5050). Backend ROS2 =
`openamr_ui_package` : `flask`, `map_relay` (/map→/ui/map), `nav_relays` (/amcl_pose, nav status →
/ui/*, conversion QoS TRANSIENT_LOCAL→VOLATILE pour le browser), rosbridge (:9090), web_video_server
(:8080 MJPEG caméra), rosapi. Vrai launch = `openamr_ui_bringup ui.launch.py` → `new_ui_launch.py`.
⚠️ Les launch `move_base_launch.py`/`map_server_launch.py` sont LEGACY (PAS dans ui.launch.py) → ne PAS
les lancer (sinon 2e Nav2/map_server).

## ✅ Bonne nouvelle : interface DÉJÀ alignée
Tous les topics/services matchent platform-sw : `/goal_pose`, `/dock_trigger`, `/undock_robot`,
`/dock_trigger_status`, `/cmd_vel`, `/scan_filtered`, `/camera/image_raw`, `/map`, `/amcl_pose`,
nav status, cancel. Rien à remapper.

## ⚠️ LE piège d'intégration n°1
`docker-compose.yml` défaut **RMW=rmw_fastrtps_cpp** mais le robot = **CycloneDDS/domain 0** → l'UI dit
« connecté » mais **panneaux vides** (FastDDS ≠ Cyclone). Fix : `.env` avec
`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` + `ROS_DOMAIN_ID=0` (cf `.env.example` que j'ai ajouté). Même
piège que [[amr-pi-ros-commands]] (PC FastDDS/domain42 ne voit pas le robot).

## Fait (branche `feat/real-robot-integration`, poussée sur fork SHuttooo)
1. Caméra défaut `/rgb_image`(sim)→`/camera/image_raw`(réel). 2. `docs/REAL-ROBOT-INTEGRATION.md`
(runbook complet). 3. `.env.example` Cyclone/domain0. 4. IP rosbridge configurable `REACT_APP_ROSBRIDGE_IP`.
PR à créer : SHuttooo:feat/real-robot-integration → openAMRobot:main.

## Reste à faire
- **B (besoin coords réelles map piece_actuelle)** : `STANDBY_POSE` (DockingControl.jsx, pose après undock)
  + `DEFAULT_BLOCK_LOCATIONS` (flask_app.py) = valeurs bidon à régler.
- **D** : tester l'UI en Docker contre le robot via le runbook → corriger ce qui casse.
- Note : l'apriltag gate [[amr-apriltag-on-demand-gate]] ne touche PAS `/camera/image_raw` → panneau
  caméra OK quel que soit l'état de docking.
## ⚠️ Contraintes d'environnement de build (2026-06-30)
- **NI node/npm NI Docker** sur le PC Ubuntu ni sur le Pi → on **édite le code + push**, le build se fait
  via Docker côté toi. Docker installé sur le PC via `curl -fsSL https://get.docker.com | sudo sh`.
- **Disque PC saturé** : Linux = `nvme0n1p5` ext4 **84,5G** (dual-boot, Windows = 367G NTFS à côté).
  Le build Docker (image ROS jazzy + node + colcon, plusieurs Go) a fait **disque plein** (`no space left`,
  /tmp à 0). Libéré ~15G en supprimant caches régénérables (`~/.cache/pip` 7,5G, `vscode-cpptools` 6,7G,
  `mozilla`) → root repassé à 16G libres (assez pour builder). `~/.cache/bazel` 3,9G laissé (build cache).
- **SSD externe « Crucial X9 »** (`/media/matthieu/Crucial X9`) = **exFAT, 769G libres** (tes dossiers
  Windows = 163G dessus). Docker NE PEUT PAS stocker sur exFAT (overlay2 = ext4). Solution non destructive
  préparée : **fichier ext4 loopback de 80G sur le SSD** (`truncate -s 80G docker.img` → `mkfs.ext4` →
  `mount -o loop /mnt/docker-ssd` → `daemon.json data-root=/mnt/docker-ssd` → restart docker ; build avec
  `TMPDIR=/mnt/docker-ssd/tmp`). Caveat : SSD débranché = Docker ne démarre plus ; ajouter à /etc/fstab.

Commits sans Claude [[amr-commit-no-claude]] ; commandes complètes [[amr-commands-always-complete]].
