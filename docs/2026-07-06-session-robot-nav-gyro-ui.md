# Session robot — 2026-07-06 : nav débloquée (deadlock 0.025), gyro, cooler + UI qui MARCHE

Grosse session de debug sur le robot réel. Trois problèmes résolus (nav qui ne bougeait plus,
dérive de pose dans RViz, throttling thermique) **et l'UI opérateur fonctionne** (waypoint + blocs). 🎉

Robot : Pi 5 (`botshare.local`), Teensy/micro-ROS, RPLIDAR A1, ROS 2 Jazzy, Nav2, CycloneDDS domaine 0.

---

## 🎉 Ce qui MARCHE maintenant
- **L'UI opérateur fonctionne** (React + rosbridge, dockerisée) : les **waypoints** et les **blocs**
  (Blockly) marchent. On pilote/programme le robot depuis le navigateur. ✅
- **La navigation bouge à nouveau** (elle restait figée avant — voir le deadlock ci-dessous).
- **Plus de dérive de pose** dans RViz (c'était le biais gyro de l'IMU).
- **Plus de throttling thermique** : cooler/ventilo ajouté → 83 °C → **47,7 °C**, `throttled=0x0`.

---

## 🔧 Problème n°1 (LE gros) : la nav ne bougeait plus — deadlock à 0,025 rad/s

**Symptôme** : on met un goal, le robot ne bouge pas. `cmd_vel` envoie en boucle
`angular.z = 0.025`, `linear.x = 0`. On dirait qu'il « calcule 50 ans ».

