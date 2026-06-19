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
- SSH : `ssh botshare@172.17.201.29` (**clé OK, pas de mot de passe** ; hostname `BOTSHARE`).
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

## Bring-up complet (lidar+ekf+filtre+caméra), si besoin (shell interactif sur le Pi)
`source ~/camera_ws/install/setup.bash && ros2 launch /home/botshare/openamr_real_bringup.launch.py`

Sécurité tests moteurs : **roues en l'air**, main sur la coupure 24 V, PWM bas d'abord.
Cf [[amr-session-suite-nav2-cyclone]], [[amr-encoder-5v-overvoltage]], [[amr-driver-balance-dip]].
