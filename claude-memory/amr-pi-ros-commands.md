---
name: amr-pi-ros-commands
description: "RECETTE qui MARCHE pour piloter le robot par SSH (agent micro-ROS, env Cyclone, test moteurs/encodeurs) — à relire avant toute commande robot"
metadata:
  node_type: memory
  type: reference
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**Workflow vérifié (2026-06-19) pour interagir avec le robot AMR depuis le PC Ubuntu.** À relire après
chaque compact — c'est la méthode qui marche, ne pas réinventer.

## Accès & environnement
- SSH : **`ssh botshare@botshare.local`** (**clé OK, pas de mot de passe** ; hostname `BOTSHARE`).
  ⚠️ **IP en DHCP → elle CHANGE** (2026-07-06 : nouveau HW Pi + ancien SSD → `172.17.201.29` MORTE
  → `172.17.17.64`). **Utiliser `botshare.local` (mDNS)**, pas l'IP en dur. Retrouver l'IP :
  `getent hosts botshare.local`. Détails : [[pi-ssh-access]].
- SSH non-interactif ne source PAS ROS → **toujours préfixer** :
  ```
  source /opt/ros/jazzy/setup.bash
  source ~/linorobot2_ws/install/setup.bash
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  ```
  (ROS_DOMAIN_ID non défini = 0 par défaut, c'est le bon).
- Teensy : `/dev/serial/by-id/usb-Teensyduino_USB_Serial_16778200-if00`, agent **115200**.
  Agent = `ros2 run micro_ros_agent micro_ros_agent serial -b 115200 -D <by-id>`. CP2102 = le RPLidar.
- ⚠️ Le PC Ubuntu par défaut est en **FastDDS / domain 42** → il ne voit PAS le robot. Pour le voir :
  `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; export ROS_DOMAIN_ID=0`. **Plus simple : bosser
  directement sur le Pi** par SSH.

## ⚠️ LE piège (et la recette qui marche)
Lancer l'agent en arrière-plan dans un appel SSH **avale toute la sortie** et/ou l'agent **meurt** à la
fermeture du SSH (`nohup &`, `setsid &` interactifs échouent → exit 255, "no output"). **NE PAS** essayer
de garder un agent vivant entre appels SSH.

**Recette qui marche** = un **script auto-suffisant sur le Pi** qui démarre l'agent, fait le boulot, tue
l'agent, et logge dans un fichier ; lancé **détaché** ; puis on lit le log dans un appel séparé :
1. Écrire `/tmp/xxx.sh` (heredoc via SSH) ; il commence par `exec > /tmp/xxx.log 2>&1`, puis
   `pkill -f "[m]icro_ros_agent"; sleep 1`, démarre l'agent `... > /tmp/agent.log 2>&1 &  AG=$!`,
   `sleep 8`, fait les tests, `kill $AG`, `echo "### DONE"`.
2. Lancer détaché : `nohup setsid bash /tmp/xxx.sh >/dev/null 2>&1 </dev/null & echo launched`.
3. Lire : appel SSH séparé qui `for i in $(seq 1 14); do grep -q "### DONE" /tmp/xxx.log && break; sleep 3; done; cat /tmp/xxx.log`.
- Filtrer le bruit : `grep -vE "WARN|rmw_cyclonedds"` (les `Failed to parse type hash ... USER_DATA (null)`
  sont **inoffensifs**, micro-ROS ne renseigne pas les type-hash).
- `pkill` : toujours le **bracket trick** `pkill -f "[m]icro_ros_agent"` (sinon self-match, exit 255).

## Topics de debug (interface réelle, vérifiée)
- **`/debug/openloop`** (`geometry_msgs/Vector3`, RELIABLE, le firmware écoute) : **x = PWM gauche,
  y = PWM droite** (−1023..1023), PID court-circuité. Publier en continu pour battre le watchdog 200 ms :
  `ros2 topic pub -r 10 /debug/openloop geometry_msgs/msg/Vector3 "{x: 200.0, y: 200.0, z: 0.0}"`.
- **`/debug/left`** et **`/debug/right`** (`Vector3`, **BEST_EFFORT** → echo avec
  `--qos-reliability best_effort`) : **x = rpm cible, y = rpm mesuré, z = counts encodeur cumulés**.
- Aussi : `/debug/pwm`, `/cmd_vel`, `/imu/data`, `/odom/unfiltered`.

## Alim : SECTEUR sans batterie (recommandé pour tester, 2026-06-20)
Batterie ET AC/DC 24 V sont en parallèle sur le même bus → **le robot tourne directement sur la brique
secteur 24 V, sans batterie** (juste « à la laisse », câble limité). **C'est la meilleure config pour
debugger** : 24 V stiff → enlève la variable « batterie faible » ([[amr-battery-voltage-check]]). Sur
secteur, la roue gauche tient (test ci-dessous OK). Précautions : rouler lentement (l'alim n'a pas de
réserve → pics d'accel/régen peuvent la faire disjoncter), gros condo 24 V optionnel, ne pas rouler sur le
câble, sécurité 230 V (différentiel 30 mA). NB : un reboot du Pi **vide `/tmp`** → les scripts `/tmp/*.sh`
sont à recréer.

## STACK COMPLÈTE Nav2 — `/tmp/bringall.sh` (lancer détaché, voir recette du piège SSH)
Tue tout, puis lance dans l'ordre : bring-up (`~/openamr_real_bringup.launch.py` = agent+lidar+EKF+filtre+
caméra+TF) → `localization_launch.py map:=~/maps/coin_ok.yaml` → `navigation_launch.py` → `goal_relay.py`.
Source les 4 workspaces (jazzy + linorobot2_ws + camera_ws + openamr-platform-sw/ros2/install) + Cyclone +
domain 0. Lancer : `nohup setsid bash /tmp/bringall.sh >/dev/null 2>&1 </dev/null &` ; attendre `### UP`.
⚠️ ORDRE LIFECYCLE : après le lancement, faire le **2D Pose Estimate** dans RViz pour donner `map→odom`,
sinon costmaps vides (cf [[amr-nav2-bringup]] piège #8). Carte = `~/maps/coin_ok.yaml`.

## TESTS MOTEURS/ENCODEURS (scripts à recréer si /tmp vidé)
- **Agent seul** (vérifie Teensy, ne bouge pas) `/tmp/agentup.sh` : pkill agent → `ros2 run micro_ros_agent
  micro_ros_agent serial -b 115200 -D <by-id>` → liste topics → `sleep 3600`. Topics attendus : /debug/*,
  /odom/unfiltered, /imu/data, /cmd_vel.
- **Test roues à vide** `/tmp/wtest.sh` (roues EN L'AIR) : echo /debug/left|right (best_effort, field y) →
  `ros2 topic pub -t 60 -r 10 /debug/openloop ... "{x:300,y:300,z:0}"` → compte les rpm non-nuls G vs D.
  Sain = les deux ~continus. Gauche=0/intermittent = faux-contact ([[amr-left-wheel-faux-contact]]).
- **Test au sol en charge** `/tmp/gtest.sh` (AU SOL, espace devant) : capture odom start/end +
  `ros2 topic pub -t 40 -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear:{x:0.10},angular:{z:0.0}}"` puis
  pub 0 (watchdog) → vérifie déplacement + G/D égalisés (PID). 2026-06-20 sur secteur : G/D OK, gauche tient.

## VÉRIF NAV (bornées — JAMAIS `topic hz` en SSH, ça bloque/timeout)
- Lifecycle : `ros2 lifecycle get /controller_server` (active). Localisé : `ros2 topic echo /amcl_pose --once`.
- **Costmaps non vides** (sinon robot aveugle) :
  `ros2 topic echo /global_costmap/costmap --field data --once | tr ',' '\n' | grep -vE '^0$|^-1$|^$' | wc -l` (>0)
  (idem /local_costmap). Clear : `ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap "{}"`.
- Réglages à chaud : footprint/inflation/min_range cf [[amr-nav2-bringup]].

## CÔTÉ PC (Ubuntu) pour RViz
Chaque terminal : `source /opt/ros/jazzy/setup.bash; export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp;
export ROS_DOMAIN_ID=0` puis `rviz2`. Fixed Frame=`map` ; Displays : Map `/map`, LaserScan `/scan_filtered`
(Best Effort), Costmap local+global, Polygon `/local_costmap/published_footprint`. Outils : **2D Pose
Estimate** (localiser) → **2D Goal Pose** (but, PAS « Nav2 Goal »).

Sécurité tests moteurs : **roues en l'air** (ou espace dégagé + main prête à couper), PWM bas d'abord.
Cf [[amr-session-suite-nav2-cyclone]], [[amr-encoder-5v-overvoltage]], [[amr-driver-balance-dip]], [[amr-next-session-plan]].
