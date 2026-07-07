# Session robot — 2026-07-07 : réécriture du correcteur de docking + toutes les commandes

Grosse session de test/debug/réécriture du correcteur final de docking (`_final_visual_approach`
dans `openamr-platform-sw/ros2/src/openamrobot_docking/scripts/dock_trigger.py`), après le fix
nav/gyro/UI du 06/07. Ce doc liste **toutes les commandes utilisées** ce soir, prêtes à copier-coller.

Résumé des changements code : voir les commits sur la branche `fix/docking-near-servo-af` du repo
`openamr-platform-sw` (autofocus continu, fix bug de dérivée, compensation de profondeur, report
d'orientation par odométrie, simplification en paliers suivre/aveugle, pondération par stabilité
puis inversée far/near, gel de la normale sous `freeze_axis_distance` + reprojection odométrique,
gate AprilTag optimisé, un seul marker RViz + logs clarifiés).

---

## 1. Bring-up complet (stack entière, avec docking)

### 0. Avant d'allumer/relancer — robot IMMOBILE
Le gyro se calibre au boot du Teensy (voir §5 pour vérifier après coup).

### Kill (tout)
```bash
pkill -9 -f "micro_ros_agent|rplidar|component_container|apriltag|dock_trigger|nav2|controller_server|planner_server|bt_navigator|behavior_server|smoother_server|amcl|map_server|lifecycle_manager|ekf_node|robot_state_publisher|static_transform|web_video_server|scan_body_filter|goal_relay|ros2 launch" 2>/dev/null
sleep 3
```
⚠️ **Piège** : lancé en une seule commande `ssh hote "pkill ... ros2 launch..."`, le motif matche la
commande SSH elle-même (qui contient littéralement le texte "ros2 launch") et coupe la connexion.
Si ça arrive, le script est quand même exécuté côté Pi — vérifier avec un `ssh hote "echo alive"`.
Pour l'éviter : mettre le kill dans un script `.sh`, le copier avec `scp`, puis `ssh hote "bash script.sh"`.

### Lancement complet
```bash
ssh botshare@botshare.local
```
```bash
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 launch openamrobot_bringup bringup.launch.py map:=/home/botshare/maps/piece_actuelle.yaml use_docking:=true
```
Variante sans docking (nav seule, plus léger) : remplacer par `use_camera:=false use_docking:=false`.

### Lancement en arrière-plan avec logs complets (non-bufferisés)
Utile pour un test automatisé/enregistré — sinon les logs Python restent coincés dans le buffer
jusqu'à la fin du process (piège rencontré ce soir : logs `[DOCKING]` du docking perdus) :
```bash
PYTHONUNBUFFERED=1 nohup ros2 launch openamrobot_bringup bringup.launch.py \
  map:=/home/botshare/maps/piece_actuelle.yaml use_docking:=true \
  > /home/botshare/bringup_docking.log 2>&1 &
disown
```

---

## 2. Relancer UNIQUEMENT le docking (sans toucher caméra/nav2/lidar déjà lancés)

### Kill (docking seulement)
```bash
pkill -9 -f "dock_trigger.py|apriltag_node|apriltag_gate.py|detected_dock_pose_publisher" 2>/dev/null
sleep 2
```

### Relance (docking seulement)
```bash
source /opt/ros/jazzy/setup.bash
source ~/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 launch openamrobot_docking docking_real.launch.py
```
⚠️ Suppose que la caméra tourne déjà (lancée par le bring-up principal).

---

## 3. Calibration encodeur — PC, ⚠️ ROUES EN L'AIR
À refaire après **chaque** power-cycle du Teensy (table perdue, en RAM) :
```bash
cd ~/Documents/openamr
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
python3 scripts/align_enc_cal.py --arm 250
```
Attendre `"table placed -> /debug/enc_cal"`.

---

## 4. RViz + localisation — PC
```bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
rviz2 -d ~/Documents/openamr/scripts/openamr_nav.rviz
```
Faire un **2D Pose Estimate** à la position réelle du robot.

Ajouter le display **MarkerArray** sur le topic `/docking/debug_markers` pour voir la ligne verte
de docking en direct (montre la normale/axe réellement utilisée par le correcteur).

### Si AMCL reste bloqué à `inactive` après le Pose Estimate (log `AMCL is not yet in the active state`)
Vérifier son état :
```bash
source /opt/ros/jazzy/setup.bash; export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; export ROS_DOMAIN_ID=0
ros2 lifecycle get /amcl
ros2 lifecycle get /map_server
```
S'il est `inactive` et que `map_server` est `active`, forcer l'activation à la main :
```bash
ros2 lifecycle set /amcl activate
```
Puis refaire le 2D Pose Estimate.

---

## 5. Vérifs utiles pendant les tests

```bash
source /opt/ros/jazzy/setup.bash; export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; export ROS_DOMAIN_ID=0

# gyro (doit être ~0 au repos — sinon repower-cycler le Teensy robot immobile)
ros2 topic echo /imu/data --once --field angular_velocity.z

# ce que le contrôleur commande réellement
ros2 topic echo /cmd_vel

# latence de l'image brute (capture -> réception réseau)
ros2 topic delay /camera/image_raw

# latence + taux de détection AprilTag (léger, ~0% CPU) — activer le gate d'abord
ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: true}"
python3 /home/matthieu/Documents/openamr/scripts/apriltag_latency.py
# puis désactiver quand terminé :
ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: false}"

# charge CPU / thermique du Pi
uptime
vcgencmd measure_temp
vcgencmd get_throttled

# état LIDAR (si /scan a 0 publisher malgré le process actif -> débrancher/rebrancher le câble USB)
ros2 topic info /scan
ros2 service call /start_motor std_srvs/srv/Empty "{}"
```

---

## 6. Docking — déclenchement manuel
```bash
source /opt/ros/jazzy/setup.bash; export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; export ROS_DOMAIN_ID=0
ros2 topic pub --once /dock_trigger std_msgs/msg/Bool "{data: true}"
# undock :
ros2 topic pub --once /undock_robot std_msgs/msg/Bool "{data: true}"
```

---

## 7. UI opérateur (Docker) — PC
```bash
cd ~/Documents/openAMRobot/openamrobot-ui
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID=0 docker compose up -d
```
Rebuild si le code de l'UI a changé (pull Raj, etc.) :
```bash
docker compose down
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID=0 docker compose up -d --build
```
- Contrôle + carte : http://localhost:5050/control
- Blocs + voix (Google Chrome pour le micro) : http://localhost:5050/blocks

---

## Reste à faire (voir aussi la mémoire du projet)
- Tester en conditions réelles le correcteur réécrit (branche `fix/docking-near-servo-af`, pas encore mergée).
- Vérifier le montage caméra (biais constant suspecté — voir hypothèse yaw de montage non calibré dans `real_bringup.launch.py`).
- Pousser les PR une fois le correcteur validé.