**D'où sort 0,025** :
```
acc_lim_theta (accélération angulaire max) = 0.5 rad/s²
période contrôleur = 0.05 s (20 Hz)
→ 0.5 × 0.05 = 0.025 rad/s
```
C'est la vitesse **max que DWB peut commander au 1er cycle depuis l'arrêt** (limite d'accélération).

**Le deadlock** :
1. Robot à l'arrêt → vitesse mesurée = 0 → DWB ne peut sampler que `0 ± acc×dt` = **±0,025 rad/s**.
2. Il commande 0,025 → **sous le plancher de stiction du moteur (~0,15 rad/s)** → roues ne tournent pas
   (cible rpm des 2 roues = 0, vérifié sur `/debug/left|right`).
3. Vitesse mesurée reste 0 → cycle suivant re-limité à 0,025 → **boucle infinie**.

**Pourquoi ça marchait vendredi (lent) et plus maintenant** : vendredi le **gyro était biaisé
(-0,31 rad/s)** → la vitesse angulaire « mesurée » n'était pas 0, donc DWB samplait autour de -0,31
et pouvait commander de vraies rotations. **En corrigeant le gyro aujourd'hui, on a supprimé ce
coup de pouce accidentel → le deadlock d'accélération est apparu.**

**Le fix** : monter les accélérations pour que le **1er cycle dépasse le plancher** :
```
acc_lim_theta : 0.5 → 3.0   (1er cycle = 3.0×0.05 = 0.15 rad/s ✅)
acc_lim_x     : 0.5 → 1.0   (1er cycle = 0.05 m/s ✅)
max_angular_accel : 0.5 → 3.0
```
Puis équilibrage (l'accel à 4.0 rendait le robot trop nerveux au freinage) :
```
decel_lim_theta : -2.0 → -3.0   (freinage renforcé)
max_vel_x   : 0.20  (vitesse avance calme, gardée)
max_vel_theta : 0.5  (rotation calme, gardée)
```
**Réglages persistants** : édités dans `nav2_params.yaml` (src + build) SUR LE PI → survivent au reboot.
⚠️ **Ces params DWB ne se règlent PAS à chaud** (`ros2 param set` ne suffit pas) → il faut **relancer**
le bring-up à chaque changement.

---

## 🔧 Problème n°2 : la pose dérivait dans RViz alors que le robot est immobile

**Cause** : le **gyro de l'IMU** avait un biais constant de **-0,31 rad/s** (≈ -17°/s) au repos.
L'EKF fusionne ce yaw-rate → il croit que le robot tourne → la pose dérive dans RViz.

**Le fix** : **power-cycler le Teensy (débrancher/rebrancher l'USB, robot IMMOBILE)**. Le firmware
calibre le gyro au boot **en supposant le robot immobile**. Après : gyro à **~0** ✅.

**Leçon** : toujours allumer/power-cycler le Teensy **robot parfaitement immobile**. Et après un
power-cycle Teensy → **refaire la calibration encodeur** (table perdue).

---

## 🔧 Problème n°3 : « No map received » / RViz qui jette tout
Log RViz : `Message Filter dropping message: frame 'odom' ... queue is full`.
= il manque la transformée **`map→odom`** = **AMCL pas encore localisé**.
**Fix** = faire le **2D Pose Estimate** dans RViz (donne la pose initiale → AMCL publie `map→odom`).

---

## 🌡️ Cooler / thermique
Ventilo ajouté aujourd'hui. Avant : 83 °C, throttling actif (`0x80008`), CPU bridé.
Maintenant : **47,7 °C, `throttled=0x0`, load ~3/4** → CPU sain, plus de bridage.

---

## 📋 LES COMMANDES (recette complète, dans l'ordre)

### 0. Rallumage — robot IMMOBILE pendant le boot du Pi (calibration gyro auto)

### 1. Bring-up — sur le Pi (SSH)
```bash
ssh botshare@botshare.local
```
```bash
pkill -9 -f "micro_ros_agent|rplidar|component_container|apriltag|dock_trigger|nav2|controller_server|planner_server|bt_navigator|behavior_server|smoother_server|amcl|map_server|lifecycle_manager|ekf_node|robot_state_publisher|static_transform|web_video_server|scan_body_filter|goal_relay|ros2 launch" 2>/dev/null
sleep 3
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
# nav seule (léger) :
ros2 launch openamrobot_bringup bringup.launch.py map:=/home/botshare/maps/piece_actuelle.yaml use_camera:=false use_docking:=false
# docking (caméra ON) :
# ros2 launch openamrobot_bringup bringup.launch.py map:=/home/botshare/maps/piece_actuelle.yaml use_docking:=true
```
⚠️ Toujours lancer depuis **`openamr-platform-sw`** (config rapide), PAS `openamr-integration` (config lente).

### 2. Calibration encodeur — 2ᵉ terminal, PC (⚠️ ROUES EN L'AIR), après chaque power-cycle Teensy
```bash
cd ~/Documents/openamr
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
python3 scripts/align_enc_cal.py --arm 250     # -> "table placed -> /debug/enc_cal"
```
Si `REFUSED` (WiFi) → sur le Pi : `python3 /tmp/align_enc_cal.py --arm 250` (recopier le script avant).

### 3. RViz + localisation — PC
```bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
rviz2 -d ~/Documents/openamr/scripts/openamr_nav.rviz
```
→ **2D Pose Estimate** à l'endroit réel du robot → envoyer un **2D Goal Pose** dégagé.

### 4. UI opérateur (Docker) — PC — ✅ MARCHE (waypoint + blocs)
```bash
cd ~/Documents/openAMRobot/openamrobot-ui
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID=0 docker compose up -d
```
- Contrôle + carte : **http://localhost:5050/control**
- Blocs + voix (dans **Google Chrome** pour le micro) : **http://localhost:5050/blocks**
- ⚠️ **Ne PAS "Start Camera"** depuis l'UI (sature le WiFi → coupe la nav).

### 5. Docking
```bash
source /opt/ros/jazzy/setup.bash; export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; export ROS_DOMAIN_ID=0
ros2 topic pub --once /dock_trigger std_msgs/msg/Bool "{data: true}"
```
Bundle 3 tags 36h11 (id2 gauche / id1 centre / id0 droite), carré noir 0,131 m, les 3 vus ensemble.

### Vérifs utiles
```bash
# gyro (doit être ~0 au repos)
ros2 topic echo /imu/data --once   # angular_velocity.z ≈ 0
# ce que le contrôleur commande
ros2 topic echo /cmd_vel
# config planner active
ros2 param get /planner_server GridBased.downsample_costmap
```

### Lancer en arrière-plan avec logs complets (session d'audit/enregistrement)
Le bring-up ci-dessus (étape 1) tourne en foreground dans le terminal SSH — c'est le cas normal,
les logs Python sortent sur un vrai TTY donc s'affichent en direct. Si on a besoin de le lancer
**détaché** (`nohup ... > fichier.log 2>&1 &`, ex. pour un test automatisé/enregistré), Python
bascule en **full buffering** dès que stdout n'est plus un TTY : les logs (ex. `dock_trigger.py`
en plein milieu du docking) restent coincés dans le buffer et n'apparaissent qu'à la fin du
process — piège rencontré le 07/07 (logs `[P5] depth=...` du docking perdus). **Fix** : préfixer
par `PYTHONUNBUFFERED=1` :
```bash
PYTHONUNBUFFERED=1 nohup ros2 launch openamrobot_bringup bringup.launch.py \
  map:=/home/botshare/maps/piece_actuelle.yaml use_docking:=true \
  > /home/botshare/bringup_docking.log 2>&1 &
disown
```

---

## Reste à faire
- **Committer proprement** les réglages `nav2_params.yaml` (accel fix + decel) dans le repo
  (ils sont pour l'instant seulement édités sur le disque du Pi — src + build).
- Tester le **docking** de bout en bout (préparé, pas encore relancé après le dernier reboot).
- Finaliser la démo UI (voix → blocs → robot) pour Alex.
