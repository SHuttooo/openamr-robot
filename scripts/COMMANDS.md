# Commandes robot AMR — aide-mémoire (PC + Pi)

Toutes les commandes qu'on utilise pour piloter/tester le robot réel. Voir aussi
[docs/software/navigation.md](../docs/software/navigation.md) et la mémoire `amr-pi-ros-commands`.

## Environnement (à sourcer dans CHAQUE terminal)
**PC Ubuntu** *(par défaut FastDDS/domain 42 → ne voit pas le robot, il FAUT ces exports)* :
```bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
```
**Pi** (SSH non-interactif ne source pas ROS) — préfixer pareil + les workspaces voulus :
```bash
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
# +pour Nav2 : source ~/camera_ws/install/setup.bash ; source ~/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ; export ROS_DOMAIN_ID=0
```
SSH : `ssh botshare@172.17.201.29` (clé OK, pas de mot de passe).

## Alimentation
- **Secteur sans batterie** (recommandé pour tester) : la brique AC/DC 24 V et la batterie sont en
  parallèle → le robot tourne directement sur le secteur (à la laisse). 24 V stiff = pas de variable
  « batterie faible ». Rouler lentement (pas de réserve → l'alim peut disjoncter sur les pics).
- **Batterie** : viser **≥ 25 V au repos** avant tout test nav (≤ 23,5 V = trop bas, couple mou → percute).
- ⚠️ Un reboot du Pi **vide `/tmp`** → recopier les scripts (`scp scripts/*.sh botshare@…:/tmp/`).

## Lancer la STACK Nav2 complète (sur le Pi)
```bash
scp scripts/bringall.sh botshare@172.17.201.29:/tmp/                 # depuis le PC, une fois
ssh botshare@172.17.201.29 'nohup setsid bash /tmp/bringall.sh >/dev/null 2>&1 </dev/null &'
ssh botshare@172.17.201.29 'for i in $(seq 1 24); do grep -q "### UP" /tmp/bringall.log && break; sleep 4; done; cat /tmp/bringall.log'
```
→ bring-up (agent+lidar+EKF+filtre+caméra+TF) + AMCL sur `~/maps/coin_ok.yaml` + Nav2 + goal_relay.

## RViz (sur le PC)
```bash
# config Nav2 prête (carte, costmaps, scan, chemins global+local, empreinte=robot, outils 2D Pose/Goal) :
source /opt/ros/jazzy/setup.bash && export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && export ROS_DOMAIN_ID=0 && rviz2 -d /home/matthieu/Documents/openamr/scripts/openamr_nav.rviz
# (config SLAM séparée : scripts/openamr_slam.rviz)
```
Fixed Frame=`map`. Affiché auto : Map `/map`, Costmap local+global, LaserScan `/scan_filtered` (Best
Effort), Path `/plan` (rouge) + `/local_plan` (cyan), Polygon `/local_costmap/published_footprint`
(**= le robot**, magenta). Outils : **2D Pose Estimate** (localiser, À FAIRE EN PREMIER) → **2D Goal Pose**
(but ; PAS « Nav2 Goal »). Modèle 3D optionnel = `robot_state_publisher` (risque doublon TF).

## Vérifs (bornées — NE JAMAIS faire `ros2 topic hz` en SSH, ça bloque)
```bash
ros2 node list
ros2 lifecycle get /controller_server          # active
ros2 topic echo /amcl_pose --once              # localisé ?
ros2 topic info /scan_filtered                 # publisher count == 1
# costmaps NON vides (sinon robot aveugle, cf gotcha #8) :
ros2 topic echo /global_costmap/costmap --field data --once | tr ',' '\n' | grep -vE '^0$|^-1$|^$' | wc -l
ros2 topic echo /local_costmap/costmap  --field data --once | tr ',' '\n' | grep -vE '^0$|^-1$|^$' | wc -l
ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap "{}"
```

## Réglages Nav2 à chaud (local + global)
```bash
ros2 param set /local_costmap/local_costmap inflation_layer.inflation_radius 0.20
ros2 param set /controller_server FollowPath.max_vel_x 0.16
# empreinte élargie +12cm (marge dure d'évitement) :
ros2 param set /local_costmap/local_costmap footprint "[[0.535,0.31],[0.535,-0.31],[0.435,-0.41],[-0.385,-0.41],[-0.485,-0.31],[-0.485,0.31],[-0.385,0.41],[0.435,0.41]]"
```

## Tests moteurs / encodeurs (scripts dans `scripts/`, à scp dans /tmp puis lancer détaché)
- **`agentup.sh`** — démarre l'agent seul (vérifie la Teensy, **ne bouge pas**).
- **`wtest.sh`** — roues **EN L'AIR** : openloop 300 sur les 2 roues, compte rpm G/D (faux-contact gauche ?).
- **`gtest.sh`** — **AU SOL**, espace devant : avance 0,10 m/s 4 s, mesure déplacement odom + G/D.
- Lancer : `ssh … 'nohup setsid bash /tmp/XXX.sh >/dev/null 2>&1 </dev/null &'` puis lire `/tmp/XXX.log`.

### Debug firmware direct (sans Nav2)
```bash
# openloop : x = PWM gauche, y = PWM droite (-1023..1023), publier en continu (watchdog 200ms) :
ros2 topic pub -r 10 /debug/openloop geometry_msgs/msg/Vector3 "{x: 200.0, y: 200.0, z: 0.0}"
# rpm roues (BEST_EFFORT) : x=cible, y=mesuré, z=counts :
ros2 topic echo /debug/left  --qos-reliability best_effort
ros2 topic echo /debug/right --qos-reliability best_effort
# avance closed-loop :
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.10}, angular: {z: 0.0}}"
```

## Cartes
```bash
# sauver la carte courante (sur le Pi) :
ros2 run nav2_map_server map_saver_cli -f ~/maps/NOM --ros-args -p save_map_timeout:=20.0
```
Cartes : `~/maps/coin_ok.*` (bonne, 2026-06-20), `coin2.*` (+ `.bak`).

## Pièges (résumé — détails dans navigation.md)
- **2D Pose Estimate AVANT tout** sinon costmaps vides → robot aveugle.
- Filtre scan doublon retiré du launch ; **« 2D Goal Pose »** + goal_relay (pas « Nav2 Goal »).
- `pkill` toujours en bracket trick : `pkill -f "[m]icro_ros_agent"`.
- Pas de `topic hz` en SSH. Reboot Pi = `/tmp` vidé.
