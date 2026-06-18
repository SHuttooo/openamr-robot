---
name: amr-session-suite-nav2-cyclone
description: "Suite session 2026-06-18/19 — CycloneDDS, openamr-platform-sw buildé, docking compris, contrôle OK, pots équilibrés ; reste = câble gauche"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Suite de [[amr-session-2026-06-18]] (fin 18 → 19 juin 2026).

**FAIT :**
1. **Bascule CycloneDDS sur TOUTE la stack** (le docking exige Cyclone ; FastDDS fait crasher dock_trigger
   sur les actions Nav2). Pi `~/.bashrc` exporte `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` ; bring-up relancé
   en Cyclone ; Ubuntu = Cyclone domain 0 même sous-réseau. ⚠️ **Tout terminal Ubuntu doit exporter Cyclone
   + domain 0** sinon ne voit rien. Docs MAJ (Fast DDS → Cyclone partout).
2. **Stack Nav2/AprilTag installé sur le Pi** (ros-jazzy-navigation2, nav2-bringup, apriltag-ros, image-proc,
   rmw-cyclonedds-cpp, laser-filters) + **openamr-platform-sw BUILDÉ** : `cd ~/openamr-platform-sw/ros2 &&
   colcon build --packages-select openamrobot_description openamrobot_nav2 openamrobot_gazebo
   openamrobot_docking` (gazebo requis pour l'ordre de build).
3. **Docking compris** (sim validée par Matthieu lui-même) : apriltag_ros (bundle 3 tags 36h11 id0/1/2 sur
   /rgb_image+camera_info) → /detected_dock_pose → dock_trigger.py → NavigateToPose staging puis approche.
   ⚠️ **Gotcha** : lancer la sim sur le **même domain** que le vrai robot → collision TF (TF_OLD_DATA) →
   NavigateToPose abort. Sim sur **domain séparé** (ex. 5). Cf [[amr-docking-nav2-real]].
4. **Contrôle robot validé** : scripts d'avance boucle fermée sur /odom EKF (`/tmp/forward50.py`) → avance
   X cm tout droit, arrêt à ±0,5 cm. (Avancé 50/57/200 cm, reculé 200 cm — OK quand la gauche marche.)
5. **Fix SLAM CycloneDDS** : sous Cyclone le scan était ~0,14 s en avance sur le TF EKF → slam_toolbox
   droppait ("queue full", pas de Registering sensor). Fix = **`transform_time_offset: 0.2`** dans ekf.yaml
   (committé). Depuis, SLAM enregistre + publie /map + map→odom.
6. **Équilibrage roues** (pot VAR droit) cf [[amr-driver-balance-dip]].
7. **Permissions Claude** : `.claude/settings.json` (projet, gitignoré) auto-allow Bash/Read/Edit/Write +
   ask pour sudo/rm/git push/teensy_loader_cli/reboot. (Peut nécessiter restart de Claude Code pour
   s'activer car .claude/ créé en cours de session.)

**Vérif params (spot-check 2026-06-19)** : la vraie config = `config/lino_base_config.h` (celle que
`-e teensy40` compile ; `dev_config.h` est INUTILISÉE). Valeurs réelles confirmées, **conformes aux docs** :
USE_MPU9250_IMU ; K_P 0.6/K_I 0.35/K_D 0.15 ; MOTOR_MAX_RPM 80 ; MAX_RPM_RATIO 0.85 ;
MOTOR_OPERATING_VOLTAGE 24 ; MOTOR_POWER_MAX_VOLTAGE 24 ; COUNTS_PER_REV 1024 ; WHEEL_DIAMETER 0.2 ;
LR_WHEELS_DISTANCE 0.45 ; **PWM_BITS 10 → PWM_MAX 1023** ; PWM_FREQUENCY 3000 (3 kHz) ; BAUDRATE 115200 ;
MOTOR1_ENCODER_INV true / MOTOR2_ENCODER_INV false ; MOTOR1_INV false / MOTOR2_INV true ;
encodeurs M1 A14/B15, M2 A11/B12 ; driver actif = **USE_GENERIC_2_IN_MOTOR_DRIVER** → M1 PWM1/INA20/INB21,
M2 PWM5/INA6/INB8. (Donc pas d'erreur de PWM_MAX/param trouvée pour l'instant.)

**RESTE (demain) — par ordre :**
A. **Réparer le câble GAUCHE** (faux-contact = bloqueur n°1, cf [[amr-left-wheel-faux-contact]]).
B. (Optionnel) tester **DIP SW1** boucle ouverte driver + finir l'équilibrage pots ([[amr-driver-balance-dip]]).
C. **Carte SLAM réelle** propre (endroit avec murs, rouler lent) → sauver.
D. **Nav2 réel** : robot_state_publisher+URDF + Nav2/AMCL sur la carte → valider une **NavigateToPose**.
E. **Caméra** : calibration (damier) + dock AprilTag physique imprimé → **docking réel**.
F. **À VÉRIFIER/ÉCRIRE demain (demande Matthieu)** : re-vérifier TOUS les paramètres firmware (au cas où
   un PWM_MAX / param serait faux) ET **écrire le CÂBLAGE COMPLET** (pinout Teensy↔drivers↔moteurs↔
   encodeurs↔IMU↔lidar↔caméra↔alim) dans docs/hardware/wiring-pinout.md, vérifié contre lino_base_config.h.

Tout est committé/poussé sur github SHuttooo/openamr-robot (master).
